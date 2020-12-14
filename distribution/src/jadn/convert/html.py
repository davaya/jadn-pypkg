import re
import json

from datetime import datetime
from typing import Dict, Generator, List, NoReturn, Tuple, Union
from xml.dom import minidom
from ..definitions import Fields, ItemID, ItemDesc, FieldID, INFO_ORDER, TypeDefinition
from ..utils import cleanup_tagid, fielddef2jadn, jadn2fielddef, jadn2typestr, typestr2jadn
# TODO: remove lxml??
from lxml import html


"""
Convert JADN schema to and from HTML format

Generated HTML uses "div tables" rather than HTML table elements to support responsive page design.
Css styles for classes beginning with 't' must be defined to render correctly.

Generated HTML includes JADN Schema classes to support parsing.
Css styles for classes beginning with 'j' are not required

CSS class definitions needed to render table layout:
tTable:   display table
tCaption: display table-caption
tHead:    display table-header-group
tHCell:   display table-cell (used in header)
tBody:    display table-row-group
tRow:     display table-row
tCell:    display table-cell (used in body)

JADN schema elements (required for parsing, available for styling):
jKey:     metadata key
jVal:     metadata value
jTname:   TypeName - name of a defined type
jTstr:    String representation of BaseType and TypeOptions
jTdesc:   TypeDesc - description of a type
jFid:     FieldId - integer tag of a field or enumerated item
jFname:   FieldName/ItemValue - name of a field or string value of an enumerated item
jFstr:    String representation of FieldType and FieldOptions (except multiplicity)
jFmult:   String representation of multiplicity FieldOptions
jFdesc:   FieldDesc/ItemDesc - description of a field in a container type or item in an enumerated type

JADN styling classes (not used for parsing):
jMeta:    metadata section
jType:    type definition
jHid:     FieldId
jHname:   FieldName
jHstr:    FieldType + FieldOptions
jHmult:   Multiplicity
jHdesc:   Description
"""

class Tag:
    """
    HTML Tag element
    """
    name: str
    contents: Union[str, List['Tag']]
    attrs: Dict[str, str]
    _escapes = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;'
    }
    _self_closing = ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr')

    def __init__(self, name: str, value: Union[str, 'Tag', List['Tag']] = None, **attrs: Dict[str, str]):
        self.name = name.lower()
        self.attrs = { **attrs }
        if self.name in self._self_closing and value:
            raise ValueError('Self closing tag should not have a value')
        if isinstance(value, str):
            self.contents = self._escape_value(value)
        elif isinstance(value, list):
            self.contents = value
        elif isinstance(value, Tag):
            self.contents = [value]
        else:
            self.contents = []

    def __str__(self) -> str:
        attrs = ' '.join(f'{k}="{v}"' for k, v in self.attrs.items())
        attrs = f' {attrs}' if attrs else ''
        if self.name in self._self_closing:
            return f'<{self.name}{attrs} />'

        value = self.contents if isinstance(self.contents, str) else ''.join(f'{v}' for v in self.contents)
        return f'<{self.name}{attrs}>{value}</{self.name}>'

    def append(self, *value: 'Tag') -> NoReturn:
        if self.name in self._self_closing:
            raise ValueError('Self closing tag should not have a value')
        if isinstance(self.contents, str):
            raise ValueError('Cannot add to string content')
        self.contents.extend(value)

    def prepend(self, *value: 'Tag') -> NoReturn:
        if self.name in self._self_closing:
            raise ValueError('Self closing tag should not have a value')
        if isinstance(self.contents, str):
            raise ValueError('Cannot add to string content')
        self.contents = [*value, *self.contents]

    def _escape_value(self, val: str) -> str:
        return ''.join(self._escapes.get(c, c) for c in val)


# Convert JADN to HTML
def html_dumps(schema: dict) -> str:
    try:
        title = schema['info']['title']
    except KeyError:
        title = 'JADN Schema'

    # Make initial tree
    doc = Tag('html',
        Tag('head', [
            Tag('meta', charset='UTF-8'),
            Tag('title', title),
            Tag('link', rel='stylesheet', href='css/dtheme.css', type='text/css')
        ]),
        lang='en'
    )
    body = Tag('body', Tag('h2', 'Schema'))

    # Add meta elements if present
    if 'info' in schema:
        m_html = Tag('div', **{'class': 'tBody'})
        mlist = [k for k in INFO_ORDER if k in schema['info']]
        for k in mlist + list({*schema['info']} - {*mlist}):
            m_html.append(Tag('div', [
                Tag('div', k + ':', **{'class': 'tCell jKey'}),
                Tag('div', json.dumps(schema['info'][k]), **{'class': 'tCell jVal'})
            ], **{'class': 'tRow'}))
        # top-level element of the metadata table
        body.append(Tag('div', m_html, **{'class': 'tTable jinfo'}))

    # Add type definitions
    for tdef in schema['types']:
        tdef = TypeDefinition(*tdef)
        d_html = Tag('div', # top-level element of a type definition
            Tag('div', [
                Tag('div', [  # container for type definition column
                    Tag('div', tdef.TypeName, **{'class': 'jTname'}),
                    Tag('div', f' = {jadn2typestr(tdef.BaseType, tdef.TypeOptions)}', **{'class': 'jTstr'})
                ], **{'class': 'jTdef'}),
                Tag('div', tdef.TypeDesc or '', **{'class': 'jTdesc'})
            ], **{'class': 'tCaption'}),
        **{'class': 'tTable jType'})

        if len(tdef) > Fields:
            field_head = Tag('div', [
                Tag('div', 'ID', **{'class': 'tHCell jHid'}),
                Tag('div', 'Name', **{'class': 'tHCell jHname'})
            ], **{'class': 'tHead'})
            if tdef.Fields and len(tdef.Fields[0]) > ItemDesc + 1:
                field_head.append(
                    Tag('div', 'Type', **{'class': 'tHCell jHstr'}),
                    Tag('div', '#', **{'class': 'tHCell jHmult'})
                )
            field_head.append(Tag('div', 'Description', **{'class': 'tHCell jHdesc'}))
            d_html.append(field_head)

            fields = Tag('div', **{'class': 'tBody'})
            for fdef in tdef.Fields:
                field_row = Tag('div', **{'class': 'tRow'})
                fname, ftyperef, fmult, fdesc = jadn2fielddef(fdef, tdef)
                if len(tdef.Fields[0]) > ItemDesc + 1:
                    field_row.append(
                        Tag('div', str(fdef[FieldID]), **{'class': 'tCell jFid'}),
                        Tag('div', fname, **{'class': 'tCell jFname'}),
                        Tag('div', ftyperef, **{'class': 'tCell jFstr'}),
                        Tag('div', fmult, **{'class': 'tCell jFmult'})
                    )
                else:
                    field_row.append(
                        Tag('div', str(fdef[ItemID]), **{'class': 'tCell jFid'}),
                        Tag('div', fname, **{'class': 'tCell jFname'})
                    )
                field_row.append(Tag('div', fdesc, **{'class': 'tCell jFdesc'}))
                fields.append(field_row)
            d_html.append(fields)
        body.append(d_html)
    doc.append(body)
    tmp = '\n'.join(minidom.parseString(f'{doc}').toprettyxml().splitlines()[1:])
    return f'<!DOCTYPE html>{tmp}'


def html_dump(schema: dict, fname: Union[bytes, str, int], source='') -> NoReturn:
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write(f'<! Generated from {source}, {datetime.ctime(datetime.now())}>\n\n')
        f.write(html_dumps(schema))


# Convert HTML to JADN
def line2jadn(lt: dict, tdef) -> Tuple[str, list]:
    def default(x: str, d: str) -> str:
        return x if x else d

    if 'jKey' in lt:
        return 'M', [lt['jKey'].rstrip(':'), lt['jVal']]
    if 'jTname' in lt:
        btype, topts, fo = typestr2jadn(lt['jTstr'])
        assert fo == []                     # field options MUST not be included in typedefs
        tdesc = default(lt.get('jTdesc', ''), '')
        if tdesc:
            m = re.match(r'^(?:\s*\/\/)?\s*(.*)$', tdesc)
            tdesc = m.group(1)
        return 'T', [lt['jTname'], btype, topts, tdesc, []]
    if 'jFid' in lt:
        fname = default(lt.get('jFname', ''), '')
        fstr = default(lt.get('jFstr', ''), '')
        fdesc = default(lt.get('jFdesc', ''), '')
        fmult = lt.get('jFmult', '')
        return 'F', fielddef2jadn(int(lt['jFid']), fname, fstr, fmult, fdesc)


def html_loads(hdoc: str) -> dict:
    tclass = ('jKey', 'jVal', 'jTname', 'jTstr', 'jTdesc', 'jFid', 'jFname', 'jFstr', 'jFmult', 'jFdesc')

    # TODO: convert to use minidom
    def get_line(hdoc: str) -> Generator[dict, None, None]:
        line = {}
        for element in html.fromstring(hdoc).iter():
            cl = [c for c in element.get('class', '').split() if c in tclass]  # Get element's token class
            if cl:
                assert len(cl) == 1  # TODO: Can't be more than one - replace assertions with proper errors
                if cl[0] in ('jKey', 'jTname', 'jFid'):
                    if line:
                        yield line
                        line = {}
                line.update({cl[0]: element.text})
        yield line

    meta = {}
    types = []
    fields = None
    for line in get_line(hdoc):
        if line:
            t, v = line2jadn(line, types[-1] if types else None)
            if t == 'F':
                fields.append(v)
            elif fields:
                cleanup_tagid(fields)
                fields = None
            if t == 'M':
                meta.update({v[0]: json.loads(v[1])})
            elif t == 'T':
                types.append(v)
                fields = types[-1][Fields]
    return {'info': meta, 'types': types} if meta else {'types': types}


def html_load(fname: Union[bytes, str, int]) -> dict:
    with open(fname, 'r') as f:
        return html_loads(f.read())
