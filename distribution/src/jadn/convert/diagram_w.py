"""
Translate a JADN schema into an Entity Relationship Diagram source file
style[format] =
    graphviz: GraphViz (dot) format
    plantuml: PlantUml format
"""

import re
from datetime import datetime
from ..definitions import (TypeName, BaseType, TypeDesc, PRIMITIVE_TYPES,
                           Fields, FieldID, FieldName, FieldType, FieldOptions, FieldDesc)
from ..utils import ftopts_s2d, multiplicity_str, jadn2fielddef


def diagram_style() -> dict:
    # Return default generation options and style attributes
    return {
        'format': 'plantuml',       # diagram format: graphviz, plantuml
        'detail': 'conceptual',     # Level of detail: conceptual, logical, information
        'links': True,              # Show link edges (dashed)
        'link_horizontal': True,    # Use e-w links vs. n-s containers
        'edge_label': True,         # Show field name on edges
        'multiplicity': True,       # Show multiplicity on edges
        'attributes': False,        # Show node attributes connected to entities (ellipse)
        'attr_color': 'palegreen',  # Attribute ellipse fill color
        'enums': 10,                # Show Enumerated values with max length (0: none, <0: unlimited)
        'header': {
            'plantuml': [
                '\' !theme spacelab',
                'hide empty members',
                'hide circle'
            ],
            'graphviz': [
                'graph [fontname=Arial, fontsize=12];',
                'node [fontname=Arial, fontsize=8, shape=record, style=filled, fillcolor=lightskyblue1];',
                'edge [fontname=Arial, fontsize=7, arrowsize=0.5, labelangle=45.0, labeldistance=0.9];',
                'bgcolor="transparent";'
            ]
        }
    }


def diagram_dumps(schema: dict, style: dict = {}) -> str:
    """
    Convert JADN schema to Entity Relationship Diagram source file
    """
    def wtd(tn, bt) -> str:
        # nodes and s are available in caller scope
        return {
            'plantuml': f'class "{tn}{bt}" as n{nodes[tn]}\n',
            'graphviz': f'n{nodes[tn]}[label=<{{<b>{tn}{bt}</b>|\n'
        }[s['format']]

    def wtde() -> str:
        # nodes and s are available in caller scope
        return {
            'plantuml': '\n',
            'graphviz': '}>]\n\n'
        }[s['format']]

    def wfd(td, fd) -> str:
        # nodes and s are available in caller scope
        if s['detail'] == 'conceptual':
            return
        if s['detail'] == 'logical':
            fval = fd[FieldName]
        elif s['detail'] == 'information':
            fname, fdef, fmult, fdesc = jadn2fielddef(fd, td)
            fdef += '' if fmult == '1' else ' [' + fmult + ']'
            fdef = fdef.translate(str.maketrans({'(': '{', ')': '}'}))  # PlantUML parses parens as methods
            fval = f'{fd[FieldID]} {fname} : {fdef}'
        return {
            'plantuml': f'  n{nodes[tn]} : {fval}\n',
            'graphviz': f'  n{nodes[tn]} : {fval}<br align="left"/>\n'
        }[s['format']]

    s = diagram_style()
    s.update(style)
    assert s['format'] in {'plantuml', 'graphviz'}
    assert s['detail'] in {'conceptual', 'logical', 'information'}
    fmt = {
        'plantuml': {
            'comment': "'",
            'start': '@startuml',
            'end': '@enduml',
            'header': s['header']['plantuml']
        },
        'graphviz': {
            'comment': '#',
            'start': 'digraph G {',
            'end': '}',
            'header': s['header']['graphviz']
        }
    }[s['format']]

    text = ''
    for k, v in schema.get('info', {}).items():
        text += f"{fmt['comment']} {k}: {v}\n"
    text += f"\n{fmt['start']}\n  " + '\n  '.join(fmt['header']) + '\n\n'

    leaf_types = (*PRIMITIVE_TYPES, 'Enumerated')
    hide_types = [] if s['attributes'] else leaf_types
    nodes = {tdef[TypeName]: k for k, tdef in enumerate(schema['types']) if tdef[BaseType] not in hide_types}
    edges = ''
    for td in schema['types']:
        if (tn := td[TypeName]) in nodes:
            bt = f' : {td[BaseType]}' if s['detail'] == 'information' else ''
            text += wtd(tn, bt)
            for fd in td[Fields]:
                text += wfd(td, fd)
                fopts, ftopts = ftopts_s2d(fd[FieldOptions])
                fieldtype = ftopts['vtype'] if fd[FieldType] in {'ArrayOf', 'MapOf'} else fd[FieldType]
                if fieldtype in nodes:
                    rel = ('.' if 'link_horizontal' in s else '..') if 'link' in fopts else '--'
                    elabel = ' : ' + fd[FieldName] if s['edge_label'] else ''
                    mult_f, mult_r = '', ''
                    if s['multiplicity']:
                        mult_f = ' "' + multiplicity_str(fopts) + '"'
                        mult_r = '"1 "'
                    edges += f'  n{nodes[tn]} {mult_r}{rel}>{mult_f} n{nodes[fieldtype]}{elabel}\n'
            text += wtde()
    return text + edges + fmt['end']


def diagram_dump(schema: dict, fname: str, source: str = '', style: dict = {}) -> None:
    with open(fname, 'w') as f:
        if source:
            f.write(f'\' Generated from {source}, {datetime.ctime(datetime.now())}"\n\n')
        f.write(diagram_dumps(schema, style) + '\n')


# Wrap typenames at word boundaries to minimize node width, using a max of "lines" lines.
def wrapstr(ss: str, lines: int = 3) -> str:
    p = 0
    bp = len(ss)/lines
    wrapped = ''
    for m in re.findall(r'([A-Z][a-z0-9]+)|([A-Z]+)|([a-z]+)', ss):  # TODO: update regex to support more word formats
        w = ''.join(m)
        if p > 0 and p + len(w)/2 > bp:
            wrapped += '\\n'
            bp += len(ss)/lines
        wrapped += w
        p += len(w)
    return wrapped


__all__ = [
    'diagram_dump',
    'diagram_dumps',
    'diagram_style'
]
