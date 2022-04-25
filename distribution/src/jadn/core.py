"""
Load, validate, prettyprint, and dump JSON Abstract Encoding Notation (JADN) schemas
"""
import json
import jsonschema
import numbers
import os
import jadn

from datetime import datetime
from typing import Any, NoReturn, TextIO, Union
from urllib.parse import urlparse
from .definitions import (
    FieldID, FieldName, FieldDesc, FIELD_LENGTH,
    OPTION_ID, REQUIRED_TYPE_OPTIONS, ALLOWED_TYPE_OPTIONS, VALID_FORMATS, is_builtin, has_fields
)
from .utils import raise_error, list_get_default, TypeDefinition, GenFieldDefinition


def data_dir() -> str:
    """
    Return directory containing JADN schema files
    """
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


# Check schema is valid
def check_typeopts(type_name: str, base_type: str, topts: dict) -> NoReturn:
    """
    Check for invalid type options and undefined formats
    """
    topts_set = set(topts)

    if ro := set(REQUIRED_TYPE_OPTIONS[base_type]) - topts_set:
        raise_error(f'Missing type option {type_name}: {ro}')
    if uo := topts_set - set(ALLOWED_TYPE_OPTIONS[base_type]):
        raise_error(f'Unsupported type option {type_name} ({base_type}): {uo}')
    if 'maxv' in topts and 'minv' in topts and topts['maxv'] < topts['minv']:
        raise_error(f'Bad value range {type_name} ({base_type}): [{topts["minv"]}..{topts["maxv"]}]')
    if 'maxf' in topts and 'minf' in topts and topts['maxf'] < topts['minf']:
        raise_error(f'Bad value range {type_name} ({base_type}): [{topts["minf"]}..{topts["maxf"]}]')

    # TODO: if format defines array, add minv/maxv (prevents adding default max)
    if fmt := topts.get('format'):
        if fmt not in VALID_FORMATS or base_type != VALID_FORMATS[fmt]:
            raise_error(f'Unsupported format {fmt} in {type_name} {base_type}')
    if 'enum' in topts and 'pointer' in topts:
        raise_error(f'Type cannot be both Enum and Pointer {type_name} {base_type}')
    if 'and' in topts and 'or' in topts:
        raise_error(f'Unsupported union+intersection in {type_name} {base_type}')


# TODO: finish convert to use dataclasses??
def check(schema: dict) -> dict:
    """
    Validate JADN schema against JSON schema,
    Validate JADN schema against JADN meta-schema, then
    Perform additional checks on type definitions
    """
    # Add empty Fields if not present
    schema_types = [TypeDefinition(*t) for t in schema['types']]
    schema['types'] = [list(t) for t in schema_types]

    data_path = data_dir()
    with open(os.path.join(data_path, 'jadn_v1.0_schema.json')) as f:     # Check using JSON Schema for JADN
        jsonschema.Draft7Validator(json.load(f)).validate(schema)

    with open(os.path.join(data_path, 'jadn_v1.0_schema.jadn')) as f:     # Optional: check using JADN meta-schema
        meta_schema = jadn.codec.Codec(json.load(f), verbose_rec=True, verbose_str=True, config=schema)
        assert meta_schema.encode('Schema', schema) == schema

    # Additional checks not included in schema
    types = set()
    for type_def in schema_types:
        if type_def.TypeName in types:
            raise_error(f'Duplicate type definition {type_def.TypeName}')
        types.add(type_def.TypeName)
        if is_builtin(type_def.TypeName):
            raise_error(f'Reserved type name {type_def.TypeName}')
        if not is_builtin(type_def.BaseType):
            raise_error(f'Invalid base type {type_def.TypeName}: {type_def.BaseType}')
        type_opts = jadn.topts_s2d(type_def.TypeOptions)
        check_typeopts(type_def.TypeName, type_def.BaseType, type_opts)

        # Check fields
        fields = type_def.Fields
        # Defined fields if there shouldn't be any
        if ('enum' in type_opts or 'pointer' in type_opts) and fields:
            raise_error(f'{type_def.TypeName}({type_def.BaseType}) should not have defined fields with the option enum/pointer')

        # Duplicates
        def duplicates(seq):
            seen = set()
            return set(x for x in seq if x in seen or seen.add(x))

        if dd := duplicates((f[FieldID] for f in fields)):
            raise_error(f'Duplicate fieldID: {type_def.TypeName} {dd}')
        if dd := duplicates((f[FieldName] for f in fields)):
            raise_error(f'Duplicate field name {type_def.TypeName} {dd}')
        # fids = {f[FieldID] for f in fields}  # Field IDs
        # fnames = {f[FieldName] for f in fields}  # Field Names
        # if len(fields) != len(fids) or len(fields) != len(fnames):
        #    raise_error(f'Duplicate field {type_def.TypeName} {len(fields)} fields, {len(fids)} unique tags, {len(fnames)} unique names')

        # Invalid definitions of field
        flen = FIELD_LENGTH[type_def.BaseType]  # Field item count
        if invalid := list_get_default([f for f in fields if len(f) != flen], 0):
            raise_error(f'Bad field id=`{invalid[FieldID]}` in {type_def.TypeName} length, {len(invalid)} should be {flen}')

        # Specific checks
        # Ordinal indexes
        if type_def.BaseType in ('Array', 'Record'):
            if invalid := list_get_default([(f, n) for n, f in enumerate(fields, 1) if f[FieldID] != n], 0):
                field, idx = invalid
                raise_error(f'Item tag error: {type_def.TypeName}({type_def.BaseType}) [{field[FieldName]}] -- {field[FieldID]} should be {idx}')

        # Full Fields -> Array, Choice, Map, Record
        if flen > FieldDesc:  # Full field, not an Enumerated item
            for field in [f if isinstance(f, GenFieldDefinition) else GenFieldDefinition(*f) for f in fields]:
                fo, fto = jadn.ftopts_s2d(field.FieldOptions)
                minc = fo.get('minc', 1)
                maxc = fo.get('maxc', 1)
                if minc < 0 or maxc < 0 or (0 < maxc < minc):
                    raise_error(f'{type_def.TypeName}/{field.FieldName} bad multiplicity {minc} {maxc}')

                if tf := fo.get('tagid', None):
                    if tf not in {f[FieldID] for f in fields}:
                        raise_error(f'{type_def.TypeName}/{field.FieldName}({field.FieldType}) choice has bad external tag {tf}')
                if is_builtin(field.FieldType):
                    check_typeopts(f'{type_def.TypeName}/{field.FieldName}', field.FieldType, fto)
                elif fto:
                    # unique option will be moved to generated ArrayOf
                    allowed = {'unique', } if maxc != 1 else set()
                    if set(fto) - allowed:
                        raise_error(f'{type_def.TypeName}/{field.FieldName}({field.FieldType}) cannot have Type options {fto}')
                if 'dir' in fo:
                    if is_builtin(field.FieldType) and not has_fields(field.FieldType):  # TODO: check defined type
                        raise_error(f'{type_def.TypeName}/{field.FieldName}: {field.FieldType} cannot be dir')
    return schema


def analyze(schema: dict) -> dict:
    def ns(name: str, nsids: dict) -> str:  # Return namespace if name has a known namespace, otherwise return full name
        nsp = name.split(':')[0]
        return nsp if nsp in nsids else name

    # TODO: Check for extension usages
    items = jadn.build_deps(schema)
    # out, roots = topo_sort(items)
    info = schema.get('info', {})
    imports = info.get('imports', {})
    exports = info.get('exports', [])

    defs = set(items) | set(imports)
    refs = {ns(r, imports) for i in items for r in items[i]} | set(exports)
    oids = (OPTION_ID['enum'], OPTION_ID['pointer'])
    refs = {r[1:] if r[0] in oids else r for r in refs}         # Reference base type for derived enums/pointers
    return {
        'unreferenced': list(map(str, defs - refs)),
        'undefined': list(map(str, refs - defs)),
        'cycles': [],
    }


def loads(jadn_str: str) -> dict:
    return check(json.loads(jadn_str))


def load(fp: TextIO) -> dict:
    return check(json.load(fp))


def load_any(fp: TextIO) -> dict:
    name = getattr(fp, 'name', getattr(getattr(fp, 'buffer'), 'url', ''))
    fn, ext = os.path.splitext(name)
    try:
        loader = {
            '.jadn': jadn.load,
            '.jidl': jadn.convert.jidl_load,
            '.html': jadn.convert.html_load
        }[ext]
    except KeyError:
        raise ValueError(f'Unsupported schema format: {name}')
    return loader(fp)


def dumps_rec(val: Any, level: int = 0, indent: int = 1, strip: bool = False, nlevel: int = None) -> str:
    if isinstance(val, (numbers.Number, type(''))):
        return json.dumps(val)

    sp2 = (level + 1) * indent * ' '
    sep2 = ',\n' if strip else ',\n\n'
    if isinstance(val, dict):
        sp = level * indent * ' '
        sep = ',\n' if level > 0 else sep2
        lines = sep.join(f'{sp2}"{k}": {dumps_rec(val[k], level + 1, indent, strip)}' for k in val)
        return f'{{\n{lines}\n{sp}}}'
    if isinstance(val, list):
        sep = ',\n' if level > 1 else sep2
        nest = val and isinstance(val[0], list)  # Not an empty list
        vals = [f"{sp2 if nest else ''}{dumps_rec(v, level + 1, indent, strip, level)}" for v in val]
        if nest:
            spn = (nlevel if nlevel else level) * indent * ' '
            return f"[\n{sep.join(vals)}\n{spn}]"
        return f"[{', '.join(vals)}]"
    return '???'


def dumps(schema: dict, strip: bool = False) -> str:
    return dumps_rec(schema, strip=strip)


def dump(schema: dict, fname: Union[str, bytes, int], source: str = '', strip: bool = False) -> NoReturn:
    with open(fname, 'w') as f:
        if source:
            f.write(f'"Generated from {source}, {datetime.ctime(datetime.now())}"\n\n')
        f.write(dumps(schema, strip=strip) + '\n')


__all__ = [
    'analyze',
    'check',
    'dump',
    'dumps',
    'load',
    'load_any',
    'loads',
    'data_dir'
]
