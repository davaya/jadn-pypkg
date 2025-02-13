"""
Load, validate, prettyprint, and dump JSON Abstract Encoding Notation (JADN) schemas
"""
import copy
import json
import jsonschema
import numbers
import os
import re
import jadn

from datetime import datetime
from typing import Any, TextIO, Union
from urllib.parse import urlparse
from .definitions import (
    TypeName, CoreType, FieldID, FieldName, FieldType, FieldDesc, Fields, FIELD_LENGTH,
    OPTION_ID, REQUIRED_TYPE_OPTIONS, ALLOWED_TYPE_OPTIONS, ALLOWED_TYPE_OPTIONS_ALL,
    VALID_FORMATS, is_builtin, has_fields
)
from .utils import raise_error, list_get_default, TypeDefinition, GenFieldDefinition


def data_dir() -> str:
    """
    Return directory containing JADN schema files
    """
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


# Check schema is valid
def check_typeopts(type_name: str, base_type: str, topts: dict) -> None:
    """
    Check for invalid type options and undefined formats
    """
    topts_set = set(topts)

    if ro := set(REQUIRED_TYPE_OPTIONS[base_type]) - topts_set:
        raise_error(f'Missing type option {type_name}: {ro}')
    if uo := topts_set - set(ALLOWED_TYPE_OPTIONS[base_type] + ALLOWED_TYPE_OPTIONS_ALL):
        raise_error(f'Unsupported type option {type_name} ({base_type}): {uo}')
    if 'maxLength' in topts and 'minLength' in topts and topts['maxLength'] < topts['minLength']:
        raise_error(f'Bad value range {type_name} ({base_type}): [{topts["minLength"]}..{topts["maxLength"]}]')
    if ('minLength' in topts or 'maxLength' in topts) and 'pattern' in topts:
        raise_error(f'String cannot have both pattern and size constraints: {type_name}')  # disable for debugging

    # TODO: if format defines array, add minLength/maxLength (prevents adding default max)
    if fmt := topts.get('format'):
        if m := re.match(r'^([iudf])(\d+)$', fmt):
            pass    # bit/digit count formats OK  TODO: auto-align with definitions
        elif fmt not in VALID_FORMATS or base_type != VALID_FORMATS[fmt]:
            raise_error(f'Unsupported format {fmt} in {type_name} {base_type}')
    if 'enum' in topts and 'pointer' in topts:
        raise_error(f'Type cannot be both Enum and Pointer {type_name} {base_type}')


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
    with open(os.path.join(data_path, 'jadn_v2.0_schema.json')) as f:     # Check using JSON Schema for JADN
        jsonschema.Draft7Validator(json.load(f)).validate(schema)

    with open(os.path.join(data_path, 'jadn_v2.0_schema.jadn')) as f:     # Check using JADN metaschema
        meta_schema = jadn.codec.Codec(json.load(f), verbose_rec=True, verbose_str=True, config=schema)
        assert meta_schema.encode('Schema', schema) == schema

    # Additional checks not included in schema
    types = {}
    for td in schema_types:
        collisions = []
        if td.TypeName in types:
            collisions.append(td.TypeName)
        if collisions:
            raise_error(f'Colliding type definitions {collisions}')
        types[td.TypeName] = td
        if is_builtin(td.TypeName):
            raise_error(f'Reserved type name {td.TypeName}')
        if not is_builtin(td.CoreType):
            raise_error(f'Invalid base type {td.TypeName}: {td.CoreType}')
        type_opts = jadn.topts_s2d(td.TypeOptions, td.CoreType)
        check_typeopts(td.TypeName, td.CoreType, type_opts)

        # Check fields
        fields = td.Fields
        # Defined fields if there shouldn't be any
        if ('enum' in type_opts or 'pointer' in type_opts) and fields:
            raise_error(f'{td.TypeName}({td.CoreType}) should not have defined fields with the option enum/pointer')
        # Invalid anonymous field types
        for fd in fields:
            fdefault = [None, None, ''] if td.CoreType == 'Enumerated' else [None, None, None, [], '']
            fd[:len(fd)] += fdefault[len(fd):]
            if has_fields(fd[FieldType]):
                raise_error(f'{td[TypeName]}/{fd[FieldName]}({fd[FieldID]}): Invalid type "{fd[FieldType]}"')

        # Duplicates
        def duplicates(seq):
            seen = set()
            return set(x for x in seq if x in seen or seen.add(x))

        if dd := duplicates((f[FieldID] for f in fields)):
            raise_error(f'Duplicate fieldID: {td.TypeName} {dd}')
        if dd := duplicates((f[FieldName] for f in fields)):
            raise_error(f'Duplicate field name {td.TypeName} {dd}')

        # Invalid definitions of field - TODO: delete: schema checks field length, defaults are filled
        flen = FIELD_LENGTH[td.CoreType]  # Field item count
        if invalid := list_get_default([f for f in fields if len(f) != flen], 0):
            raise_error(f'Bad field {td.TypeName}.{invalid[FieldID]}: length {len(invalid)} should be {flen}')

        # Specific checks
        # Ordinal indexes
        if td.CoreType in ('Array', 'Record'):
            if invalid := list_get_default([(f, n) for n, f in enumerate(fields, 1) if f[FieldID] != n], 0):
                to = jadn.topts_s2d(td.TypeOptions)
                if 'extends' not in to and 'restricts' not in to:
                    field, idx = invalid
                    raise_error(f'Item id error: {td.TypeName}({td.CoreType}) [{field[FieldName]}] -- {field[FieldID]} should be {idx}')

        # Full Fields -> Array, Choice, Map, Record
        if flen > FieldDesc:  # Full field, not an Enumerated item
            for field in [f if isinstance(f, GenFieldDefinition) else GenFieldDefinition(*f) for f in fields]:
                fo, fto = jadn.ftopts_s2d(field.FieldOptions, field.FieldType)
                minOccurs = fo.get('minOccurs', 1)
                maxOccurs = fo.get('maxOccurs', 1)
                if minOccurs < 0 or (0 < maxOccurs < minOccurs):
                    raise_error(f'{td.TypeName}.{field.FieldName} bad multiplicity {minOccurs} {maxOccurs}')

                if tf := fo.get('tagid', None):
                    if tf not in {f[FieldID] for f in fields}:
                        raise_error(f'{td.TypeName}/{field.FieldName}({field.FieldType}) choice has bad external tag {tf}')

                if is_builtin(field.FieldType):
                    check_typeopts(f'{td.TypeName}/{field.FieldName}', field.FieldType, fto)
                elif fto:
                    # unique option will be moved to generated ArrayOf
                    allowed = {'unique', } if maxOccurs != 1 else set()
                    if set(fto) - allowed:
                        raise_error(f'{td.TypeName}/{field.FieldName}({field.FieldType}) cannot have Type options {fto}')
                if 'dir' in fo:
                    if is_builtin(field.FieldType) and not has_fields(field.FieldType):  # TODO: check defined type
                        raise_error(f'{td.TypeName}/{field.FieldName}: {field.FieldType} cannot be dir')
    return schema


def analyze(schema: dict) -> dict:
    items = jadn.build_deps(schema)
    meta = schema.get('meta', {})
    roots = meta.get('roots', [])
    defs = set(items)
    dep_refs = {v for d in items for v in items[d]}
    refs = set(dep_refs) | set(roots)
    return {
        'unreferenced': list(defs - refs),
        'undefined': list(refs - defs),
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
        raise KeyError(f'Unsupported schema format: {name}')
    return loader(fp)


def pprint(val: Any, level: int = 0, indent: int = 2, strip: bool = False) -> str:
    if isinstance(val, (numbers.Number, type(''))):
        return json.dumps(val, ensure_ascii=False)

    sp = level * indent * ' '
    sp2 = (level + 1) * indent * ' '
    sep2 = ',\n' if strip else ',\n\n'
    if isinstance(val, dict):
        sep = ',\n' if level > 0 else sep2
        lines = sep.join(f'{sp2}"{k}": {pprint(val[k], level + 1, indent, strip)}' for k in val)
        return f'{{\n{lines}\n{sp}}}'
    if isinstance(val, list):
        sep = ',\n' if level > 1 else sep2
        nest = val and isinstance(val[0], list)  # Not an empty list
        if nest:
            vals = [f"{sp2}{pprint(v, level, indent, strip)}" for v in val]
            spn = level * indent * ' '
            return f"[\n{sep.join(vals)}\n{spn}]"
        vals = [f"{pprint(v, level + 1, indent, strip)}" for v in val]
        return f"[{', '.join(vals)}]"
    return '???'


def strip_trailing_defaults(schema: dict[dict, list]) -> dict:
    tdef = [None, None, [], '', []]
    for td in schema['types']:
        fdef = [None, None, ''] if td[CoreType] == 'Enumerated' else [None, None, None, [], '']
        for fd in td[Fields]:
            while fd and fd[-1] == fdef[len(fd)-1]:
                fd.pop()
        while td and td[-1] == tdef[len(td)-1]:
            td.pop()
    return schema


def dumps(schema: dict, strip: bool = False) -> str:
    sc1 = {'meta': schema['meta'], 'types': copy.deepcopy(schema['types'])}
    return pprint(strip_trailing_defaults(sc1), strip=strip)


def dump(schema: dict, fname: Union[str, bytes, int], source: str = '', strip: bool = False) -> None:
    with open(fname, 'w', encoding='utf8') as f:
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
