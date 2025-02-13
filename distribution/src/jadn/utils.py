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
    TypeName, CoreType, TypeOptions, Fields, ItemDesc, FieldID, FieldName, FieldType, FieldOptions, FieldDesc,
    DEFAULT_CONFIG, TYPE_OPTIONS, FIELD_OPTIONS, OPTION_ID, OPTION_TYPES, MAX_DEFAULT, MAX_UNLIMITED,
    is_builtin, has_fields, TypeDefinition,
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


def build_deps(schema: dict[str, list]) -> dict[str, list[str]]:
    """
    Build a Dependency dict: {TypeName: [Dep1, Dep2, ...]}
    Returns dependencies for each type in order and a list of all referenced types.
    A single unreferenced type (root) indicates a fully-connected hierarchy;
    multiple roots indicate disconnected items or hierarchies,
    and no roots indicate a dependency cycle.
    """
    def get_refs(tdef: list) -> list[str]:  # Return all type references from a type definition
        # Options whose value is/has a type name: strip option id
        oids = [OPTION_ID['ktype'], OPTION_ID['vtype'], OPTION_ID['extends'], OPTION_ID['restricts']]
        # Options that enumerate fields: keep option id
        oids2 = [OPTION_ID['enum'], OPTION_ID['pointer']]
        refs = [to[1:] for to in tdef[TypeOptions] if to[0] in oids and not is_builtin(to[1:])]
        refs += ([to[1:] for to in tdef[TypeOptions] if to[0] in oids2])
        if has_fields(tdef[CoreType]):  # Ignore Enumerated
            for f in tdef[Fields]:
                if not is_builtin(f[FieldType]):
                    # Add reference to type name
                    refs.append(f[FieldType])
                # Get refs from type opts in field (extension)
                refs += get_refs(['', f[FieldType], f[FieldOptions], ''])
        return refs

    deps = {t[TypeName]: get_refs(t) for t in schema['types']}
    return deps


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


def topts_s2d(olist: Union[list[OPTION_TYPES], tuple[OPTION_TYPES, ...]], typename: str = None) -> dict:
    """
    Convert list of type definition option strings to options dictionary
    """
    ptype = {'Binary': bytes, 'Boolean': bool, 'Integer': int, 'Number': float, 'String': str}.get(typename, None)
    assert isinstance(olist, (list, tuple)), f'{olist} is not a list'
    topts = {o for o in olist if ord(o[0]) in TYPE_OPTIONS}
    if uopts := {*olist} - topts:
        raise_error(f"Unknown type options: {','.join(uopts)}")
    opts = {}
    for o in topts:
        k, v, _ = TYPE_OPTIONS[ord(o[0])]
        t = v if v else ptype
        if t is None:
            raise_error(f"Invalid type option for {typename}: {k}={o[1:]}")
        opts[k] = t(o[1:])
    return opts


def ftopts_s2d(olist: Union[list[OPTION_TYPES], tuple[OPTION_TYPES, ...]], typename: str = None) -> tuple[dict, dict]:
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
            topts.update(topts_s2d([o], typename))
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
    def can_opts(olist: list[OPTION_TYPES], coretype: str):
        opts_sort(olist)                # Sort options into canonical order (for comparisons)
        fo, to = ftopts_s2d(olist, coretype)      # Remove default size and multiplicity options
        if 'minLength' in to and to['minLength'] == 0:
            del_opt(olist, 'minLength')
        if 'maxLength' in to and to['maxLength'] == MAX_DEFAULT:
            del_opt(olist, 'maxLength')
        if 'minOccurs' in fo and fo['minOccurs'] == 1:
            del_opt(olist, 'minOccurs')
        if 'maxOccurs' in fo and fo['maxOccurs'] == 1:
            del_opt(olist, 'maxOccurs')
        # if coretype == 'Number':           # TODO: fix corner case input = 2.000
        #     minf = get_optx(olist, 'minf')
        #     if minf is not None and '.' not in olist[minf]:
        #         olist[minf] += '.0'
        #     maxf = get_optx(olist, 'maxf')
        #     if maxf is not None and '.' not in olist[maxf]:
        #         olist[maxf] += '.0'

    cschema = copy.deepcopy(schema)     # don't modify original
    for td in cschema['types']:
        can_opts(td[TypeOptions], td[CoreType])
        if td[CoreType] != 'Enumerated':
            for fd in td[Fields]:
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
        m1 = re.match(r'^\s*(!?[-$:\w]+)(?:\[([^]]+)])?$', optstr)   # Typeref: nsid:Name$qualifier
        if m1 is None:
            raise_error(f'TypeString2JADN: unexpected function: {optstr}')
        return OPTION_ID[m1.group(1).lower()] + m1.group(2) if m1.group(2) else m1.group(1)

    topts = {}
    fo = []
    p_name = r'\s*(!?[-.:\w]+)'                     # 1 type name TODO: Use $TypeRef
    p_id = r'(#?)'                                  # 2 'id'
    p_func = r'(?:\(([^)]+)\))?'                    # 3 'ktype', 'vtype', 'enum', 'pointer', 'tagid'
    p_lengthpat = r'\{(.*)\}'                        # 4 'minLength', 'maxLength', 'pattern'
    p_format = r'\s+\/(\w[-\w]*)'                   # 5 'format'
    p_flag = r'\s+(unique|set|unordered|sequence|abstract|final)'    # 6 rest: flags
    p_attr = r'\s+(restricts|extends)\((.+)\)'      # 6 rest: TODO: parse extends/restricts separately for better error
    pattern = fr'^{p_name}{p_id}{p_func}(.*?)\s*$'
    m = re.match(pattern, typestring)
    if m is None:
        raise_error(f'TypeString2JADN: "{typestring}" does not match pattern {pattern}')
    tname = m.group(1)
    if tname[0] == '!':
        fo += [OPTION_ID['not']]
        tname = tname[1:]
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
        # Matches     group(3) = [   group(7) = ]   group(8) = rest
        # [x,y] rest  group(4) = x   group(6) = y
        # [x] rest    group(4) = x
        # x rest      group(2) = x
        rangepat = r'^\s*=\s*(([-\d.]+)|([[(])([-\d.]+)(\s*,\s*([-*\d.]+))?([])]))(.*)$'
        if m := re.match(rangepat, rest):
            rest = m.group(8)
            fn = {'Integer': int, 'Number': float}[tname]
            if x := m.group(2):
                topts.update({'const': fn(x)})
            elif x := m.group(4):
                y = y if (y := m.group(6)) else x
                lo = {'[': 'minInclusive', '(': 'minExclusive'}[m.group(3)]
                hi = {']': 'maxInclusive', ')': 'maxExclusive'}[m.group(7)]
                topts.update({lo: fn(x)})
                topts.update(({hi: fn(y)} if y != '*' else {}))
        else:
            for opt in re.findall(p_lengthpat, rest):
                if m := re.match('pattern=\"(.+)\"', opt):
                    topts.update({'pattern': m.group(1)})
                elif len(x := opt.split('..', maxsplit=1)) == 2:
                    a, b = x
                    a = '*' if a != '*' and int(a) == 0 else a   # Default min size = 0
                    topts.update({} if a == '*' else {'minLength': int(a)})
                    topts.update({} if b == '*' else {'maxLength': int(b)})
                else:
                    raise_error(f'unrecognized arg "{opt}", expected pattern or range')
        for opt in re.findall(p_format, rest):  # TODO: allow multiple formats
            topts.update({'format': opt})
        for opt in re.findall(p_flag, rest):
            topts.update({opt: True})
        for opt in re.findall(p_attr, rest):
            topts.update({opt[0]: opt[1]})
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

    # Length range (single-ended) - default is {0..*}
    # min/max Length: {}
    def _lrange(ops: dict) -> str:
        lo = ops.pop('minLength', 0)
        hi = ops.pop('maxLength', MAX_DEFAULT)
        hs = '*' if hi == MAX_DEFAULT else '.' if hi == MAX_UNLIMITED else str(hi)
        return f'{{{lo}..{hs}}}' if lo != 0 or hs != '*' else ''

    # Value range (double-ended) - default is [*..*]
    # min/max Inclusive: []
    # min/max Exclusive: ()
    def _vrange(ops: dict) -> str:
        lc = '(' if 'minExclusive' in ops else '['
        hc = ')' if 'maxExclusive' in ops else ']'
        lo = ops.pop('minInclusive', ops.pop('minExclusive', '*'))
        hi = ops.pop('maxInclusive', ops.pop('maxExclusive', '*'))
        return f'={lc}{lo}, {hi}{hc}' if lo != '*' or hi != '*' else ''

    opts = topts_s2d(topts, tname)
    txt = '#' if opts.pop('id', None) else ''   # SIDE EFFECT: remove known options from opts.
    if tname in ('ArrayOf', 'MapOf'):
        txt += f"({_kvstr(opts.pop('ktype'))}, " if tname == 'MapOf' else '('
        txt += f"{_kvstr(opts.pop('vtype'))})"

    if v := opts.pop('combine', None):
        txt += f"({ {'O': 'anyOf', 'A': 'allOf', 'X': 'oneOf'}[v]})"

    if v := opts.pop('enum', None):
        txt += f'(Enum[{v}])'

    if v := opts.pop('pointer', None):
        txt += f'(Pointer[{v}])'

    if v := opts.pop('pattern', None):
        txt += f'{{pattern="{v}"}}'

    if v := _vrange(opts):
        txt += v

    if v := _lrange(opts):
        txt += v

    if v := opts.pop('format', None):
        txt += f' /{v}'

    for opt in ('unique', 'set', 'unordered', 'sequence', 'abstract', 'final'):
        if o := opts.pop(opt, None):
            txt += (' ' + opt)

    for opt in ('extends', 'restricts'):
        if o := opts.pop(opt, None):
            txt += f" {opt}({o})"

    return f"{tname}{txt}{f' ?{opts}?' if opts else ''}"  # Flag unrecognized options


def multiplicity_str(opts: dict) -> str:
    lo = opts.get('minOccurs', 1)
    hi = opts.get('maxOccurs', 1)
    hs = '*' if hi <= MAX_DEFAULT else str(hi)
    return f'{hi}' if 0 <= hi == lo else f'{lo}..{hs}'  # 0 <= hi and hi == lo


def id_type(td: list) -> bool:    # True if FieldName is a label in description
    return (td[CoreType] == 'Array'
            or get_optx(td[TypeOptions], 'id') is not None
            or get_optx(td[TypeOptions], 'combine') is not None)


def jadn2fielddef(fdef: list, tdef: list) -> tuple[str, str, str, str]:
    idtype = id_type(tdef)
    fname = '' if idtype else fdef[FieldName]
    fdesc = f'{fdef[FieldName]}:: ' if idtype else ''
    is_enum = tdef[CoreType] == 'Enumerated'
    fdesc += fdef[ItemDesc if is_enum else FieldDesc]
    ftyperef = ''
    fmult = ''

    if not is_enum:
        fo, fto = ftopts_s2d(fdef[FieldOptions], fdef[FieldType])
        fname += '/' if 'dir' in fo else ''
        tf = ''
        if tagid := fo.get('tagid', None):
            tf = [f[FieldName] for f in tdef[Fields] if f[FieldID] == tagid][0]
            tf = f'(TagId[{tf if tf else tagid}])'
        ft = jadn2typestr(f'{fdef[FieldType]}{tf}', opts_d2s(fto))
        fnot = '!' if 'not' in fo else ''
        ftyperef = f'Key({ft})' if 'key' in fo else f'Link({ft})' if 'link' in fo else fnot + ft
        fmult = multiplicity_str(fo)
    return fname, ftyperef, fmult, fdesc


def fielddef2jadn(fid: int, fname: str, fstr: str, fmult: str, fdesc: str) -> list:
    def fopts_s2d(olist: list) -> dict:
        fd = {}
        for o in olist:
            k, v, _ = FIELD_OPTIONS[ord(o[0])]
            fd[k] = o[1:]
        return fd

    ftyperef = ''
    fo = {}
    if fstr:
        if m := re.match(r'^(Link|Key)\((.*)\)$', fstr):
            fo = {m.group(1).lower(): True}
            fstr = m.group(2)
        ftyperef, topts, fopts = typestr2jadn(fstr)
        # Field is one of: enum#, enum, field#, field
        fo.update(topts_s2d(topts, ftyperef))                   # Copy type options (if any) into field options (JADN extension)
        if fname.endswith('/'):
            fo.update({'dir': True})
            fname = fname.rstrip('/')
        if m := re.match(r'^(\d+)(?:\.\.(\d+|\*))?$', fmult) if fmult else None:
            groups = m.groups()
            if maxOccurs := groups[1]:
                minOccurs = int(groups[0])
                maxOccurs = -1 if maxOccurs == '*' else int(maxOccurs)
            else:
                minOccurs = maxOccurs = int(groups[0])
            fo.update({'minOccurs': minOccurs} if minOccurs != 1 else {})
            fo.update({'maxOccurs': maxOccurs} if maxOccurs != 1 else {})
        elif fmult:
            fo.update({'minOccurs': -1, 'maxOccurs': -1})
        fo.update(fopts_s2d(fopts))
        # if fopts:
        #     assert len(fopts) == 1 and fopts[0][0] == OPTION_ID['tagid']    # Update if additional field options defined
        #     fo.update({'tagid': fopts[0][1:]})      # if field name, MUST update to id after all fields have been read
    if fdesc:
        m = re.match(r'^(?:\s*\/\/)?\s*(.*)$', fdesc)
        fdesc = m.group(1)
        if not fname:
            if m := re.match(r'^([^:]+)::\s*(.*)$', fdesc):
                fname = m.group(1)
                fdesc = m.group(2)
    return [fid, fname, ftyperef, opts_d2s(fo), fdesc] if ftyperef else [fid, fname, fdesc]


def get_config(schema: dict) -> dict:
    config = dict(DEFAULT_CONFIG)
    config.update(schema.get('meta', {}).get('config', {}))
    ns = config.get('$NSID', '').lstrip('^').rstrip('$')    # Derived $TypeRef pattern
    tn = config.get('$TypeName', '').lstrip('^').rstrip('$')
    config.update({'$TypeRef': fr'^({ns}(?<=.):)?{tn}$'})   # Non-empty prefix before ':'
    return config


# Schema conversion for object-like use
def object_types(types: list[list]) -> list[TypeDefinition]:
    rtn_types: list[TypeDefinition] = []
    for t in types:
        t = TypeDefinition(*t)
        if t.CoreType == 'Enumerated':
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
