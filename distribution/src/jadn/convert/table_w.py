"""
Translate JADN to HTML or Markdown property tables
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, NoReturn, Type, Union
from ..definitions import (
    TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemID, ItemValue, ItemDesc, FieldID, INFO_ORDER, SIMPLE_TYPES,
    is_builtin
)
from ..utils import jadn2fielddef, jadn2typestr, topts_s2d


# --------- Basic Conversion Class -----------------
class BasicConversion:
    """
    Basic JADN -> FORMAT conversion class

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
    doc: str
    schema: dict

    def __init__(self, schema: dict):
        self.doc = ''
        self.schema = schema
        # What happens here?

    def convert(self) -> str:
        self.doc = self.doc_begin()
        self.doc += self.write_meta()
        self.doc += self.write_types()
        self.doc += self.doc_end()
        return self.doc

    # Helper functions
    def write_meta(self) -> str:
        meta = ''
        if info := self.schema.get('info', None):
            meta += self.meta_begin()
            mlist = [k for k in INFO_ORDER if k in info]
            for h in mlist + list(set(info) - set(mlist)):
                mh = info[h]
                meta += self.meta_item(h, mh)
            meta += self.meta_end()
        return meta

    def write_types(self) -> str:
        types = ''
        for td in self.schema['types']:
            ttype = jadn2typestr(td[BaseType], td[TypeOptions])
            to = topts_s2d(td[TypeOptions])
            if not is_builtin(td[BaseType]):
                types += 'Error - bad type: ' + str(td) + '\n'
            elif td[BaseType] in (SIMPLE_TYPES + ('ArrayOf', 'MapOf')) or 'enum' in to or 'pointer' in to:
                cls = ['b', 's', 'd']
                types += self.type_begin('', '', ['Type Name', 'Type Definition', 'Description'], cls)
                types += self.type_item([td[TypeName], ttype, td[TypeDesc]], cls)
            elif td[BaseType] == 'Enumerated':
                cls = ['n', 'b', 'd']
                types += self._tbegin(to, td[TypeName], ttype, ['ID', 'Name', 'Description'], cls)
                for fd in td[Fields]:
                    types += self._titem(to, [str(fd[ItemID]), fd[ItemValue], fd[ItemDesc]], cls)
            else:  # Array, Choice, Map, Record
                cls = ['n', 'b', 's', 'n', 'd']
                if td[BaseType] == 'Array':
                    cls2 = ['n', 's', 'n', 'd']  # Don't print ".ID" in type name but display fields as compact
                    types += self._tbegin(to, td[TypeName], ttype, ['ID', 'Type', '#', 'Description'], cls2)
                    # to.update({'id': None})
                else:
                    types += self._tbegin(to, td[TypeName], ttype, ['ID', 'Name', 'Type', '#', 'Description'], cls)
                for fd in td[Fields]:
                    fn, ftype, fmult, fdesc = jadn2fielddef(fd, td)
                    types += self._titem(to, [str(fd[FieldID]), fn, ftype, fmult, fdesc], cls)
            types += self.type_end()
        return types

    # Override functions
    def doc_begin(self) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `doc_begin`')

    def doc_end(self) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `doc_end`')

    def sect(self, num, name) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `sect`')

    def meta_begin(self) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `meta_begin`')

    def meta_item(self, key: str, val: Union[dict, list, str]) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `meta_item`')

    def meta_end(self) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `meta_end`')

    def type_begin(self, tname: str, ttype: str, headers: List[str], cls: List[str]) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `type_begin`')

    def type_item(self, row: list, cls: list) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `type_item`')

    def type_end(self) -> str:
        raise NotImplementedError(f'{self.__class__.__name__} does not implement `type_end`')

    # Utility functions
    def _tbegin(self, to: dict, name: str, tdef: str, head: List[str], cls: List[str]) -> str:
        h = head
        c = cls
        if 'id' in to:
            h = [head[0]] + head[2:]
            c = [cls[0]] + cls[2:]
        return self.type_begin(name, tdef, h, c)

    def _titem(self, to: dict, fitems: List[str], cls: List[str]) -> str:
        f = fitems
        c = cls
        if 'id' in to:
            f = [fitems[0]] + fitems[2:]
            label = '**' + fitems[1] + '**::' if fitems[1] else ''
            f[-1] = label + f[-1]
            c = [cls[0]] + cls[2:]
        return self.type_item(f, c)


# --------- Markdown output -----------------
class MarkdownConversion(BasicConversion):
    def doc_begin(self) -> str:
        return '## Schema\n'

    def doc_end(self) -> str:
        return ''

    def sect(self, num, name) -> str:
        # n = '.'.join([str(n) for n in num]) + ' '
        # return '\n' + len(num)*'#' + ' ' + n + name + '\n'
        return ''

    def meta_begin(self) -> str:
        return '| . | . |\n| ---: | :--- |\n'

    def meta_item(self, key: str, val: Union[dict, list, str]) -> str:
        if key == 'exports':
            sval = ', '.join(val)
        elif key in ('imports', 'config'):
            sval = ' '.join(['**' + k + '**:&nbsp;' + str(v).replace('|', '&vert;') for k, v in val.items()])
        else:
            sval = val
        return f'| **{key}:** | {sval} |\n'

    def meta_end(self) -> str:
        return ''

    def type_begin(self, tname: str, ttype: str, headers: List[str], cls: List[str]) -> str:
        assert len(headers) == len(cls)
        ch = {'n': '---:', 'h': '---:', 's': ':---', 'd': ':---', 'b': ':---'}
        clh = [ch[c] if c in ch else '---' for c in cls]
        to = f' ({ttype})' if ttype else ''
        tc = f'\n**_Type: {tname}{to}_**' if tname else ''
        return f"{tc}\n\n| {' | '.join(headers)} |\n| {' | '.join(clh)} |\n"

    def type_item(self, row: list, cls: list) -> str:
        assert len(row) == len(cls)
        return f"| {' | '.join([self._fmt(*r) for r in zip(row, cls)])} |\n"

    def type_end(self) -> str:
        return ''

    # Utility functions
    def _fmt(self, s: str, f: str) -> str:
        f1 = {'n': '', 's': '', 'd': '', 'b': '**', 'h': '**_'}
        f2 = {'n': '', 's': '', 'd': '', 'b': '**', 'h': '_**'}
        ss = '\\*' if s == '*' else s
        return f'{f1[f]}{ss}{f2[f]}'


# ---------- JADN Source (JAS) output ------------------
class JasConversion(BasicConversion):
    def doc_begin(self) -> str:
        return ''

    def doc_end(self) -> str:
        return ''

    def sect(self, num, name) -> str:
        return ''

    def meta_begin(self) -> str:
        return ''

    def meta_item(self, key: str, val: Union[dict, list, str]) -> str:
        return ''

    def meta_end(self) -> str:
        return ''

    def type_begin(self, tname: str, ttype: str, headers: list, cls: list) -> str:
        assert len(headers) == len(cls)
        return ''

    def type_item(self, row: list, cls: list) -> str:
        assert len(row) == len(cls)
        return ''

    def type_end(self) -> str:
        return ''


# ---------- CDDL output ------------------
class CddlConversion(BasicConversion):
    def doc_begin(self) -> str:
        return ''

    def doc_end(self) -> str:
        return ''

    def sect(self, num, name) -> str:
        return ''

    def meta_begin(self) -> str:
        return ''

    def meta_item(self, key: str, val: Union[dict, list, str]) -> str:
        return ''

    def meta_end(self) -> str:
        return ''

    def type_begin(self, tname: str, ttype: str, headers: list, cls: list) -> str:
        assert len(headers) == len(cls)
        return ''

    def type_item(self, row: list, cls: list) -> str:
        assert len(row) == len(cls)
        return ''

    def type_end(self) -> str:
        return ''


# ---------- Thrift output ------------------
class ThriftConversion(BasicConversion):
    def doc_begin(self) -> str:
        return ''

    def doc_end(self, ) -> str:
        return ''

    def sect(self, num, name) -> str:
        return ''

    def meta_begin(self) -> str:
        return ''

    def meta_item(self, key: str, val: Union[dict, list, str]) -> str:
        return ''

    def meta_end(self, ) -> str:
        return ''

    def type_begin(self, tname: str, ttype: str, headers: list, cls: list) -> str:
        assert len(headers) == len(cls)
        return ''

    def type_item(self, row: list, cls: list) -> str:
        assert len(row) == len(cls)
        return ''

    def type_end(self) -> str:
        return ''


# ----------------------------------------------
class ConversionFormats(str, Enum):
    CDDL = 'cddl'
    JAS = 'jas'
    MarkDown = 'markdown'
    Thrift = 'thrift'


wtab: Dict[ConversionFormats, Type[BasicConversion]] = {
    ConversionFormats.CDDL: CddlConversion,
    ConversionFormats.JAS: JasConversion,
    ConversionFormats.MarkDown: MarkdownConversion,
    ConversionFormats.Thrift: ThriftConversion
}

DEFAULT_FORMAT = ConversionFormats.MarkDown


def table_dumps(schema: dict, form: ConversionFormats = DEFAULT_FORMAT) -> str:
    if cls := wtab.get(form):
        return cls(schema).convert()
    raise ValueError(f'{form} is not a valid conversion format')


def table_dump(schema: dict, fname: Union[bytes, str, int], source='', form: ConversionFormats = DEFAULT_FORMAT) -> NoReturn:
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write(f'<!-- Generated from {source}, {datetime.ctime(datetime.now())}-->\n')
        f.write(table_dumps(schema, form))


__all__ = [
    'ConversionFormats',
    'table_dump',
    'table_dumps'
]
