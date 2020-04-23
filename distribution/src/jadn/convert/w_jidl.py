"""
Translate JADN to JADN Interface Definition Language
"""

from datetime import datetime

from jadn.definitions import *
from jadn.utils import topts_s2d, ftopts_s2d, typestring


def jidl_dumps(jadn):

    def _mult(opts, optional=False):
        lo = opts.pop('minc', 1)
        hi = opts.pop('maxc', 1)
        if hi == 1:
            return '' if lo == 1 else (' optional' if optional else ' [0..1]')
        h = '*' if hi == 0 else str(hi)
        return ' [' + str(lo) + '..' + str(h) + ']'

    def _fieldstr(typestr, opts):
        if 'minc' in opts or 'maxc' in opts:
            return typestr + _mult(opts, optional=True)
        if 'tfield' in opts:
            return typestr + '(&' + opts['tfield'] + ')'
        return typestr

    def line(cw, content, desc):
        fmt = '{:' + str(cw) + '}{}'
        return fmt.format(content.rstrip(), ' // ' + desc if desc else '').rstrip() + '\n'

    meta = jadn['meta'] if 'meta' in jadn else {}
    text = ''
    meta_list = ('title', 'module', 'patch', 'description', 'exports', 'imports')
    for h in meta_list + tuple(set(meta) - set(meta_list)):
        if h in meta:
            text += '{:>12}: {}\n'.format(h, meta[h])

    efmt = ['  {0:4d} {1:15}',          # Enumerated
            '  {0:4d}']                 # Enumerated.ID
    ffmt = ['  {0:4d} {1:15} {2:20}',   # Full
            '  {0:4d} {2:20}']          # Full.ID

    for td in jadn['types']:
        bt = td[BaseType]
        assert is_builtin(bt)
        to = topts_s2d(td[TypeOptions])
        ts = typestring(bt, to)
        flds = '{' if has_fields(bt) or (bt == 'Enumerated' and 'enum' not in to and 'pointer' not in to) else ''
        text += '\n' + line(44, '{} = {} {}'.format(td[TypeName], ts, flds), td[TypeDesc])
        if flds:
            id = 1 if 'id' in to or bt == 'Array' else 0
            for n, f in enumerate(td[Fields]):
                sep = ',' if n < len(td[Fields]) - 1 else ''
                if bt == 'Enumerated':
                    content = efmt[id].format(f[ItemID], f[ItemValue] + sep)
                    desc = (f[ItemValue] + ':: ' if id and f[ItemValue] else '') + f[ItemDesc]
                    text += line(48, content, desc)
                else:
                    ft, fto = ftopts_s2d(f[FieldOptions])
                    fo = {'minc': 1, 'maxc': 1}
                    fo.update(ft)
                    fs = _fieldstr(typestring(f[FieldType], fto), fo) + (' unique' if 'unique' in fto else '')
                    fn = f[FieldName] + ('/' if 'dir' in fo else '')
                    content = ffmt[id].format(f[FieldID], fn, fs + sep)
                    desc = (f[FieldName] + ':: ' if id and f[FieldName] else '') + f[FieldDesc]
                    text += line(48, content, desc)

        text += '}\n' if flds else ''

    return text


def jidl_dump(jadn, fname, source=''):
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write('/* Generated from ' + source + ', ' + datetime.ctime(datetime.now()) + ' */\n\n')
        f.write(jidl_dumps(jadn))
