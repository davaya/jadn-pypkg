"""
Support functions for JADN codec
  Convert dict between nested and flat
  Convert typedef options between dict and strings
"""

import re
from functools import reduce
from jadn.definitions import *


def raise_error(*s):                     # Handle errors
    raise ValueError(*s)


# Dict conversion utilities


def _dmerge(x, y):
    k, v = next(iter(y.items()))
    if k in x:
        _dmerge(x[k], v)
    else:
        x[k] = v
    return x


def hdict(keys, value, sep='.'):
    """
    Convert a hierarchical-key value pair to a nested dict
    """
    return reduce(lambda v, k: {k: v}, reversed(keys.split(sep)), value)


def fluff(src, sep='.'):
    """
    Convert a flat dict with hierarchical keys to a nested dict

    :param src: flat dict - e.g., {'a.b.c': 1, 'a.b.d': 2}
    :param sep: separator character for keys
    :return: nested dict - e.g., {'a': {'b': {'c': 1, 'd': 2}}}
    """
    return reduce(lambda x, y: _dmerge(x, y), [hdict(k, v, sep) for k, v in src.items()], {})


def flatten(cmd, path='', fc=None, sep='.'):
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


def dlist(src):
    """
    Convert dicts with numeric keys to lists

    :param src: {'a': {'b': {'0':'red', '1':'blue'}, 'c': 'foo'}}
    :return: {'a': {'b': ['red', 'blue'], 'c': 'foo'}}
    """
    if isinstance(src, dict):
        for k in src:
            src[k] = dlist(src[k])
        if set(src) == set([str(k) for k in range(len(src))]):
            src = [src[str(k)] for k in range(len(src))]
    return src


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


def topo_sort(items):
    """
    Topological sort with locality
    Sorts a list of (item: (dependencies)) pairs so that 1) all dependency items are listed before the parent item,
    and 2) dependencies are listed in the given order and as close to the parent as possible.
    Returns the sorted list of items and a list of root items.  A single root indicates a fully-connected hierarchy;
    multiple roots indicate disconnected items or hierarchies, and no roots indicate a dependency cycle.
    """
    def walk_tree(it):
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


def get_optx(opts, oname):
    n = [i for i, x in enumerate(opts) if x[0] == OPTION_ID[oname]]
    return n[0] if n else None


def del_opt(opts, oname):
    n = [i for i, x in enumerate(opts) if x[0] == OPTION_ID[oname]]
    if n:
        del opts[n[0]]


def topts_s2d(olist):        # Convert list of type definition option strings to options dictionary
    tval = {
        'id': lambda x: True,
        'vtype': lambda x: x,
        'ktype': lambda x: x,
        'enum': lambda x: x,
        'pointer': lambda x: x,
        'format': lambda x: x,
        'pattern': lambda x: x,
        'minv': lambda x: float(x),
        'maxv': lambda x: float(x),
        'unique': lambda x: True,
        'and': lambda x: x,
        'or': lambda x: x,
    }
    assert set(tval) == {k for k in TYPE_OPTIONS.values()}
    assert isinstance(olist, (list, tuple)), f'{olist} is not a list'
    opts = {}
    for o in olist:
        try:
            k = TYPE_OPTIONS[ord(o[0])]
            opts[k] = tval[k](o[1:])
        except KeyError:
            raise_error(f'Unknown type option: {o}')
    return opts


def ftopts_s2d(olist):       # Convert list of field definition option strings to options dictionary
    fval = {
        'minc': lambda x: int(x),
        'maxc': lambda x: int(x),
        'dir': lambda x: True,
        'tfield': lambda x: int(x),
        'default': lambda x: x,
    }
    assert set(fval) == {k for k in FIELD_OPTIONS.values()}
    assert isinstance(olist, (list, tuple)), f'{olist} is not a list'
    fopts, topts = {}, {}
    for o in olist:
        try:
            k = FIELD_OPTIONS[ord(o[0])]
            fopts[k] = fval[k](o[1:])
        except KeyError:
            topts.update(topts_s2d([o]))
    return fopts, topts


def opts_d2s(to):
    return [OPTION_ID[k] + ('' if v is True else str(v)) for k, v in to.items()]


def opts_sort(olist):      # Sort JADN option list into canonical order
    return sorted(olist, key=lambda x: OPTION_ORDER[x[0]])


def typestr2jadn(typestring):
    topts = {}
    p_name = r'([:\w$-]+)'              # 1 type name
    p_id = r'(.ID)?'                    # 2 'id'
    p_func = r'(\(\w+\))?'              # 3 'ktype', 'vtype', 'enum', 'pointer'
    p_range = r'(?:\s*\{(.*)\})?'       # 4 'minv', 'maxv'
    p_format = r'(?:\s*\/(\w[-\w]*))?'  # 5 'format'
    p_pattern = r'(?:\s*\(%(.+)%\))?'   # 6 'pattern'
    p_unique = r'\s*(unique)?'          # 7 'unique'
    pattern = '^' + p_name + p_id + p_func + p_range + p_format + p_pattern + p_unique + '$'
    m = re.match(pattern, typestring)
    tname = m.group(1)
    topts.update({'id': True} if m.group(2) else {})
    func = m.group(3)                   # TODO: (ktype, vtype), Enum(), Pointer() options
    if m.group(4):
        a, b = m.group(4).split('..', maxsplit=1)
        topts.update({} if a == '*' else {'minv': float(a)})
        topts.update({} if b == '*' else {'maxv': float(b)})
    topts.update({'format': m.group(5)} if m.group(5) else {})
    topts.update({'pattern': m.group(6)} if m.group(6) else {})
    topts.update({'unique': True} if m.group(7) else {})
    return tname, opts_d2s(topts)


def jadn2typestr(tname, topts):     # Convert typename and options to string

    def _kvstr(optv):               # Handle ktype/vtype containing Enum options
        if optv[0] == OPTION_ID['enum']:
            return 'Enum(' + optv[1:] + ')'
        elif optv[0] == OPTION_ID['pointer']:
            return 'Pointer(' + optv[1:] + ')'
        return optv

    def _srange(ops):               # Size range (single-ended) - default is {0..*}
        lo = ops.pop('minv', 0)
        hi = ops.pop('maxv', 0)
        hs = '*' if hi == 0 else str(hi)
        return str(lo) + '..' + hs if lo != 0 or hi != 0 else ''

    def _vrange(ops):               # Value range (double-ended) - default is {*..*}
        lo = ops.pop('minv', '*')
        hi = ops.pop('maxv', '*')
        return str(lo) + '..' + str(hi) if lo != '*' or hi != '*' else ''

    opts = topts_s2d(topts)
    extra = '.ID' if opts.pop('id', None) else ''   # SIDE EFFECT!: remove known options from opts.
    if tname == 'ArrayOf':
        extra += '(' + _kvstr(opts.pop('vtype')) + ')'
    elif tname == 'MapOf':
        extra += '(' + _kvstr(opts.pop('ktype')) + ', ' + _kvstr(opts.pop('vtype')) + ')'
    v = opts.pop('enum', None)
    extra += '(Enum(' + v + '))' if v else ''
    v = opts.pop('pointer', None)
    extra += '(Pointer(' + v + '))' if v else ''
    v = opts.pop('pattern', None)
    extra += '(%' + v + '%)' if v else ''
    v = _vrange(opts) if tname in ('Integer', 'Number') else _srange(opts)
    extra += '{' + v + '}' if v else ''
    v = opts.pop('format', None)
    extra += ' /' + v if v else ''
    v = opts.pop('unique', None)
    extra += ' unique' if v else ''
    v = opts.pop('and', None)           # hack set operations for now.  TODO: generalize to any number
    extra += ' ∩ ' + v if v else ''
    v = opts.pop('or', None)
    extra += ' ∪ ' + v if v else ''
    return tname + extra + (' ?' + str([str(k) for k in opts]) + '?' if opts else '')  # Flag unrecognized options


def jadn2fielddef(fdef, tdef):
    """
    fopts = minc, maxc, tfield, dir, default

    ft, fto = ftopts_s2d(fdef[FieldOptions])
    fo = {'minc': 1, 'maxc': 1}
    fo.update(ft)
    etree.SubElement(he3, 'div', {'class': 'tCell jFstr'}).text = jadn2typestr(fdef[FieldType], fto)
    etree.SubElement(he3, 'div', {'class': 'tCell jFmult'}).text = multiplicity(fo['minc'], fo['maxc'])
    etree.SubElement(he3, 'div', {'class': 'tCell jFdesc'}).text = fdef[FieldDesc]
    """

    idt = get_optx(tdef[TypeOptions], 'id') is not None
    fo, fto = ftopts_s2d(fdef[FieldOptions])
    fname = ('' if idt else fdef[FieldName]) + ('/' if 'dir' in fo else '')  # TODO: process tfield
    tfield = fo.get('tfield')
    tf = ''
    if tfield:
        tf = {f[FieldID]: f[FieldName] for f in tdef[Fields]}[tfield]
        tf = tf if tf else str(tfield)
        tf = '(Tag(' + tf + '))'
    ftyperef = jadn2typestr(fdef[FieldType] + tf, opts_d2s(fto))
    minc, maxc = fo.get('minc', 1), fo.get('maxc', 1)
    fmult = '1' if minc == 1 and maxc == 1 else str(minc) + '..' + ('*' if maxc == 0 else str(maxc))
    fdesc = (fdef[FieldName] + ':: ' if idt else '') + fdef[FieldDesc]
    return fname, ftyperef, fmult, fdesc


def fielddef2jadn(fname, fstr, fmult, fdesc):
    ftyperef, fopts = typestr2jadn(fstr)
    # one of: enum.id, enum, field.id, field
    fo = topts_s2d(fopts)
    fo.update({} if fname else {'id': True})
    m = re.match(r'^(\d+)\.\.(\d+|\*)$', fmult)
    if m:
        minc = int(m.group(1))
        maxc = 0 if m.group(2) == '*' else int(m.group(2))
        fo.update({'minc': minc} if minc != 1 else {})
        fo.update({'maxc': maxc} if maxc != 1 else {})
    return [fname, ftyperef, opts_sort(opts_d2s(fo)), fdesc] if ftyperef else [fname, fdesc]


def get_config(meta):
    config = dict(DEFAULT_CONFIG)
    config.update(meta['config'] if meta and 'config' in meta else {})
    return config
