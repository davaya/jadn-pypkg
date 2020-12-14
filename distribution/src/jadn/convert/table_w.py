"""
Translate JADN to HTML or Markdown property tables
"""
from datetime import datetime
from typing import List, NoReturn, Union
from ..definitions import (
    TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemID, ItemValue, ItemDesc, FieldID, INFO_ORDER, SIMPLE_TYPES,
    is_builtin
)
from ..utils import jadn2fielddef, jadn2typestr, topts_s2d


def _fmt(s: str, f: str) -> str:
    f1 = {'n': '', 's': '', 'd': '', 'b': '**', 'h': '**_'}
    f2 = {'n': '', 's': '', 'd': '', 'b': '**', 'h': '_**'}
    ss = '\\*' if s == '*' else s
    return f'{f1[f]}{ss}{f2[f]}'


# --------- Markdown output -----------------
def doc_begin_m() -> str:
    return '## Schema\n'


def doc_end_m() -> str:
    return ''


def sect_m(num, name) -> str:
    # n = '.'.join([str(n) for n in num]) + ' '
    # return '\n' + len(num)*'#' + ' ' + n + name + '\n'
    return ''


def meta_begin_m() -> str:
    return '| . | . |\n| ---: | :--- |\n'


def meta_item_m(h: str, val: Union[dict, list, str]) -> str:
    if h == 'exports':
        sval = ', '.join(val)
    elif h in ('imports', 'config'):
        sval = ' '.join(['**' + k + '**:&nbsp;' + str(v).replace('|', '&vert;') for k, v in val.items()])
    else:
        sval = val
    return '| **' + h + ':** | ' + sval + ' |\n'


def meta_end_m() -> str:
    return ''


def type_begin_m(tname: str, ttype: str, headers: List[str], cls: List[str]) -> str:
    assert len(headers) == len(cls)
    ch = {'n': '---:', 'h': '---:', 's': ':---', 'd': ':---', 'b': ':---'}
    clh = [ch[c] if c in ch else '---' for c in cls]
    to = f' ({ttype})' if ttype else ''
    tc = f'\n**_Type: {tname}{to}_**' if tname else ''
    return f"{tc}\n\n| {' | '.join(headers)} |\n| {' | '.join(clh)} |\n"


def type_item_m(row: list, cls: list) -> str:
    assert len(row) == len(cls)
    return f"| {' | '.join([_fmt(*r) for r in zip(row, cls)])} |\n"


def type_end_m() -> str:
    return ''


# ---------- JADN Source (JAS) output ------------------
def doc_begin_s() -> str:
    return ''


def doc_end_s() -> str:
    return ''


def sect_s(num, name) -> str:
    return ''


def meta_begin_s() -> str:
    return ''


def meta_item_s(key, val) -> str:
    return ''


def meta_end_s() -> str:
    return ''


def type_begin_s(tname: str, ttype: str, headers: list, cls: list) -> str:
    assert len(headers) == len(cls)
    return ''


def type_item_s(row: list, cls: list) -> str:
    assert len(row) == len(cls)
    return ''


def type_end_s() -> str:
    return ''


# ---------- CDDL output ------------------
def doc_begin_c() -> str:
    return ''


def doc_end_c() -> str:
    return ''


def sect_c(num, name) -> str:
    return ''


def meta_begin_c() -> str:
    return ''


def meta_item_c(key, val) -> str:
    return ''


def meta_end_c() -> str:
    return ''


def type_begin_c(tname: str, ttype: str, headers: list, cls: list) -> str:
    assert len(headers) == len(cls)
    return ''


def type_item_c(row: list, cls: list) -> str:
    assert len(row) == len(cls)
    return ''


def type_end_c() -> str:
    return ''


# ---------- Thrift output ------------------
def doc_begin_t() -> str:
    return ''


def doc_end_t() -> str:
    return ''


def sect_t(num, name) -> str:
    return ''


def meta_begin_t() -> str:
    return ''


def meta_item_t(key, val) -> str:
    return ''


def meta_end_t() -> str:
    return ''


def type_begin_t(tname: str, ttype: str, headers: list, cls: list) -> str:
    assert len(headers) == len(cls)
    return ''


def type_item_t(row: list, cls: list) -> str:
    assert len(row) == len(cls)
    return ''


def type_end_t() -> str:
    return ''

# ----------------------------------------------

"""
doc_begin - initial content
doc_end - closing content, if any
sect - section heading for human document formats, nothing for machine-readable schemas
meta_begin - begin meta content
meta_item - most meta items
meta_imps - special handling for imports meta item
meta_end - close meta content
type_begin - begin type definition
type_item - add field to type definition
type_end - close type definition
"""
# TODO: refactor into base and sub classes to support instance context

wtab = {
    'jas': (doc_begin_s, doc_end_s, sect_s, meta_begin_s, meta_item_s, meta_end_s, type_begin_s, type_item_s, type_end_s),
    'cddl': (doc_begin_c, doc_end_c, sect_c, meta_begin_c, meta_item_c, meta_end_c, type_begin_c, type_item_c, type_end_c),
    'thrift': (doc_begin_t, doc_end_t, sect_t, meta_begin_t, meta_item_t, meta_end_t, type_begin_t, type_item_t, type_end_t),
    'markdown': (doc_begin_m, doc_end_m, sect_m, meta_begin_m, meta_item_m, meta_end_m, type_begin_m, type_item_m, type_end_m)
}

DEFAULT_FORMAT = 'markdown'


def table_dumps(schema: dict, form=DEFAULT_FORMAT) -> str:
    """
    Translate JADN schema into other formats

    Column classes for presentation formats:
    n - number (right aligned)
    h - meta header (bold, right aligned)
    s - string (left aligned)
    b - bold (bold, left aligned)
    d - description (left aligned, extra width)
    """
    doc_begin, doc_end, sect, meta_begin, meta_item, meta_end, type_begin, type_item, type_end = wtab[form]
    text = doc_begin()

    def _tbegin(to: dict, name: str, tdef: str, head: List[str], cls: List[str]) -> str:
        h = head
        c = cls
        if 'id' in to:
            h = [head[0]] + head[2:]
            c = [cls[0]] + cls[2:]
        return type_begin(name, tdef, h, c)

    def _titem(to: dict, fitems: List[str], cls: List[str]) -> str:
        f = fitems
        c = cls
        if 'id' in to:
            f = [fitems[0]] + fitems[2:]
            label = '**' + fitems[1] + '**::' if fitems[1] else ''
            f[-1] = label + f[-1]
            c = [cls[0]] + cls[2:]
        return type_item(f, c)

    if 'info' in schema:
        meta = schema['info']
        text += meta_begin()
        mlist = [k for k in INFO_ORDER if k in schema['info']]
        for h in mlist + list(set(schema['info']) - set(mlist)):
            mh = meta[h]
            text += meta_item(h, mh)
        text += meta_end()

    for td in schema['types']:
        ttype = jadn2typestr(td[BaseType], td[TypeOptions])
        to = topts_s2d(td[TypeOptions])
        if not is_builtin(td[BaseType]):
            text += 'Error - bad type: ' + str(td) + '\n'
        elif td[BaseType] in (SIMPLE_TYPES + ('ArrayOf', 'MapOf')) or 'enum' in to or 'pointer' in to:
            cls = ['b', 's', 'd']
            text += type_begin('', None, ['Type Name', 'Type Definition', 'Description'], cls)
            text += type_item([td[TypeName], ttype, td[TypeDesc]], cls)
        elif td[BaseType] == 'Enumerated':
            cls = ['n', 'b', 'd']
            text += _tbegin(to, td[TypeName], ttype, ['ID', 'Name', 'Description'], cls)
            for fd in td[Fields]:
                text += _titem(to, [str(fd[ItemID]), fd[ItemValue], fd[ItemDesc]], cls)
        else:                                       # Array, Choice, Map, Record
            cls = ['n', 'b', 's', 'n', 'd']
            if td[BaseType] == 'Array':
                cls2 = ['n', 's', 'n', 'd']         # Don't print ".ID" in type name but display fields as compact
                text += _tbegin(to, td[TypeName], ttype, ['ID', 'Type', '#', 'Description'], cls2)
                # to.update({'id': None})
            else:
                text += _tbegin(to, td[TypeName], ttype, ['ID', 'Name', 'Type', '#', 'Description'], cls)
            for fd in td[Fields]:
                fn, ftype, fmult, fdesc = jadn2fielddef(fd, td)
                text += _titem(to, [str(fd[FieldID]), fn, ftype, fmult, fdesc], cls)
        text += type_end()

    text += doc_end()
    return text


def table_dump(schema: dict, fname: Union[bytes, str, int], source='', form=DEFAULT_FORMAT) -> NoReturn:
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write(f'<!-- Generated from {source}, {datetime.ctime(datetime.now())}-->\n')
        f.write(table_dumps(schema, form))
