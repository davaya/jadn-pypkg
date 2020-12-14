"""
Support functions for JADN codec
  Convert dict between nested and flat
  Convert typedef options between dict and strings
"""
import copy
import re

from functools import reduce
from typing import Dict, List, NoReturn, Tuple, Union
from .definitions import (
    TypeName, BaseType, TypeOptions, Fields, ItemDesc, FieldID, FieldName, FieldType, FieldOptions, FieldDesc,
    DEFAULT_CONFIG, TYPE_OPTIONS, FIELD_OPTIONS, OPTION_ID, OPTION_TYPES, is_builtin, has_fields, TypeDefinition,
    EnumFieldDefinition, GenFieldDefinition
)


# Handle errors
def raise_error(*s) -> NoReturn:
    raise ValueError(*s)


# Dict conversion utilities
def dmerge(*dicts: dict) -> dict:
    """
    Merge any number of dicts
    """
    return {k: v for d in dicts for k, v in d.items()}


def hdict(keys: str, value: any, sep: str = '.') -> dict:
    """
    Convert a hierarchical-key value pair to a nested dict
    """
    return reduce(lambda v, k: {k: v}, reversed(keys.split(sep)), value)


def fluff(src: dict, sep: str = '.') -> dict:
    """
    Convert a flat dict with hierarchical keys to a nested dict

    :param src: flat dict - e.g., {'a.b.c': 1, 'a.b.d': 2}
    :param sep: separator character for keys
    :return: nested dict - e.g., {'a': {'b': {'c': 1, 'd': 2}}}
    """
    return reduce(dmerge, [hdict(k, v, sep) for k, v in src.items()], {})


def flatten(cmd: dict, path: str = '', fc: dict = None, sep: str = '.') -> dict:
    """
    Convert a nested dict to a flat dict with hierarchical keys
    """
    if fc is None:
        fc = {}
    fcmd = fc.copy()
    if isinstance(cmd, dict):
        for k, v in cmd.items():
            k = k.split(':')[1] if ':' in k else k
            fcmd = flatten(v, sep.join((path, k)) if path else k, fcmd)
    elif isinstance(cmd, list):
        for n, v in enumerate(cmd):
            fcmd.update(flatten(v, sep.join([path, str(n)])))
    else:
        fcmd[path] = cmd
    return fcmd


def dlist(src: dict) -> dict:
    """
    Convert dicts with numeric keys to lists

    :param src: {'a': {'b': {'0':'red', '1':'blue'}, 'c': 'foo'}}
    :return: {'a': {'b': ['red', 'blue'], 'c': 'foo'}}
    """
    if isinstance(src, dict):
        for k in src:
            src[k] = dlist(src[k])
        if set(src) == {str(k) for k in range(len(src))}:
            src = [src[str(k)] for k in range(len(src))]
    return src


def build_deps(schema: dict) -> Dict[str, List[str]]:
    """
    Build a Dependency dict: {TypeName: {Dep1, Dep2, ...}}
    """
    def get_refs(tdef: list) -> list:         # Return all type references from a type definition
        oids = [OPTION_ID['ktype'], OPTION_ID['vtype'], OPTION_ID['and'], OPTION_ID['or']]  # Options whose value is/has a type name
        oids2 = [OPTION_ID['enum'], OPTION_ID['pointer']]                       # Options that enumerate fields
        refs = [to[1:] for to in tdef[TypeOptions] if to[0] in oids and not is_builtin(to[1:])]
        refs += [to for to in tdef[TypeOptions] if to[0] in oids2]
        if has_fields(tdef[BaseType]):
            for f in tdef[Fields]:
                if not is_builtin(f[FieldType]):
                    refs.append(f[FieldType])                              # Add reference to type name
                refs += get_refs(['', f[FieldType], f[FieldOptions], ''])  # Get refs from type opts in field (extension)
        return refs

    return {t[TypeName]: get_refs(t) for t in schema['types']}


def topo_sort(items: List[Tuple[str, List[str]]]) -> Tuple[list, set]:
    """
    Topological sort with locality
    Sorts a list of (item: (dependencies)) pairs so that 1) all dependency items are listed before the parent item,
    and 2) dependencies are listed in the given order and as close to the parent as possible.
    Returns the sorted list of items and a list of root items.  A single root indicates a fully-connected hierarchy;
    multiple roots indicate disconnected items or hierarchies, and no roots indicate a dependency cycle.
    """
    def walk_tree(it: str) -> NoReturn:
        for i in deps[it]:
            if i not in out:
                walk_tree(i)
                out.append(i)

    out = []
    deps = {i[0]: i[1] for i in items}           # TODO: update for items dict
    roots = {i[0] for i in items} - set().union(*[i[1] for i in items])
    for item in roots:
        walk_tree(item)
        out.append(item)
    out = out if out else [i[0] for i in items]     # if cycle detected, don't sort
    return out, roots


def get_optx(opts: List[OPTION_TYPES], oname: str) -> Union[OPTION_TYPES, None]:
    n = [i for i, x in enumerate(opts) if x[0] == OPTION_ID[oname]]
    return n[0] if n else None


def del_opt(opts: List[OPTION_TYPES], oname: str) -> NoReturn:
    if n := [i for i, x in enumerate(opts) if x[0] == OPTION_ID[oname]]:
        del opts[n[0]]


def topts_s2d(olist: Union[List[OPTION_TYPES], Tuple[OPTION_TYPES, ...]], frange: bool = False) -> dict:
    """
    Convert list of type definition option strings to options dictionary
    """
    assert isinstance(olist, (list, tuple)), f'{olist} is not a list'
    opts = {}
    for o in olist:
        try:
            k = TYPE_OPTIONS[ord(o[0])]
            opts[k[0]] = k[1](o[1:])
        except KeyError:
            raise_error(f'Unknown type option: {o}')
    return opts


def ftopts_s2d(olist: Union[List[OPTION_TYPES], Tuple[OPTION_TYPES, ...]]) -> Tuple[dict, dict]:
    """
    Convert list of field definition option strings to options dictionary
    returns - FieldOptions, TypeOptions
    """
    assert isinstance(olist, (list, tuple)), f'{olist} is not a list'
    fopts, topts = {}, {}
    for o in olist:
        try:
            k = FIELD_OPTIONS[ord(o[0])]
            fopts[k[0]] = k[1](o[1:])
        except KeyError:
            topts.update(topts_s2d([o]))
    return fopts, topts


def opts_d2s(to: dict) -> List[str]:
    try:
        return [OPTION_ID[k] + ('' if v is True else str(v)) for k, v in to.items()]
    except KeyError:
        raise_error(f'Unknown option tag {to}')


def opts_sort(olist: Union[List[OPTION_TYPES], Tuple[OPTION_TYPES, ...]]) -> NoReturn:
    """
    Sort JADN option list into canonical order
    """
    def opt_order(o):
        try:
            k = FIELD_OPTIONS[ord(o)][2]
        except KeyError:
            k = TYPE_OPTIONS[ord(o)][2]
        return k

    olist.sort(key=lambda x: opt_order(x[0]))


def canonicalize(schema: dict) -> dict:
    def can_opts(olist: List[OPTION_TYPES], btype: str):
        opts_sort(olist)                # Sort options into canonical order (for comparisons)
        fo, to = ftopts_s2d(olist)      # Remove default size and multiplicity options
        if 'minv' in to and to['minv'] == 0 and btype != 'Integer':
            del_opt(olist, 'minv')
        if 'minc' in fo and fo['minc'] == 1:
            del_opt(olist, 'minc')
        if 'maxc' in fo and fo['maxc'] == 1:
            del_opt(olist, 'maxc')
        if btype == 'Number':           # TODO: fix corner case input = 2.000
            minf = get_optx(olist, 'minf')
            if minf is not None and '.' not in olist[minf]:
                olist[minf] += '.0'
            maxf = get_optx(olist, 'maxf')
            if maxf is not None and '.' not in olist[maxf]:
                olist[maxf] += '.0'

    cschema = copy.deepcopy(schema)     # don't modify original
    for td in cschema['types']:
        can_opts(td[TypeOptions], td[BaseType])
        for fd in td[Fields]:
            if td[BaseType] != 'Enumerated':
                can_opts(fd[FieldOptions], fd[FieldType])
    return cschema


def cleanup_tagid(fields: List[list]) -> List[list]:
    """
    If type definition contains a TagId option, replace field name with id
    """
    for f in fields:
        if len(f) > FieldOptions:
            tx = get_optx(f[FieldOptions], 'tagid')
            if tx is not None:
                to = f[FieldOptions][tx]
                try:
                    int(to[1:])                 # Check if already a Field Id
                except ValueError:              # Look up Id corresponding to Field Name
                    fx = {x[FieldName]: x[FieldID] for x in fields}
                    f[FieldOptions][tx] = to[0] + str(fx[to[1:]])
    return fields


def typestr2jadn(typestring: str) -> Tuple[str, List[str], list]:
    def parseopt(optstr: str) -> str:
        m1 = re.match(r'^\s*([-$\w]+)(?:\[([^]]+)\])?$', optstr)
        if m1 is None:
            raise_error(f'TypeString2JADN: unexpected function: {optstr}')
        return OPTION_ID[m1.group(1).lower()] + m1.group(2) if m1.group(2) else m1.group(1)

    topts = {}
    fo = []
    p_name = r'\s*=?\s*([-$:\w]+)'      # 1 type name
    p_id = r'(\.ID)?'                   # 2 'id'
    p_func = r'(?:\(([^)]+)\))?'        # 3 'ktype', 'vtype', 'enum', 'pointer', 'tagid'
    p_rangepat = r'(?:\{(.*)\})?'       # 4 'minv', 'maxv', 'pattern'
    p_format = r'(?:\s+\/(\w[-\w]*))?'  # 5 'format'
    p_unique = r'(\s+unique)?'          # 6 'unique'
    pattern = fr'^{p_name}{p_id}{p_func}{p_rangepat}{p_format}{p_unique}\s*$'
    m = re.match(pattern, typestring)
    if m is None:
        raise_error(f'TypeString2JADN: "{typestring}" does not match pattern {pattern}')
    tname = m.group(1)
    topts.update({'id': True} if m.group(2) else {})
    if m.group(3):                      # (ktype, vtype), Enum(), Pointer() options
        opts = [parseopt(x) for x in m.group(3).split(',', maxsplit=1)]
        if tname == 'MapOf':
            topts.update({'ktype': opts[0], 'vtype': opts[1]})
        elif tname == 'ArrayOf':
            assert len(opts) == 1
            topts.update({'vtype': opts[0]})
        else:
            assert len(opts) == 1
            topts.update(topts_s2d([opts[0]]) if ord(opts[0][0]) in TYPE_OPTIONS else {})
            fo += [opts[0]] if ord(opts[0][0]) in FIELD_OPTIONS else []         # TagId option
    if m.group(4):
        if m1 := re.match('^pattern="(.+)"$', m.group(4)):
            topts.update({'pattern': m1.group(1)})
        else:
            a, b = m.group(4).split('..', maxsplit=1)
            if tname == 'Number':
                topts.update({} if a == '*' else {'minf': float(a)})
                topts.update({} if b == '*' else {'maxf': float(b)})
            else:
                a = '*' if tname != 'Integer' and a != '*' and int(a) == 0 else a   # Default min size = 0
                topts.update({} if a == '*' else {'minv': int(a)})
                topts.update({} if b == '*' else {'maxv': int(b)})
    topts.update({'format': m.group(5)} if m.group(5) else {})
    topts.update({'unique': True} if m.group(6) else {})
    return tname, opts_d2s(topts), fo


def jadn2typestr(tname: str, topts: List[OPTION_TYPES]) -> str:
    """
    Convert typename and options to string
    """
    # Handle ktype/vtype containing Enum options
    def _kvstr(optv: str) -> str:
        if optv[0] == OPTION_ID['enum']:
            return f'Enum[{optv[1:]}]'
        if optv[0] == OPTION_ID['pointer']:
            return f'Pointer[{optv[1:]}]'
        return optv

    # Size range (single-ended) - default is {0..*}
    def _srange(ops: dict) -> str:
        lo = ops.pop('minv', 0)
        hi = ops.pop('maxv', -1)
        hs = '*' if hi < 0 else str(hi)
        return f'{lo}..{hs}' if lo != 0 or hs != '*' else ''

    # Value range (double-ended) - default is {*..*}
    def _vrange(ops: dict) -> str:
        lo = ops.pop('minv', '*')
        hi = ops.pop('maxv', '*')
        return f'{lo}..{hi}' if lo != '*' or hi != '*' else ''

    # Value range (double-ended) - default is {*..*}
    def _frange(ops: dict) -> str:
        lo = ops.pop('minf', '*')
        hi = ops.pop('maxf', '*')
        return f'{lo}..{hi}' if lo != '*' or hi != '*' else ''

    opts = topts_s2d(topts)
    extra = '.ID' if opts.pop('id', None) else ''   # SIDE EFFECT: remove known options from opts.
    if tname == 'ArrayOf':
        extra += f"({_kvstr(opts.pop('vtype'))})"
    elif tname == 'MapOf':
        extra += f"({_kvstr(opts.pop('ktype'))}, {_kvstr(opts.pop('vtype'))})"

    if v := opts.pop('enum', None):
        extra += f'(Enum[{v}])'

    if v := opts.pop('pointer', None):
        extra += f'(Pointer[{v}])'

    if v := opts.pop('pattern', None):  # String can have {range} or {pattern} or /format
        extra += f'{{pattern="{v}"}}'

    if v := _vrange(opts) if tname == 'Integer' else (_frange(opts) if tname == 'Number' else _srange(opts)):
        extra += f'{{{v}}}'

    if v := opts.pop('format', None):
        extra += f' /{v}'

    if opts.pop('unique', None):
        extra += ' unique'

    if v := opts.pop('and', None):  # hack set operations for now.  TODO: generalize to any number
        extra += f' ∩ {v}'

    if v := opts.pop('or', None):
        extra += f' ∪ {v}'

    return f"{tname}{extra}{' ?' + str(map(str, opts)) + '?' if opts else ''}"  # Flag unrecognized options


def jadn2fielddef(fdef: list, tdef: list) -> Tuple[str, str, str, str]:
    idtype = tdef[BaseType] == 'Array' or get_optx(tdef[TypeOptions], 'id') is not None
    fname = '' if idtype else fdef[FieldName]
    fdesc = fdef[FieldName] + ':: ' if idtype else ''
    if tdef[BaseType] == 'Enumerated':
        fdesc += fdef[ItemDesc]
        ftyperef, fmult = '', ''
    else:
        fdesc += fdef[FieldDesc]
        fo, fto = ftopts_s2d(fdef[FieldOptions])
        fname += '/' if 'dir' in fo else ''
        tagid = fo.get('tagid')
        tf = ''
        if tagid:
            tf = {f[FieldID]: f[FieldName] for f in tdef[Fields]}[tagid]
            tf = tf if tf else str(tagid)
            tf = f'(TagId[{tf}])'
        ft = jadn2typestr(fdef[FieldType] + tf, opts_d2s(fto))
        ftyperef = f'Key({ft})' if 'key' in fo else f'Link({ft})' if 'link' in fo else ft
        minc, maxc = fo.get('minc', 1), fo.get('maxc', 1)
        fmult = '1' if minc == 1 and maxc == 1 else str(minc) + '..' + ('*' if maxc == 0 else str(maxc))
    return fname, ftyperef, fmult, fdesc


def fielddef2jadn(fid: int, fname: str, fstr: str, fmult: str, fdesc: str) -> list:
    ftyperef = ''
    fo = {}
    if fstr:
        if m := re.match(r'^(Link|Key)\((.*)\)$', fstr):
            fo = {m.group(1).lower(): True}
            fstr = m.group(2)
        ftyperef, topts, fopts = typestr2jadn(fstr)
        # Field is one of: enum.id, enum, field.id, field
        fo.update(topts_s2d(topts))                   # Copy type options (if any) into field options (JADN extension)
        if fname.endswith('/'):
            fo.update({'dir': True})
            fname = fname.rstrip('/')
        if m := re.match(r'^(\d+)\.\.(\d+|\*)|(\d+)$', fmult) if fmult else None:
            if m.group(3):
                minc = int(m.group(3))
                maxc = minc
            else:
                minc = int(m.group(1))
                maxc = 0 if m.group(2) == '*' else int(m.group(2))
            fo.update({'minc': minc} if minc != 1 else {})
            fo.update({'maxc': maxc} if maxc != 1 else {})
        elif fmult:
            fo.update({'minc': -1, 'maxc': -1})
        if fopts:
            assert len(fopts) == 1 and fopts[0][0] == OPTION_ID['tagid']    # Update if additional field options defined
            fo.update({'tagid': fopts[0][1:]})      # if field name, MUST update to id after all fields have been read
    if fdesc:
        m = re.match(r'^(?:\s*\/\/)?\s*(.*)$', fdesc)
        fdesc = m.group(1)
        if not fname:
            if m := re.match(r'^([^:]+)::\s*(.*)$', fdesc):
                fname = m.group(1)
                fdesc = m.group(2)
    return [fid, fname, ftyperef, opts_d2s(fo), fdesc] if ftyperef else [fid, fname, fdesc]


def get_config(meta: dict) -> dict:
    config = dict(DEFAULT_CONFIG)
    config.update(meta['config'] if meta and 'config' in meta else {})
    return config


# Schema conversion for object-like use
def object_types(types: List[list]) -> List[TypeDefinition]:
    rtn_types: List[TypeDefinition] = []
    for t in types:
        t = TypeDefinition(*t)
        if t.BaseType == 'Enumerated':
            t.Fields = [EnumFieldDefinition(*f) for f in t.Fields]
        else:
            t.Fields = [GenFieldDefinition(*f) for f in t.Fields]
        rtn_types.append(t)
    return rtn_types


def object_type_schema(schema: dict) -> dict:
    sc = copy.deepcopy(schema)
    sc['types'] = object_types(sc['types'])
    return sc


def list_types(types: List[TypeDefinition]) -> List[list]:
    rtn_types: List[list] = []
    for t in types:
        t.Fields = [list(f) for f in t.Fields]
        rtn_types.append(list(t))
    return rtn_types


def list_type_schema(schema: dict) -> dict:
    sc = copy.deepcopy(schema)
    sc['types'] = list_types(sc['types'])
    return sc
