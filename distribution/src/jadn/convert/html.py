from datetime import datetime
from lxml import etree, html
from lxml.html.builder import *
from jadn.definitions import *
from jadn.utils import topts_s2d, ftopts_s2d, typestring, multiplicity

"""
Convert JADN schema to and from HTML format

Generated HTML uses "div tables" rather than HTML table elements to support responsive page design. 

CSS class names needed to render with table layout (required):
tTable:   display table
tCaption: display table-caption
tHead:    display table-header-group
tHCell:   display table-cell (used in header)
tBody:    display table-row-group
tRow:     display table-row
tCell:    display table-cell (used in body)

JADN-specific column layout (optional)
jHid:     FieldId
jHname:   FieldName
jHstr:    FieldType + FieldOptions
jHmult:   Multiplicity
jHdesc:   Description

JADN-specific element styling (optional):
jKey:     metadata keys
jVal:     metadata values
jTname:   TypeName - name of a defined type
jTstr:    String representation of BaseType and TypeOptions
jTdesc:   TypeDesc - description of a type
jFid:     FieldId - integer tag of a field or enumerated item
jFname:   FieldName/ItemValue - name of a field or string value of an enumerated item
jFstr:    String representation of FieldType and FieldOptions (except multiplicity)
jFmult:   String representation of multiplicity FieldOptions
jFdesc:   FieldDesc/ItemDesc - description of a field in a container type or item in an enumerated type
"""

def html_dumps(schema):
    try:
        title = schema['meta']['title']
    except KeyError:
        title = 'JADN Schema'
    doc = HTML(ATTR({'lang': 'en'}),        # Make initial etree
        HEAD(
            META(charset='UTF-8'),
            TITLE(title),
            LINK(rel='stylesheet', href='dtheme.css', type='text/css')
        ),
        BODY(
            H2('Schema')
        )
    )
    body = doc.find('body')

    if 'meta' in schema:                    # Add meta elements if present
        het = etree.Element('div', {'class': 'tTable'})         # top-level element of the metadata table
        he2 = etree.SubElement(het, 'div', {'class': 'tBody'})
        mlist = [k for k in ('title', 'module', 'patch', 'description', 'exports') if k in schema['meta']]
        for k in mlist + list(set(schema['meta']) - set(mlist)):
            he3 = etree.SubElement(he2, 'div', {'class': 'tRow'})
            etree.SubElement(he3, 'div', {'class': 'tCell jKey'}).text = k + ':'
            v = schema['meta'][k]
            if k == 'exports':
                val = ', '.join(v)
            elif k in ('imports', 'config'):
                val = ', '.join((vk + ':\u00a0' + vv for vk, vv in v.items()))
            else:
                val = str(v)
            etree.SubElement(he3, 'div', {'class': 'tCell jVal'}).text = val
        body.append(het)

    for tdef in schema['types']:            # Add type definitions
        het = etree.Element('div', {'class': 'tTable'})             # top-level element of a type definition
        he2 = etree.SubElement(het, 'div', {'class': 'tCaption'})
        he3 = etree.SubElement(he2, 'div', {'class': 'jTdef'})      # container for type definition column
        etree.SubElement(he3, 'div', {'class': 'jTname'}).text = tdef[TypeName]
        to = topts_s2d(tdef[TypeOptions])
        etree.SubElement(he3, 'div', {'class': 'jTstr'}).text = ' = ' + typestring(tdef[BaseType], to)
        etree.SubElement(he2, 'div', {'class': 'jTdesc'}).text = ' // ' + tdef[TypeDesc] if tdef[TypeDesc] else ''
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
                if len(tdef[Fields][0]) > ItemDesc + 1:
                    etree.SubElement(he3, 'div', {'class': 'tCell jFid'}).text = str(fdef[FieldID])
                    etree.SubElement(he3, 'div', {'class': 'tCell jFname'}).text = fdef[FieldName]  # TODO: id option
                    ft, fto = ftopts_s2d(fdef[FieldOptions])
                    fo = {'minc': 1, 'maxc': 1}
                    fo.update(ft)
                    etree.SubElement(he3, 'div', {'class': 'tCell jFstr'}).text = typestring(fdef[FieldType], fto)
                    etree.SubElement(he3, 'div', {'class': 'tCell jFmult'}).text = multiplicity(fo['minc'], fo['maxc'])
                    etree.SubElement(he3, 'div', {'class': 'tCell jFdesc'}).text = fdef[FieldDesc]
                else:
                    etree.SubElement(he3, 'div', {'class': 'tCell jFid'}).text = str(fdef[ItemID])
                    etree.SubElement(he3, 'div', {'class': 'tCell jFname'}).text = fdef[ItemValue]  # TODO: id option
                    etree.SubElement(he3, 'div', {'class': 'tCell jFdesc'}).text = fdef[ItemDesc]
        body.append(het)

    return html.tostring(doc, pretty_print=True, doctype='<!DOCTYPE html>').decode('utf-8')


def html_loads(text):
    htree = html.fromstring(text)
    meta = {}
    types = []
    return {'meta': meta, 'types': types}


def html_dump(schema, fname, source=''):
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write('<! Generated from ' + source + ', ' + datetime.ctime(datetime.now()) + '>\n\n')
        f.write(html_dumps(schema))


def html_load(fname):
    with open(fname, 'r') as f:
        return html_loads(f.read())