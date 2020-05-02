"""
Support functions for JADN codec
  Convert dict between nested and flat
  Convert typedef options between dict and strings
"""

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


def topts_s2d(olist):        # Convert list of type definition option strings to options dictionary
    tval = {
        'id': lambda x: True,
        'vtype': lambda x: x,
        'ktype': lambda x: x,
        'enum': lambda x: x,
        'pointer': lambda x: x,
        'format': lambda x: x,
        'pattern': lambda x: x,
        'minv': lambda x: int(x),
        'maxv': lambda x: int(x),
        'unique': lambda x: True,
        'and': lambda x: x,
        'or': lambda x: x,
    }

    assert set(tval) == {k for k in TYPE_OPTIONS.values()}
    assert isinstance(olist, (list, tuple)), '%r is not a list' % olist
    opts = {}
    for o in olist:
        try:
            k = TYPE_OPTIONS[ord(o[0])]
            opts[k] = tval[k](o[1:])
        except KeyError:
            raise ValueError('Unknown type option: %s' % o)
    return opts


def ftopts_s2d(ostr):       # Convert list of field definition option strings to options dictionary
    fval = {
        'minc': lambda x: int(x),
        'maxc': lambda x: int(x),
        'tfield': lambda x: x,
        'dir': lambda x: True,
        'default': lambda x: x,
    }

    assert set(fval) == {k for k in FIELD_OPTIONS.values()}
    assert isinstance(ostr, (list, tuple)), '%r is not a list' % ostr
    fopts, topts = {}, {}
    for o in ostr:
        try:
            k = FIELD_OPTIONS[ord(o[0])]
            fopts[k] = fval[k](o[1:])
        except KeyError:
            topts.update(topts_s2d([o]))
    return fopts, topts


def multiplicity(minc, maxc):
    if minc == 1 and maxc == 1:
        return '1'
    return str(minc) + '..' + ('*' if maxc == 0 else str(maxc))


def typestring(typename, typeopts):            # Convert typename and options to string.

    def _typestr(tname, opts):          # SIDE EFFECT: remove known options from opts to flag leftovers

        def _kvstr(optv):               # Handle ktype/vtype containing Enum options
            if optv[0] == OPTION_ID['enum']:
                return 'Enum(' + optv[1:] + ')'
            elif optv[0] == OPTION_ID['pointer']:
                return 'Pointer(' + optv[1:] + ')'
            return optv

        def _rangestr(ops, vrange=False):  # Value range is double-ended: [*..*], Size range is single-ended: [0..*]
            dlo = '*' if vrange else 0
            lo = ops.pop('minv', dlo)
            hi = ops.pop('maxv', '*')
            hi = '*' if hi == 0 and not vrange else hi
            return str(lo) + '..' + str(hi) if lo != dlo or hi != '*' else ''

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
        v = _rangestr(opts, tname in ('Integer', 'Number'))
        extra += '{' + v + '}' if v else ''
        v = opts.pop('format', None)
        extra += ' /' + v if v else ''
        v = opts.pop('unique', None)
        extra += ' unique' if v else ''
        v = opts.pop('and', None)           # hack set operations for now.  TODO: generalize to any number
        extra += ' ∩ ' + v if v else ''
        v = opts.pop('or', None)
        extra += ' ∪ ' + v if v else ''
        return tname + extra

    o2 = typeopts.copy()                        # Don't modify opts
    ts = _typestr(typename, o2)
    return ts + (' ?' + str([str(k) for k in o2]) + '?' if o2 else '')  # Flag unrecognized options


def get_config(meta):
    config = dict(DEFAULT_CONFIG)
    config.update(meta['config'] if meta and 'config' in meta else {})
    return config