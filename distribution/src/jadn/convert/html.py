import re
import json

from datetime import datetime
from lxml import etree, html
# TODO: change to specific imports??
from lxml.html.builder import *
from jadn.definitions import (
    # Field Indexes
    TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemID, ItemDesc, FieldID,
    # Const values
    INFO_ORDER
)
from typing import Generator, NoReturn, Tuple, Union
from jadn import jadn2typestr, typestr2jadn, jadn2fielddef, fielddef2jadn, cleanup_tagid


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

"""
Convert JADN to HTML
"""


def html_dumps(schema: dict) -> str:
    try:
        title = schema['info']['title']
    except KeyError:
        title = 'JADN Schema'
    doc = HTML(
        ATTR({'lang': 'en'}),        # Make initial etree
        HEAD(
            META(charset='UTF-8'),
            TITLE(title),
            LINK(rel='stylesheet', href='css/dtheme.css', type='text/css')
        ),
        BODY(
            H2('Schema')
        )
    )
    body = doc.find('body')

    if 'info' in schema:                    # Add meta elements if present
        het = etree.Element('div', {'class': 'tTable jinfo'})       # top-level element of the metadata table
        he2 = etree.SubElement(het, 'div', {'class': 'tBody'})
        mlist = [k for k in INFO_ORDER if k in schema['info']]
        for k in mlist + list(set(schema['info']) - set(mlist)):
            he3 = etree.SubElement(he2, 'div', {'class': 'tRow'})
            etree.SubElement(he3, 'div', {'class': 'tCell jKey'}).text = k + ':'
            etree.SubElement(he3, 'div', {'class': 'tCell jVal'}).text = json.dumps(schema['info'][k])
        body.append(het)

    for tdef in schema['types']:            # Add type definitions
        het = etree.Element('div', {'class': 'tTable jType'})       # top-level element of a type definition
        he2 = etree.SubElement(het, 'div', {'class': 'tCaption'})
        he3 = etree.SubElement(he2, 'div', {'class': 'jTdef'})      # container for type definition column
        etree.SubElement(he3, 'div', {'class': 'jTname'}).text = tdef[TypeName]
        etree.SubElement(he3, 'div', {'class': 'jTstr'}).text = ' = ' + jadn2typestr(tdef[BaseType], tdef[TypeOptions])
        etree.SubElement(he2, 'div', {'class': 'jTdesc'}).text = tdef[TypeDesc] if tdef[TypeDesc] else ''
        if len(tdef) > Fields:
            he2 = etree.SubElement(het, 'div', {'class': 'tHead'})
            etree.SubElement(he2, 'div', {'class': 'tHCell jHid'}).text = 'ID'
            etree.SubElement(he2, 'div', {'class': 'tHCell jHname'}).text = 'Name'
            if tdef[Fields] and len(tdef[Fields][0]) > ItemDesc + 1:
                etree.SubElement(he2, 'div', {'class': 'tHCell jHstr'}).text = 'Type'
                etree.SubElement(he2, 'div', {'class': 'tHCell jHmult'}).text = '#'
            etree.SubElement(he2, 'div', {'class': 'tHCell jHdesc'}).text = 'Description'
            he2 = etree.SubElement(het, 'div', {'class': 'tBody'})
            for fdef in tdef[Fields]:
                he3 = etree.SubElement(he2, 'div', {'class': 'tRow'})
                fname, ftyperef, fmult, fdesc = jadn2fielddef(fdef, tdef)
                if len(tdef[Fields][0]) > ItemDesc + 1:
                    etree.SubElement(he3, 'div', {'class': 'tCell jFid'}).text = str(fdef[FieldID])
                    etree.SubElement(he3, 'div', {'class': 'tCell jFname'}).text = fname
                    etree.SubElement(he3, 'div', {'class': 'tCell jFstr'}).text = ftyperef
                    etree.SubElement(he3, 'div', {'class': 'tCell jFmult'}).text = fmult
                    etree.SubElement(he3, 'div', {'class': 'tCell jFdesc'}).text = fdesc
                else:
                    etree.SubElement(he3, 'div', {'class': 'tCell jFid'}).text = str(fdef[ItemID])
                    etree.SubElement(he3, 'div', {'class': 'tCell jFname'}).text = fname
                    etree.SubElement(he3, 'div', {'class': 'tCell jFdesc'}).text = fdesc
        body.append(het)

    return html.tostring(doc, pretty_print=True, doctype='<!DOCTYPE html>').decode('utf-8')


def html_dump(schema: dict, fname: Union[bytes, str, int], source='') -> NoReturn:
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write(f'<! Generated from {source}, {datetime.ctime(datetime.now())}>\n\n')
        f.write(html_dumps(schema))


"""
Convert HTML to JADN
"""


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
    def get_line(hdoc: str) -> Generator[dict, None, None]:
        line = {}
        tclass = ('jKey', 'jVal', 'jTname', 'jTstr', 'jTdesc', 'jFid', 'jFname', 'jFstr', 'jFmult', 'jFdesc')
        for element in html.fromstring(hdoc).iter():
            cl = [c for c in element.get('class', '').split() if c in tclass]    # Get element's token class
            if cl:
                assert len(cl) == 1     # TODO: Can't be more than one - replace assertions with proper errors
                if cl[0] in ('jKey', 'jTname', 'jFid'):
                    if line:
                        yield line
                        line = {}
                line.update({cl[0]: element.text})
        yield line

    meta = {}
    types = []
    fields = None
    for n, line in enumerate(get_line(hdoc), start=1):
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
