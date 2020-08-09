"""
Load, validate, prettyprint, and dump JSON Abstract Encoding Notation (JADN) schemas
"""

import json
import jsonschema
import numbers
import os
from datetime import datetime

import jadn
from jadn.definitions import *


def data_dir():
    """
    Return directory containing JADN schema files
    """
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


def raise_error(*s):                     # Handle errors
    raise ValueError(*s)


def check(schema):
    """
    Validate JADN schema against JSON schema,
    Validate JADN schema against JADN meta-schema, then
    Perform additional checks on type definitions
    """

    def check_typeopts(type_name, base_type, topts):  # Check for invalid type options and undefined formats
        ro = {k for k in REQUIRED_TYPE_OPTIONS[base_type]} - {k for k in topts}
        if ro:
            raise_error(f'Missing type option {type_name}: {str(ro)}')
        uo = {k for k in topts} - {k for k in ALLOWED_TYPE_OPTIONS[base_type]}
        if uo:
            raise_error(f'Unsupported type option {type_name} ({base_type}): {str(uo)}')
        if 'format' in topts:        # TODO: if format defines array, add minv/maxv (prevents adding default max)
            f = topts['format']
            fm = dict(list(FORMAT_VALIDATE.items()) + list(FORMAT_JS_VALIDATE.items()) + list(FORMAT_SERIALIZE.items()))
            if f not in fm or base_type != fm[f]:
                raise_error(f'Unsupported format {f} in {type_name} {base_type}')
        if 'enum' in topts and 'pointer' in topts:
            raise_error(f'Type cannot be both Enum and Pointer {type_name} {base_type}')
        if 'and' in topts and 'or' in topts:
            raise_error(f'Unsupported union+intersection in {type_name} {base_type}')

    for t in schema['types']:           # Transition old type definitions to constant length
        if len(t) <= Fields:
            t.append([])

    here = data_dir()
    with open(os.path.join(here, 'jadn_v1.0_schema.json')) as f:     # Check using JSON Schema for JADN
        jsonschema.Draft7Validator(json.load(f)).validate(schema)

    with open(os.path.join(here, 'jadn_v1.0_schema.jadn')) as f:     # Optional: check using JADN meta-schema
        meta_schema = jadn.codec.Codec(json.load(f), verbose_rec=True, verbose_str=True, config=schema)
        assert meta_schema.encode('Schema', schema) == schema

    types = set()                                               # Additional checks not included in schema
    for t in schema['types']:
        tn = t[TypeName]
        bt = t[BaseType]
        if tn in types:
            raise_error(f'Duplicate type definition {tn}')
        types |= {tn}
        if is_builtin(tn):
            raise_error(f'Reserved type name {tn}')
        if not is_builtin(bt):
            raise_error(f'Invalid base type {tn}: {bt}')
        topts = jadn.topts_s2d(t[TypeOptions])
        check_typeopts(tn, bt, topts)
        flen = 0 if 'enum' in topts or 'pointer' in topts else FIELD_LENGTH[bt]
        if flen:                # Check fields
            fids = set()        # Field IDs
            fnames = set()      # Field Names
            ordinal = bt in ('Array', 'Record')
            for n, f in enumerate(t[Fields]):
                if len(f) != flen:
                    raise_error(f'Bad field {n+1} in {tn} length, {len(f)} should be {flen}')
                fids.update({f[FieldID]})
                fnames.update({f[FieldName]})
                if ordinal and f[FieldID] != n + 1:
                    raise_error(f'Item tag error: {tn}({bt}) [{f[FieldName]}] -- {f[FieldID]} should be {n+1}')
                if flen > FieldDesc:    # Full field, not an Enumerated item
                    fo, fto = jadn.ftopts_s2d(f[FieldOptions])
                    minc, maxc = fo.get('minc', 1), fo.get('maxc', 1)
                    if minc < 0 or maxc < 0 or (maxc > 0 and maxc < minc):
                        raise_error(f'{tn}/{f[FieldName]} bad multiplicity {minc} {maxc}')
                    tf = fo.get('tagid')
                    if tf and tf not in fids:
                        raise_error(f'{tn}/{f[FieldName]}({f[FieldType]}) choice has bad external tag {tf}')
                    if is_builtin(f[FieldType]):
                        check_typeopts(f'{tn}/{f[FieldName]}', f[FieldType], fto)
                    elif fto:
                        allowed = {'unique', } if maxc != 1 else set()  # unique option is moved to generated ArrayOf
                        if set(fto) - allowed:
                            raise_error(f'{tn}/{f[FieldName]}({f[FieldType]}) cannot have Type options {fto}')
                    if 'dir' in fo:
                        if is_builtin(f[FieldType]) and not has_fields(f[FieldType]):   # TODO: check defined type
                            raise_error(f'{tn}/{f[FieldName]}: {f[FieldType]} cannot be dir')

            if len(t[Fields]) != len(fids) or len(t[Fields]) != len(fnames):
                raise_error(f'Duplicate field {tn} {len(t[Fields])} fields, {len(fids)} unique tags, {len(fnames)} unique names')
    return schema


def analyze(schema):
    def ns(name, nsids):   # Return namespace if name has a known namespace, otherwise return full name
        nsp = name.split(':')[0]
        return nsp if nsp in nsids else name

    # TODO: Check for extension usages

    items = jadn.build_deps(schema)
    # out, roots = topo_sort(items)
    meta = schema['info'] if 'info' in schema else {}
    imports = meta['imports'] if 'imports' in meta else {}
    exports = meta['exports'] if 'exports' in meta else []
    defs = {i for i in items} | set(imports)
    refs = set().union([ns(r, imports) for i in items for r in items[i]]) | set(exports)
    oids = (OPTION_ID['enum'], OPTION_ID['pointer'])
    refs = {r[1:] if r[0] in oids else r for r in refs}         # Reference base type for derived enums/pointers
    return {
        'unreferenced': [str(k) for k in defs - refs],
        'undefined': [str(k) for k in refs - defs],
        'cycles': [],
    }


def loads(jadn_str):
    schema = json.loads(jadn_str)
    return check(schema)


def load(fname):
    with open(fname, encoding='utf-8') as f:
        schema = json.load(f)
    return check(schema)


def dumps(schema, level=0, indent=1, strip=False, nlevel=None):
    def _d(schema, level=0, indent=1, strip=False, nlevel=None):
        sp = level * indent * ' '
        sp2 = (level + 1) * indent * ' '
        sep2 = ',\n' if strip else ',\n\n'
        if isinstance(schema, dict):
            sep = ',\n' if level > 0 else sep2
            lines = []
            for k in schema:
                lines.append(sp2 + '"' + k + '": ' + _d(schema[k], level + 1, indent, strip))
            return '{\n' + sep.join(lines) + '\n' + sp + '}'
        elif isinstance(schema, list):
            sep = ',\n' if level > 1 else sep2
            vals = []
            nest = schema and isinstance(schema[0], list)  # Not an empty list
            for v in schema:
                sp3 = sp2 if nest else ''
                vals.append(sp3 + _d(v, level + 1, indent, strip, level))
            if nest:
                spn = (nlevel if nlevel else level) * indent * ' '
                return '[\n' + sep.join(vals) + '\n' + spn + ']'
            return '[' + ', '.join(vals) + ']'
        elif isinstance(schema, (numbers.Number, type(''))):
            return json.dumps(schema)
        return '???'

    return _d(jadn.canonicalize(schema), level, indent, strip, nlevel)


def dump(schema, fname, source='', strip=False):
    with open(fname, 'w') as f:
        if source:
            f.write('"Generated from ' + source + ', ' + datetime.ctime(datetime.now()) + '"\n\n')
        f.write(dumps(schema, strip=strip) + '\n')
