"""
Load, validate, prettyprint, and dump JSON Abstract Encoding Notation (JADN) schemas
"""
import json
import jsonschema
import numbers
import os
import jadn

from datetime import datetime
from typing import NoReturn, Union
from .definitions import (
    FieldID, FieldName, FIELD_LENGTH, OPTION_ID, REQUIRED_TYPE_OPTIONS, ALLOWED_TYPE_OPTIONS, VALID_FORMATS,
    is_builtin, has_fields
)
from .utils import raise_error, list_types, object_types


def data_dir() -> str:
    """
    Return directory containing JADN schema files
    """
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


def check(schema: dict) -> dict:
    """
    Validate JADN schema against JSON schema,
    Validate JADN schema against JADN meta-schema, then
    Perform additional checks on type definitions
    """
    def check_typeopts(type_name: str, base_type: str, topts: dict) -> NoReturn:
        """
        Check for invalid type options and undefined formats
        """
        if ro := {*REQUIRED_TYPE_OPTIONS[base_type]} - {*topts.keys()}:
            raise_error(f'Missing type option {type_name}: {ro}')
        if uo := {*topts.keys()} - {*ALLOWED_TYPE_OPTIONS[base_type]}:
            raise_error(f'Unsupported type option {type_name} ({base_type}): {uo}')
        if 'maxv' in topts and 'minv' in topts and topts['maxv'] < topts['minv']:
            raise_error(f'Bad value range {type_name} ({base_type}): [{topts["minv"]}..{topts["maxv"]}]')
        # TODO: if format defines array, add minv/maxv (prevents adding default max)
        if fmt := topts.get('format'):
            if fmt not in VALID_FORMATS or base_type != VALID_FORMATS[fmt]:
                raise_error(f'Unsupported format {fmt} in {type_name} {base_type}')
        if 'enum' in topts and 'pointer' in topts:
            raise_error(f'Type cannot be both Enum and Pointer {type_name} {base_type}')
        if 'and' in topts and 'or' in topts:
            raise_error(f'Unsupported union+intersection in {type_name} {base_type}')

    # Add empty Fields if not present
    schema['types'] = list_types(object_types(schema['types']))

    local_dir = data_dir()
    with open(os.path.join(local_dir, 'jadn_v1.0_schema.json')) as f:     # Check using JSON Schema for JADN
        jsonschema.Draft7Validator(json.load(f)).validate(schema)

    with open(os.path.join(local_dir, 'jadn_v1.0_schema.jadn')) as f:     # Optional: check using JADN meta-schema
        meta_schema = jadn.codec.Codec(json.load(f), verbose_rec=True, verbose_str=True, config=schema)
        assert meta_schema.encode('Schema', schema) == schema

    # Additional checks not included in schema
    types = set()  # Additional checks not included in schema
    for t in object_types(schema['types']):
        if t.TypeName in types:
            raise_error(f'Duplicate type definition {t.TypeName}')
        types.add(t.TypeName)
        if is_builtin(t.TypeName):
            raise_error(f'Reserved type name {t.TypeName}')
        if not is_builtin(t.BaseType):
            raise_error(f'Invalid base type {t.TypeName}: {t.BaseType}')
        topts = jadn.topts_s2d(t.TypeOptions)
        check_typeopts(t.TypeName, t.BaseType, topts)

        # Check fields
        if flen := (0 if 'enum' in topts or 'pointer' in topts else FIELD_LENGTH[t.BaseType]):
            fids = set()  # Field IDs
            fnames = set()  # Field Names
            ordinal = t.BaseType in ('Array', 'Record')
            for n, f in enumerate(t.Fields):
                if len(f) != flen:
                    raise_error(f'Bad field {n + 1} in {t.TypeName} length, {len(f)} should be {flen}')
                fids.add(f[FieldID])
                fnames.add(f[FieldName])
                if ordinal and f[FieldID] != n + 1:
                    raise_error(f'Item tag error: {t.TypeName}({t.BaseType}) [{f[FieldName]}] -- {f[FieldID]} should be {n + 1}')
                if has_fields(t.BaseType):  # Full field, not an Enumerated item
                    fo, fto = jadn.ftopts_s2d(f.FieldOptions)
                    minc = fo.get('minc', 1)
                    maxc = fo.get('maxc', 1)
                    if minc < 0 or maxc < 0 or (0 < maxc < minc):
                        raise_error(f'{t.TypeName}/{f.FieldName} bad multiplicity {minc} {maxc}')

                    if tf := fo.get('tagid'):
                        if tf not in fids:
                            raise_error(f'{t.TypeName}/{f.FieldName}({f.FieldType}) choice has bad external tag {tf}')
                    if is_builtin(f.FieldType):
                        check_typeopts(f'{t.TypeName}/{f.FieldName}', f.FieldType, fto)
                    elif fto:
                        # unique option is moved to generated ArrayOf
                        if {*fto} - ({'unique', } if maxc != 1 else set()):
                            raise_error(f'{t.TypeName}/{f.FieldName}({f.FieldType}) cannot have Type options {fto}')
                    if 'dir' in fo:
                        if is_builtin(f.FieldType) and not has_fields(f.FieldType):  # TODO: check defined type
                            raise_error(f'{t.TypeName}/{f.FieldName}: {f.FieldType} cannot be dir')

            if len(t.Fields) != len(fids) or len(t.Fields) != len(fnames):
                raise_error(f'Duplicate field {t.TypeName} {len(t.Fields)} fields, {len(fids)} unique tags, {len(fnames)} unique names')
    return schema


def analyze(schema: dict) -> dict:
    def ns(name: str, nsids: dict) -> str:   # Return namespace if name has a known namespace, otherwise return full name
        nsp = name.split(':')[0]
        return nsp if nsp in nsids else name

    # TODO: Check for extension usages
    items = jadn.build_deps(schema)
    # out, roots = topo_sort(items)
    meta = schema['info'] if 'info' in schema else {}
    imports = meta['imports'] if 'imports' in meta else {}
    exports = meta['exports'] if 'exports' in meta else []
    defs = {*items.keys()} | set(imports)
    refs = set().union([ns(r, imports) for i in items for r in items[i]]) | set(exports)
    oids = (OPTION_ID['enum'], OPTION_ID['pointer'])
    refs = {r[1:] if r[0] in oids else r for r in refs}         # Reference base type for derived enums/pointers
    return {
        'unreferenced': [str(k) for k in defs - refs],
        'undefined': [str(k) for k in refs - defs],
        'cycles': [],
    }


def loads(jadn_str: str) -> dict:
    schema = json.loads(jadn_str)
    return check(schema)


def load(fname: Union[str, bytes, int]) -> dict:
    with open(fname, encoding='utf-8') as f:
        schema = json.load(f)
    return check(schema)


def dumps(schema: dict, strip: bool = False) -> str:
    def _d(val: any, level: int = 0, indent: int = 1, strip: bool = False, nlevel: int = None) -> str:
        sp = level * indent * ' '
        sp2 = (level + 1) * indent * ' '
        sep2 = ',\n' if strip else ',\n\n'
        if isinstance(val, dict):
            sep = ',\n' if level > 0 else sep2
            lines = []
            for k in val:
                lines.append(sp2 + '"' + k + '": ' + _d(val[k], level + 1, indent, strip))
            return '{\n' + sep.join(lines) + '\n' + sp + '}'
        if isinstance(val, list):
            sep = ',\n' if level > 1 else sep2
            vals = []
            nest = val and isinstance(val[0], list)  # Not an empty list
            for v in val:
                sp3 = sp2 if nest else ''
                vals.append(sp3 + _d(v, level + 1, indent, strip, level))
            if nest:
                spn = (nlevel if nlevel else level) * indent * ' '
                return '[\n' + sep.join(vals) + '\n' + spn + ']'
            return '[' + ', '.join(vals) + ']'
        if isinstance(val, (numbers.Number, type(''))):
            return json.dumps(val)
        return '???'

    return _d(schema, strip=strip)


def dump(schema: dict, fname: Union[str, bytes, int], source: str = '', strip: bool = False) -> NoReturn:
    with open(fname, 'w') as f:
        if source:
            f.write(f'"Generated from {source}, {datetime.ctime(datetime.now())}"\n\n')
        f.write(dumps(schema, strip=strip) + '\n')
