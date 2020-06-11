import re
from arpeggio.cleanpeg import ParserPEG
from datetime import datetime
from lxml import etree, html
from lxml.html.builder import *
from jadn.definitions import *
from jadn.utils import topts_s2d, ftopts_s2d, jadn2typestr, multiplicity


"""
Convert JADN schema to and from HTML format

Generated HTML uses "div tables" rather than HTML table elements to support responsive page design.
JADN-specific class names are used to parse HTML to JADN, but css definitions are optional.

CSS class names needed to render with table layout (required):
tTable:   display table
tCaption: display table-caption
tHead:    display table-header-group
tHCell:   display table-cell (used in header)
tBody:    display table-row-group
tRow:     display table-row
tCell:    display table-cell (used in body)

JADN column headers (styling optional):
jHid:     FieldId
jHname:   FieldName
jHstr:    FieldType + FieldOptions
jHmult:   Multiplicity
jHdesc:   Description

JADN schema elements (styling optional):
jMeta:    metadata section root
jKey:     metadata key
jVal:     metadata value
jType:    type definition root
jTname:   TypeName - name of a defined type
jTstr:    String representation of BaseType and TypeOptions
jTdesc:   TypeDesc - description of a type
jFid:     FieldId - integer tag of a field or enumerated item
jFname:   FieldName/ItemValue - name of a field or string value of an enumerated item
jFstr:    String representation of FieldType and FieldOptions (except multiplicity)
jFmult:   String representation of multiplicity FieldOptions
jFdesc:   FieldDesc/ItemDesc - description of a field in a container type or item in an enumerated type
"""

"""
Convert JADN to HTML
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
        het = etree.Element('div', {'class': 'tTable jMeta'})       # top-level element of the metadata table
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
        het = etree.Element('div', {'class': 'tTable jType'})       # top-level element of a type definition
        he2 = etree.SubElement(het, 'div', {'class': 'tCaption'})
        he3 = etree.SubElement(he2, 'div', {'class': 'jTdef'})      # container for type definition column
        etree.SubElement(he3, 'div', {'class': 'jTname'}).text = tdef[TypeName]
        to = topts_s2d(tdef[TypeOptions])
        etree.SubElement(he3, 'div', {'class': 'jTstr'}).text = ' = ' + jadn2typestr(tdef[BaseType], to)
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
                    etree.SubElement(he3, 'div', {'class': 'tCell jFstr'}).text = jadn2typestr(fdef[FieldType], fto)
                    etree.SubElement(he3, 'div', {'class': 'tCell jFmult'}).text = multiplicity(fo['minc'], fo['maxc'])
                    etree.SubElement(he3, 'div', {'class': 'tCell jFdesc'}).text = fdef[FieldDesc]
                else:
                    etree.SubElement(he3, 'div', {'class': 'tCell jFid'}).text = str(fdef[ItemID])
                    etree.SubElement(he3, 'div', {'class': 'tCell jFname'}).text = fdef[ItemValue]  # TODO: id option
                    etree.SubElement(he3, 'div', {'class': 'tCell jFdesc'}).text = fdef[ItemDesc]
        body.append(het)

    return html.tostring(doc, pretty_print=True, doctype='<!DOCTYPE html>').decode('utf-8')


def html_dump(schema, fname, source=''):
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write('<! Generated from ' + source + ', ' + datetime.ctime(datetime.now()) + '>\n\n')
        f.write(html_dumps(schema))


"""
Convert HTML to JADN
"""

def load_meta(e):
    key = e.text.strip(': ')
    ev = e.getnext()
    if 'jVal' in ev.get('class', ''):
        val = ev.text
        if key == 'exports':
            val = [v for v in ev.text.split(',')]
        elif key in ('config', 'imports'):
            val = {k.strip(): v.strip() for item in ev.text.split(',') for k, v in (item.split(':', maxsplit=1),)}
        return {key: val}


def load_type(e):
    tdef = [None, None, None, '']
    for x in e.iter():
        cl = x.get('class', '')
        if 'jTname' in cl:
            tdef[TypeName] = x.text.strip()
        elif 'jtRow':
            pass
    return ['foo', 'Record', [], '']


def html_loads(hdoc):
    html_grammar = """
        schema  = kvp* typedef* EOF
        kvp     = key value
        key     = "jKey" us name ":"? rs
        value   = "jVal" us any rs

        name    = r"[-$\w]+"
        us      = "!"
        rs      = "|"
        any     = r"[^|]*"

        typedef = typename typestr typedesc? (field*/item*)
        field   = fieldid fieldname fieldstr multi fielddesc?
        item    = fieldid
        
        typename    = "jTname" us name rs
        typestr     = "jTstr" us "=" any rs
        typedesc    = "jTdesc" us "//" any rs
        fieldid     = "jFid" us r"\d+" rs
        fieldname   = "jFname" us name rs
        fieldstr    = "jFstr" us any rs
        fielddesc   = "jFdesc" us any rs
        multi       = "jFmult" us r"\d+(\.\.\d+)?" rs
    """

    def split_typestr(typestr):
        return typestr, []

    def split_fieldstr(fieldstr, multi):
        return fieldstr + ('[' + multi + ']' if multi != '1' else ''), []

    def jtoken(txt):    # Extract text from HTML elements with specified class attributes
        for e in html.fromstring(txt).iter():
            cl = [c for c in e.get('class', '').split() if c[0] == 'j']
            if cl and cl[0] in ('jKey', 'jVal', 'jTname', 'jTstr', 'jTdesc', 'jFid', 'jFname', 'jFstr', 'jFmult', 'jFdesc'):
                yield cl[0] + '!' + (e.text.strip() if e.text else '') + '|' + '\n'
                # yield cl[0] + chr(31) + (e.text.strip() if e.text else '') + chr(30) + '\n'

    def walk(node, ptree='', indent=0, close=False):
        if getattr(node, '__iter__', ''):
            ptree += '\n' + '. ' * indent + node.name + ': '
            for n in list(node):
                ptree = walk(n, ptree, indent + 1, close)
            ptree += '\n' + '. ' * indent if close else ''
        else:
            ptree += node.value + ' '
            # ptree += '\n' + '- ' * indent + node.value
        return ptree

    def v_schema(node, nl):
        meta = [v for d in nl for k, v in d.items() if k == 'kvp']
        types = [v for d in nl for k, v in d.items() if k == 'typedef']
        return {'meta': {k: v for d in meta for k, v in d.items()},
                'types': types}

    def v_kvp(node, nl):
        k, v = nl[0]['key'], nl[1]['value']
        if k == 'exports':
            v = v.split(',')
        elif k in ('imports', 'config'):
            v = dict(map(str.strip, x.split(':', maxsplit=1)) for x in v.split(','))
        return {k: v}

    def v_typedef(node, nl):
        basetype, topts = split_typestr(nl[1]['typestr'])
        fields = [v for d in nl for k, v in d.items() if k == 'field']
        return [nl[0]['typename'], basetype , topts, nl[2]['typedesc']] + [fields]

    def v_value3(node, nl):
        return node[3].value

    def v_field(node, nl):
        fieldtype, ftopts = split_fieldstr(nl[2]['fieldstr'], nl[3]['multi'])
        return [int(nl[0]['fieldid']), nl[1]['fieldname'], fieldtype, ftopts, nl[4]['fielddesc']]

    def v_default(node, nl):
        if getattr(node, '__iter__', ''):
            return node[2].value        # Get "value" for rules like ["name" sep "value" sep]
        return node.value

    visitor = {
        'schema': v_schema,
        'kvp': v_kvp,
        'typedef': v_typedef,
        'typestr': v_value3,
        'typedesc': v_value3,
        'field': v_field,
    }

    def visit(node):
        name = node.name.split()[0]
        nl = []
        if getattr(node, '__iter__', ''):
            for n in list(node):
                nl.append(visit(n))
        value = visitor[name](node, nl) if name in visitor else v_default(node, nl)
        return {name: value}

    tokens = ''.join(jtoken(hdoc))
    # print(tokens)
    parser = ParserPEG(html_grammar, 'schema')
    parse_tree = parser.parse(tokens)
    # print(walk(parse_tree))
    schema = visit(parse_tree)['schema']
    return schema


def html_load(fname):
    with open(fname, 'r') as f:
        return html_loads(f.read())


"""
HTML Parser Diagnostics
"""


def html_tree_dumps(html_doc, indents='. '):
    """
    Parse an HTML document and pretty-print the element tree
    """
    path = []
    tree_walk(html.fromstring(html_doc), path)
    return tree_dumps(path, indents)


def tree_walk(element, path, node=1, indent=0, parent=None):
    """
    Traverse an element tree in depth-first order
    :param element: Root lxml Element
    :param path: Empty array [] used to return the tree.
    :return: next node number.  Path is a list of 4-tuples: (Element, Node number, Depth, Parent).
             Node < 0 indicates upward (closing) traversal.
    """
    path.append((element, node, indent, parent))
    n0 = node
    for subelement in list(element):
        node = tree_walk(subelement, path, node+1, indent+1, n0)
    if node != n0:
        path.append((element, -n0, indent, parent))
    return node


def tree_dumps(path, s='. '):
    """
    Pretty-print a tree of lxml Elements
    :param path: list of node tuples (Element, node number, depth, parent)
    :param s: indentation string
    :return: string representation of element tree
    """

    void_tags = ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                 'link', 'meta', 'param', 'source', 'track', 'wbr')
    ds = ''
    for (e, n, l, p) in path:       # Element instance, node number, level, parent node
        if n > 0:
            if e.tag in void_tags:
                assert e.text == None
                assert not list(e)
                ds += f"{n:>4} {l * s}<{e.tag} {e.attrib}> {repr(e.tail)}\n"
            else:
                close_tag = '' if list(e) else f"</{e.tag}> {repr(e.tail)}"
                ds += f"{n:>4} {l*s}<{e.tag} {e.attrib}>{repr(e.text)}{close_tag}\n"
        else:
            ds += f"{-n:>4} {l*s}</{e.tag}> {repr(e.tail)}\n"
    return ds
