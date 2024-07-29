"""
Support functions for JADN codec
  Convert dict between nested and flat
  Convert typedef options between dict and strings
"""
import copy
import re

from functools import reduce
from typing import Any, NoReturn, Union
from .definitions import (
    TypeName, BaseType, TypeOptions, Fields, ItemDesc, FieldID, FieldName, FieldType, FieldOptions, FieldDesc,
    DEFAULT_CONFIG, TYPE_OPTIONS, FIELD_OPTIONS, OPTION_ID, OPTION_TYPES, is_builtin, has_fields, TypeDefinition,
    EnumFieldDefinition, GenFieldDefinition
)


# Handle errors
def raise_error(*s) -> NoReturn:
    raise ValueError(*s)


# Truncate a string to "n" characters, replacing end with ".." if truncated
def etrunc(s: str, n: int) -> str:
    return s if n is None else s[:n-2] + (s[n-2:], '..')[len(s) > n] if n > 1 else s[:n]


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


def build_deps(schema: dict[str, list]) -> tuple[dict[str, list[str]], set[str]]:
    """
    Build a Dependency dict: {TypeName: [Dep1, Dep2, ...]}
    Returns dependencies for each type in order and a list of all referenced types.
    A single unreferenced type (root) indicates a fully-connected hierarchy;
    multiple roots indicate disconnected items or hierarchies,
    and no roots indicate a dependency cycle.
    """
    def get_refs(tdef: list) -> list[str]:  # Return all type references from a type definition
        # Options whose value is/has a type name: strip option id
        oids = [OPTION_ID['ktype'], OPTION_ID['vtype']]
        # Options that enumerate fields: keep option id
        oids2 = [OPTION_ID['enum'], OPTION_ID['pointer']]
        refs = [to[1:] for to in tdef[TypeOptions] if to[0] in oids and not is_builtin(to[1:])]
        refs += ([to for to in tdef[TypeOptions] if to[0] in oids2])
        if has_fields(tdef[BaseType]):  # Ignore Enumerated
            for f in tdef[Fields]:
                if not is_builtin(f[FieldType]):
                    # Add reference to type name
                    refs.append(f[FieldType])
                # Get refs from type opts in field (extension)
                refs += get_refs(['', f[FieldType], f[FieldOptions], ''])
        return refs

    deps = {t[TypeName]: get_refs(t) for t in schema['types']}
    refs = {v for d in deps for v in deps[d]}
    return deps, refs


def topo_sort(deps: dict[str, list[str]], roots: list[str]) -> list[str]:
    """
    Topological sort with locality
    Sorts a list of (item: (dependencies)) pairs so that 1) all dependency items are listed after the parent item,
    and 2) dependencies are listed in the input order and as close to the parent as possible.
    Returns the sorted list of items.
    """
    out: list[str] = []

    def walk_tree(it: str) -> None:
        if it not in out:
            out.append(it)
            for i in deps.get(it, []):
                walk_tree(i)

    for item in roots:
        walk_tree(item)
    out = out if out else list(deps)     # if cycle detected, don't sort
    return out


def get_optx(opts: list[OPTION_TYPES], oname: str) -> Union[OPTION_TYPES, None]:
    if n := [i for i, x in enumerate(opts) if x[0] == OPTION_ID[oname]]:
        return n[0]
    return None


def del_opt(opts: list[OPTION_TYPES], oname: str) -> None:
    if n := [i for i, x in enumerate(opts) if x[0] == OPTION_ID[oname]]:
        del opts[n[0]]


def topts_s2d(olist: Union[list[OPTION_TYPES], tuple[OPTION_TYPES, ...]], frange: bool = False) -> dict:
    """
    Convert list of type definition option strings to options dictionary
    """
    assert isinstance(olist, (list, tuple)), f'{olist} is not a list'
    topts = {o for o in olist if ord(o[0]) in TYPE_OPTIONS}
    if uopts := {*olist} - topts:
        raise_error(f"Unknown type options: {','.join(uopts)}")
    opts = {}
    for o in topts:
        k, v, _ = TYPE_OPTIONS[ord(o[0])]
        opts[k] = v(o[1:])
    return opts


def ftopts_s2d(olist: Union[list[OPTION_TYPES], tuple[OPTION_TYPES, ...]]) -> tuple[dict, dict]:
    """
    Convert list of field definition option strings to options dictionary
    returns - FieldOptions, TypeOptions
    """
    assert isinstance(olist, (list, tuple)), f'{olist} is not a list'
    fopts = {}
    topts = {}
    for o in olist:
        try:
            k, v, _ = FIELD_OPTIONS[ord(o[0])]
            fopts[k] = v(o[1:])
        except KeyError:
            topts.update(topts_s2d([o]))
    return fopts, topts


def opts_d2s(to: dict) -> list[str]:
    rtn: list[str] = []
    for k, v in to.items():
        try:
            rtn.append(f"{OPTION_ID[k]}{'' if v is True else str(v)}")
        except KeyError:
            raise_error(f'Unknown option tag {k}')
    return rtn


def opts_sort(olist: Union[list[OPTION_TYPES], tuple[OPTION_TYPES, ...]]) -> None:
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
    def can_opts(olist: list[OPTION_TYPES], basetype: str):
        opts_sort(olist)                # Sort options into canonical order (for comparisons)
        fo, to = ftopts_s2d(olist)      # Remove default size and multiplicity options
        if 'minv' in to and to['minv'] == 0 and basetype != 'Integer':
            del_opt(olist, 'minv')
        if 'minc' in fo and fo['minc'] == 1:
            del_opt(olist, 'minc')
        if 'maxc' in fo and fo['maxc'] == 1:
            del_opt(olist, 'maxc')
        if basetype == 'Number':           # TODO: fix corner case input = 2.000
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


def cleanup_tagid(fields: list[list]) -> list[list]:
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


def typestr2jadn(typestring: str) -> tuple[str, list[str], list]:
    def parseopt(optstr: str) -> str:
        m1 = re.match(r'^\s*([-$:\w]+)(?:\[([^]]+)])?$', optstr)   # Typeref: nsid:Name$qualifier
        if m1 is None:
            raise_error(f'TypeString2JADN: unexpected function: {optstr}')
        return OPTION_ID[m1.group(1).lower()] + m1.group(2) if m1.group(2) else m1.group(1)

    topts = {}
    fo = []
    p_name = r'\s*=?\s*([-$:\w]+)'                  # 1 type name
    p_id = r'(\.ID)?'                               # 2 'id'
    p_func = r'(?:\(([^)]+)\))?'                    # 3 'ktype', 'vtype', 'enum', 'pointer', 'tagid'
    p_rangepat = r'\{(.*)\}'                        # 4 'minv', 'maxv', 'pattern'
    p_format = r'\s+\/(\w[-\w]*)'                   # 5 'format'
    p_kw = r'\s+(unique|set|unordered|sequence)'    # 6 multiplicity
    pattern = fr'^{p_name}{p_id}{p_func}(.*?)\s*$'
    m = re.match(pattern, typestring)
    if m is None:
        raise_error(f'TypeString2JADN: "{typestring}" does not match pattern {pattern}')
    tname = m.group(1)
    topts.update({'id': True} if m.group(2) else {})
    if m.group(3):                      # (ktype, vtype), Enum(), Pointer(), Choice() options
        opts = [parseopt(x) for x in m.group(3).split(',', maxsplit=1)]
        assert len(opts) == (2 if tname == 'MapOf' else 1)  # TODO: raise proper error message
        if tname == 'MapOf':
            topts.update({'ktype': opts[0], 'vtype': opts[1]})
        elif tname == 'ArrayOf':
            topts.update({'vtype': opts[0]})
        elif tname == 'Choice':
            topts.update({'combine': {'anyOf': 'O', 'allOf': 'A', 'oneOf': 'X'}[opts[0]]})
        else:
            topts.update(topts_s2d([opts[0]]) if ord(opts[0][0]) in TYPE_OPTIONS else {})
            fo += [opts[0]] if ord(opts[0][0]) in FIELD_OPTIONS else []         # TagId option
    if rest := m.group(4):
        for opt in re.findall(p_rangepat, rest):
            if m := re.match('pattern=\"(.+)\"', opt):
                topts.update({'pattern': m.group(1)})
            else:
                a, b = opt.split('..', maxsplit=1)
                if tname == 'Number':
                    topts.update({} if a == '*' else {'minf': float(a)})
                    topts.update({} if b == '*' else {'maxf': float(b)})
                else:
                    a = '*' if tname != 'Integer' and a != '*' and int(a) == 0 else a   # Default min size = 0
                    topts.update({} if a == '*' else {'minv': int(a)})
                    topts.update({} if b == '*' else {'maxv': int(b)})
        for opt in re.findall(p_format, rest):
            topts.update({'format': opt})
        for opt in re.findall(p_kw, rest):
            topts.update({opt: True})
    return tname, opts_d2s(topts), fo


def jadn2typestr(tname: str, topts: list[OPTION_TYPES]) -> str:
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
    if tname in ('ArrayOf', 'MapOf'):
        extra += f"({_kvstr(opts.pop('ktype'))}, " if tname == 'MapOf' else '('
        extra += f"{_kvstr(opts.pop('vtype'))})"

    if v := opts.pop('combine', None):
        extra += f"({ {'O': 'anyOf', 'A': 'allOf', 'X': 'oneOf'}[v]})"

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

    if opts.pop('set', None):
        extra += ' set'

    if opts.pop('unordered', None):
        extra += ' unordered'

    if opts.pop('sequence', None):
        extra += ' sequence'
    return f"{tname}{extra}{f' ?{str(map(str, opts))}?' if opts else ''}"  # Flag unrecognized options


def multiplicity_str(opts: dict) -> str:
    lo = opts.get('minc', 1)
    hi = opts.get('maxc', 1)
    hs = '*' if hi < 1 else str(hi)
    return f'{lo}..{hs}' if lo != 1 or hi != 1 else '1'


def id_type(td: list) -> bool:    # True if FieldName is a label in description
    return (td[BaseType] == 'Array'
            or get_optx(td[TypeOptions], 'id') is not None
            or get_optx(td[TypeOptions], 'combine') is not None)


def jadn2fielddef(fdef: list, tdef: list) -> tuple[str, str, str, str]:
    idtype = id_type(tdef)
    fname = '' if idtype else fdef[FieldName]
    fdesc = f'{fdef[FieldName]}:: ' if idtype else ''
    is_enum = tdef[BaseType] == 'Enumerated'
    fdesc += fdef[ItemDesc if is_enum else FieldDesc]
    ftyperef = ''
    fmult = ''

    if not is_enum:
        fo, fto = ftopts_s2d(fdef[FieldOptions])
        fname += '/' if 'dir' in fo else ''
        tf = ''
        if tagid := fo.get('tagid', None):
            tf = [f[FieldName] for f in tdef[Fields] if f[FieldID] == tagid][0]
            tf = f'(TagId[{tf if tf else tagid}])'
        ft = jadn2typestr(f'{fdef[FieldType]}{tf}', opts_d2s(fto))
        ftyperef = f'Key({ft})' if 'key' in fo else f'Link({ft})' if 'link' in fo else ft
        fmult = multiplicity_str(fo)
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
        if m := re.match(r'^(\d+)(?:\.\.(\d+|\*))?$', fmult) if fmult else None:
            groups = m.groups()
            if maxc := groups[1]:
                minc = int(groups[0])
                maxc = 0 if maxc == '*' else int(maxc)
            else:
                minc = maxc = int(groups[0])
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
    if meta:
        config.update(meta.get('config', {}))
    return config


# Schema conversion for object-like use
def object_types(types: list[list]) -> list[TypeDefinition]:
    rtn_types: list[TypeDefinition] = []
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


def list_types(types: list[TypeDefinition]) -> list[list]:
    return [[*t[:-1], [list(f) for f in t.Fields]] for t in types]


def list_type_schema(schema: dict) -> dict:
    sc = copy.deepcopy(schema)
    sc['types'] = list_types(sc['types'])
    return sc


# General Utilities
def list_get_default(lst: list, idx: int, default: Any = None) -> Any:
    try:
        return lst[idx]
    except IndexError:
        return default
