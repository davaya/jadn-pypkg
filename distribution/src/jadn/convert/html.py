import re
from arpeggio.cleanpeg import ParserPEG
from datetime import datetime
from lxml import etree, html
from lxml.html.builder import *
from jadn.definitions import *
from jadn import topts_s2d, ftopts_s2d, jadn2typestr, typestr2jadn, jadn2fielddef, fielddef2jadn


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
        etree.SubElement(he3, 'div', {'class': 'jTstr'}).text = ' = ' + jadn2typestr(tdef[BaseType], tdef[TypeOptions])
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
                    fname, ftyperef, fmult, fdesc = jadn2fielddef(fdef, tdef)
                    etree.SubElement(he3, 'div', {'class': 'tCell jFname'}).text = fname
                    etree.SubElement(he3, 'div', {'class': 'tCell jFstr'}).text = ftyperef
                    etree.SubElement(he3, 'div', {'class': 'tCell jFmult'}).text = fmult
                    etree.SubElement(he3, 'div', {'class': 'tCell jFdesc'}).text = fdesc
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


def html_loads(hdoc, debug=False):

    html_grammar = """
        schema  = kvp* typedef* EOF
        kvp     = key value
        typedef = tname tstr tdesc? (field+ / item+)?
        field   = fid fname fstr fmult fdesc?
        item    = fid fname fdesc?
        
        key     = r"jKey\x21(.*):\\x7c$"
        value   = r"jVal\x21(.*)\\x7c$"
        tname   = r"jTname\x21(.*)\\x7c$"
        tstr    = r"jTstr\x21\s*=\s*(.*)\\x7c$"
        tdesc   = r"jTdesc\x21(?:\/\/)?\s*(.*)\\x7c$"
        fid     = r"jFid\x21(.*)\\x7c$"
        fname   = r"jFname\x21(.*)\\x7c$"
        fstr    = r"jFstr\x21(.*)\\x7c$"
        fmult   = r"jFmult\x21(.*)\\x7c$"
        fdesc   = r"jFdesc\x21(.*)\\x7c$"
    """

    # Extract text from HTML elements with specified class attributes; class IDs used for pre-parsing
    # Use US(\x31) / RS(\x30) in production token stream to avoid collisions (! and | used for debug readability)
    def jtoken(txt):
        for e in html.fromstring(txt).iter():
            cl = [c for c in e.get('class', '').split() if c[0] == 'j']
            if cl and cl[0] in ('jKey', 'jVal', 'jTname', 'jTstr', 'jTdesc', 'jFid', 'jFname', 'jFstr', 'jFmult', 'jFdesc'):
                yield cl[0] + '\x21' + (e.text.strip() if e.text else '') + '\x7c' + '\n'

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
        schema = {'meta': {k: v for d in meta for k, v in d.items()}} if meta else {}
        schema.update({'types': [v for d in nl for k, v in d.items() if k == 'typedef']})
        return schema

    def v_kvp(node, nl):
        k, v = nl[0]['key'], nl[1]['value']
        if k == 'exports':
            v = v.split(',')
        elif k in ('imports', 'config'):
            v = dict(map(str.strip, x.split(':', maxsplit=1)) for x in v.split(','))
        return {k: v}

    def v_typedef(node, nl):
        basetype, topts = typestr2jadn(nl[1]['tstr'])
        fields = [v for d in nl for k, v in d.items() if k in ('field', 'item')]
        return [nl[0]['tname'], basetype , topts, nl[2]['tdesc']] + ([fields] if fields else [])

    def v_field(node, nl):
        return [int(nl[0]['fid'])] + fielddef2jadn(nl[1]['fname'], nl[2]['fstr'], nl[3]['fmult'], nl[4]['fdesc'])

    def v_item(node, nl):
        return [int(nl[0]['fid']), nl[1]['fname'], nl[2]['fdesc']]

    def v_default(node):
        if node.value:
            if getattr(node, '__iter__', ''):
                return visit(node)
            return node.rule.regex.match(node.value).group(1)

    visitor = {
        'schema': v_schema,
        'kvp': v_kvp,
        'typedef': v_typedef,
        'field': v_field,
        'item': v_item,
    }

    def visit(node):
        name = node.name.split()[0]
        nl = []
        if getattr(node, '__iter__', ''):
            for n in list(node):
                nl.append(visit(n))
        value = visitor[name](node, nl) if name in visitor else v_default(node)
        return {name: value}

    # print(html_tree_dumps(hdoc))
    parser = ParserPEG(html_grammar, 'schema', debug=debug)
    tokens = ''.join(jtoken(hdoc))
    parse_tree = parser.parse(tokens)
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
