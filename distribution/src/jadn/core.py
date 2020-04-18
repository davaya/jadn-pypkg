"""
Load, validate, prettyprint, and dump JSON Abstract Encoding Notation (JADN) schemas
"""

import json
import jsonschema
import numbers
import os
from datetime import datetime
from collections import defaultdict
from jadn.definitions import *
from jadn.utils import topts_s2d, ftopts_s2d
from jadn.codec.codec import Codec


def jadn_dir():
    """
    Return directory containing JADN schema files
    """
    return os.path.abspath(os.path.dirname(__file__))

def jadn_check(schema):
    """
    Validate JADN schema against JSON schema,
    Validate JADN schema against JADN meta-schema, then
    Perform additional checks on type definitions
    """

    def check_typeopts(type_name, base_type, topts):  # Check for invalid type options and undefined formats
        ro = {k for k in REQUIRED_TYPE_OPTIONS[base_type]} - {k for k in topts}
        if ro:
            _error('Missing type option', type_name + ':', str(ro))
        uo = {k for k in topts} - {k for k in ALLOWED_TYPE_OPTIONS[base_type]}
        if uo:
            _error('Unsupported type option', type_name + ' (' + base_type+ '):', str(uo))
        if 'format' in topts:
            f = topts['format']
            fm = dict(list(FORMAT_VALIDATE.items()) + list(FORMAT_JS_VALIDATE.items()) + list(FORMAT_SERIALIZE.items()))
            if f not in fm or base_type != fm[f]:
                _error('Unsupported format', f, 'in', type_name, base_type)
        if 'enum' in topts and 'pointer' in topts:
            _error('Type cannot be both Enum and Pointer', type_name, base_type)
        if 'and' in topts and 'or' in topts:
            _error('Unsupported union+intersection in ', type_name, base_type)

    here = jadn_dir()
    with open(os.path.join(here, 'jadn_schema.json')) as f:       # Check using JSON Schema for JADN
        jsonschema.Draft7Validator(json.load(f)).validate(schema)

    with open(os.path.join(here, 'jadn_schema.jadn')) as f:       # Optional: check using JADN meta-schema
        meta_schema = Codec(json.load(f), verbose_rec=True, verbose_str=True, config=schema)
        assert meta_schema.encode('Schema', schema) == schema

    types = set()                                                   # Additional checks not included in schema
    for t in schema['types']:
        tn = t[TypeName]
        bt = t[BaseType]
        if tn in types:
            _error('Duplicate type definition', tn)
        types |= {tn}
        if is_builtin(tn):
            _error('Reserved type name', tn)
        if not is_builtin(bt):
            _error('Invalid base type', tn + ':', bt)
        topts = topts_s2d(t[TypeOptions])
        check_typeopts(tn, bt, topts)
        flen = 0 if 'enum' in topts or 'pointer' in topts else FIELD_LENGTH[bt]
        if flen and len(t) <= Fields:
            _error('Missing fields', tn + '(' + bt + ')')
        elif not flen and len(t) > Fields:
            _error(tn + '(' + bt + ')', 'Cannot have fields')

        if flen:                # Check fields
            fids = set()        # Field IDs
            fnames = set()      # Field Names
            ordinal = bt in ('Array', 'Record')
            for n, f in enumerate(t[Fields]):
                if len(f) != flen:
                    _error('Bad field', n+1, 'in', tn, 'length', len(f), 'should be', flen)
                fids.update({f[FieldID]})
                fnames.update({f[FieldName]})
                if ordinal and f[FieldID] != n + 1:
                    _error('Item tag error:', tn + '(' + bt + ')[' + f[FieldName] + '] --', f[FieldID], 'should be', n + 1)
                if flen > FieldDesc:    # Full field, not an Enumerated item
                    fo, fto = ftopts_s2d(f[FieldOptions])
                    if is_builtin(f[FieldType]):
                        check_typeopts(tn + '/' + f[FieldName], f[FieldType], fto)
                        if 'minc' in fo and 'maxc' in fo:
                            if fo['minc'] < 0 or (fo['maxc'] > 0 and fo['maxc'] < fo['minc']):
                                _error(tn + '/', f[FieldName], 'bad cardinality', fo['minc'], fo['maxc'])
                    elif fto:
                        # _error(tn + '/' + f[FieldName] + '(' + f[FieldType] + ') cannot have Type options', fto)
                        pass    # TODO: pass 'unique' to multiplicity-based ArrayOf
            if len(t[Fields]) != len(fids) or len(t[Fields]) != len(fnames):
                _error('Duplicate field', tn, len(t[Fields]), 'fields,', len(fids), 'unique tags', len(fnames), 'unique names')
    return schema


def build_deps(schema):         # Build a Dependency dict: {TypeName: {Dep1, Dep2, ...}}
    def get_refs(tdef):         # Return all type references from a type definition
        oids = [OPTION_ID['ktype'], OPTION_ID['vtype'], OPTION_ID['and'], OPTION_ID['or']]  # Options whose value is/has a type name
        oids2 = [OPTION_ID['enum'], OPTION_ID['pointer']]                       # Options that enumerate fields
        refs = [to[1:] for to in tdef[TypeOptions] if to[0] in oids and not is_builtin(to[1:])]
        refs += [to for to in tdef[TypeOptions] if to[0] in oids2]
        if has_fields(tdef[BaseType]):
            for f in tdef[Fields]:
                if not is_builtin(f[FieldType]):
                    refs.append(f[FieldType])                               # Add reference to type name
                refs += get_refs(['', f[FieldType], f[FieldOptions], ''])   # Get refs from type opts in field (extension)
        return refs

    return {t[TypeName]: get_refs(t) for t in schema['types']}


def jadn_analyze(schema):
    def ns(name, nsids):   # Return namespace if name has a known namespace, otherwise return full name
        nsp = name.split(':')[0]
        return nsp if nsp in nsids else name

    items = build_deps(schema)
    # out, roots = topo_sort(items)
    imports = schema['meta']['imports'] if 'imports' in schema['meta'] else {}
    exports = schema['meta']['exports'] if 'exports' in schema['meta'] else []
    defs = {i for i in items} | set(imports)
    refs = set().union([ns(r, imports) for i in items for r in items[i]]) | set(exports)
    oids = (OPTION_ID['enum'], OPTION_ID['pointer'])
    refs = {r[1:] if r[0] in oids else r for r in refs}         # Reference base type for derived enums/pointers
    return {
        'unreferenced': [str(k) for k in defs - refs],
        'undefined': [str(k) for k in refs - defs],
        'cycles': [],
    }


def jadn_loads(jadn_str):
    schema = json.loads(jadn_str)
    return jadn_check(schema)


def jadn_load(fname):
    with open(fname, encoding='utf-8') as f:
        schema = json.load(f)
    return jadn_check(schema)


def jadn_dumps(schema, level=0, indent=1, strip=False, nlevel=None):
    sp = level * indent * ' '
    sp2 = (level + 1) * indent * ' '
    sep2 = ',\n' if strip else ',\n\n'
    if isinstance(schema, dict):
        sep = ',\n' if level > 0 else sep2
        lines = []
        for k in schema:
            lines.append(sp2 + '"' + k + '": ' + jadn_dumps(schema[k], level + 1, indent, strip))
        return '{\n' + sep.join(lines) + '\n' + sp + '}'
    elif isinstance(schema, list):
        sep = ',\n' if level > 1 else sep2
        vals = []
        nest = schema and isinstance(schema[0], list)       # Not an empty list
        for v in schema:
            sp3 = sp2 if nest else ''
            vals.append(sp3 + jadn_dumps(v, level + 1, indent, strip, level))
        if nest:
            spn = (nlevel if nlevel else level) * indent * ' '
            return '[\n' + sep.join(vals) + '\n' + spn + ']'
        return '[' + ', '.join(vals) + ']'
    elif isinstance(schema, (numbers.Number, type(''))):
        return json.dumps(schema)
    return '???'


def jadn_dump(schema, fname, source='', strip=False):
    with open(fname, 'w') as f:
        if source:
            f.write('"Generated from ' + source + ', ' + datetime.ctime(datetime.now()) + '"\n\n')
        f.write(jadn_dumps(schema, strip=strip) + '\n')


def _error(*s):                     # Handle errors
    raise ValueError(*s)


class SchemaModule:
    def __init__(self, source):     # Read schema data, get module name
        self.source = None          # Filename or URL
        self.module = None          # Namespace unique name
        self.schema = None          # JADN data
        self.imports = None         # Copy of meta['imports'] or empty {}
        self.tx = None              # Type index: {type name: type definition in schema}
        self.deps = None            # Internal dependencies: {type1: {t2, t3}, type2: {t3, t4, t5}}
        self.refs = None            # External references {namespace1: {type1: {t2, t3}, ...}}
        self.used = None            # Types from this module that have been referenced {t2, t3}
        if isinstance(source, dict):    # If schema is provided, save data
            self.schema = source
        elif isinstance(source, str):   # If filename or URL is provided, load data and record source
            if '://' in source:
                pass                    # TODO: read schema from URL
            else:
                with open(source, encoding='utf-8') as f:
                    self.schema = json.load(f)
            self.source = source

        if 'meta' in self.schema:
            self.module = self.schema['meta']['module']
            self.imports = self.schema['meta']['imports'] if 'imports' in self.schema['meta'] else {}
        else:
            _error('Schema module must have a module ID')
        self.clear()

    def load(self):                 # Validate schema, build type dependencies and external references
        if not self.deps:           # Ignore if already loaded
            jadn_check(self.schema)
            self.tx = {t[TypeName]: t for t in self.schema['types']}
            self.deps = build_deps(self.schema)
            self.refs = defaultdict(lambda: defaultdict(set))
            for tn in self.deps:
                for dn in self.deps[tn].copy():     # Iterate over copy so original can be modified safely
                    if ':' in dn:
                        self.deps[tn].remove(dn)
                        nsid, typename = dn.split(':', maxsplit=1)
                        self.refs[self.imports[nsid]][tn].add(typename)

    def clear(self):
        self.used = set()

    def add_used(self, type):
        self.used.add(type)
