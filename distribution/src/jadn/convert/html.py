import re
import json

from datetime import datetime
from typing import Generator, NoReturn, Tuple, Union
from lxml import html
from .utils import DocHTML
from ..definitions import Fields, ItemID, ItemDesc, FieldID, INFO_ORDER, TypeDefinition
from ..utils import cleanup_tagid, fielddef2jadn, jadn2fielddef, jadn2typestr, typestr2jadn
from ..core import check
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


# Convert JADN to HTML
def html_dumps(schema: dict) -> str:
    # Make initial tree
    doc, tag = DocHTML('<!DOCTYPE html>', lang='en').context()

    with tag('head'):
        tag('meta', charset='UTF-8')
        tag('title', schema.get('info', {}).get('title', 'JADN Schema'))
        tag('link', rel='stylesheet', href='css/dtheme.css', type='text/css')

    with tag('body'):
        tag('h2', 'Schema')

        # Add meta elements if present
        if info := schema.get('info', None):
            with tag('div', klass='tBody'):
                mlist = [k for k in INFO_ORDER if k in info]
                for k in mlist + list({*info} - {*mlist}):
                    with tag('div', klass='tRow'):
                        tag('div', f'{k}:', klass='tCell jKey')
                        tag('div', json.dumps(info[k]), klass='tCell jVal')
                # top-level element of the metadata table
                tag('div', klass='tTable jinfo')

        # Add type definitions
        for tdef in schema['types']:
            tdef = TypeDefinition(*tdef)
            with tag('div', klass='tTable jType'):  # top-level element of a type definition
                with tag('div', klass='tCaption'):
                    with tag('div', klass='jTdef'):  # container for type definition column
                        tag('div', tdef.TypeName, klass='jTname')
                        tag('div', f' = {jadn2typestr(tdef.BaseType, tdef.TypeOptions)}', klass='jTstr')
                    tag('div', tdef.TypeDesc or '', klass='jTdesc')

                if len(tdef) > Fields:
                    with tag('div', klass='tHead'):
                        tag('div', 'ID', klass='tHCell jHid')
                        tag('div', 'Name', klass='tHCell jHname')
                        if tdef.Fields and len(tdef.Fields[0]) > ItemDesc + 1:
                            tag('div', 'Type', klass='tHCell jHstr')
                            tag('div', '#', klass='tHCell jHmult')
                        tag('div', 'Description', klass='tHCell jHdesc')

                    with tag('div', klass='tBody'):
                        for fdef in tdef.Fields:
                            with tag('div', klass='tRow'):
                                fname, ftyperef, fmult, fdesc = jadn2fielddef(fdef, [*tdef])
                                if len(tdef.Fields[0]) > ItemDesc + 1:
                                    tag('div', str(fdef[FieldID]), klass='tCell jFid')
                                    tag('div', fname, klass='tCell jFname')
                                    tag('div', ftyperef, klass='tCell jFstr')
                                    tag('div', fmult, klass='tCell jFmult')
                                else:
                                    tag('div', str(fdef[ItemID]), klass='tCell jFid')
                                    tag('div', fname, klass='tCell jFname')
                                tag('div', fdesc, klass='tCell jFdesc')
    return doc.getvalue(True)


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
    return check({'info': meta, 'types': types} if meta else {'types': types})


def html_load(fname: Union[bytes, str, int]) -> dict:
    with open(fname, 'r') as f:
        return html_loads(f.read())


__all__ = [
    'html_dump',
    'html_dumps',
    'html_load',
    'html_loads'
]
