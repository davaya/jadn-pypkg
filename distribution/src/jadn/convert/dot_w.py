"""
Translate a JADN schema into a GraphViz (https://graphviz.org/) graph display file
"""

import re
from datetime import datetime
from typing import NoReturn
from ..definitions import (TypeName, BaseType, TypeDesc, PRIMITIVE_TYPES,
                           Fields, FieldName, FieldType, FieldOptions, FieldDesc)
from ..utils import ftopts_s2d, multiplicity_str


# Wrap typenames at word boundaries to minimize node width, using a max of "lines" lines.
def wrapstr(ss: str, lines: int=3) -> str:
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


def dot_style() -> dict:
    # Return default generation options and GraphViz style attributes
    return {
        'detail': 'conceptual',     # Level of detail: conceptual, logical, information
        'links': True,              # Show link edges (dashed)
        'attributes': False,        # Show node attributes connected to entities (ellipse)
        'attr_color': 'palegreen',  # Attribute ellipse fill color
        'edge_label': True,         # Show field name on edges
        'multiplicity': True,       # Show multiplicity on edges
        'header': {                 # Options defined in GraphViz "Node, Edge and Graph Attributes"
            'graph': {
                'fontname': 'Times',
                'fontsize': 12
            },
            'node': {
                'fontname': 'Arial',
                'fontsize': 8,
                'shape': 'box',
                'style': 'filled',
                'fillcolor': 'lightskyblue1'
            },
            'edge': {
                'fontname': 'Arial',
                'fontsize': 7,
                'arrowsize': 0.5,
                'labelangle': 45.0,
                'labeldistance': 0.9
            },
            'bgcolor': 'transparent',
        }
    }


def dot_header(style: dict) -> str:
    header = 'digraph G {\n'
    for kw, val in style.items():
        v2 = f'="{val}"'
        if isinstance(val, dict):
            v2 = f' [{", ".join([k3 + "=" + str(v3) for k3, v3 in val.items()])}]'
        header += f'  {kw}{v2};\n'
    return header


def dot_dumps(schema: dict, style: dict=None) -> str:
    """
    Convert JADN schema to GraphViz "dot" file
    """
    s = dot_style()
    if style:
        s.update(style)

    text = ''
    for k, v in schema.get('info', {}).items():
        text += f'# {k}: {v}\n'
    text += f'\n{dot_header(s.get("header", ""))}\n'

    atypes = (*PRIMITIVE_TYPES, 'Enumerated')
    nodes = {tdef[TypeName]: k for k, tdef in enumerate(schema['types']) if tdef[BaseType] not in atypes}
    for td in schema['types']:
        node_type = f', shape="ellipse", fillcolor="{s["attr_color"]}"' if td[BaseType] in atypes else ''
        if s['attributes'] or not node_type:
            node_type = ', shape="hexagon"' if '<->' in td[TypeDesc] else node_type     # TODO: replace SOSA hacks
            text += f'  n{nodes[td[TypeName]]} [label="{wrapstr(td[TypeName])}"{node_type}]\n'
            for fd in td[Fields]:
                fopts, topts = ftopts_s2d(fd[FieldOptions])
                fieldtype = topts['vtype'] if fd[FieldType] == 'MapOf' else fd[FieldType]
                if fieldtype in nodes:
                    edge_attrs = ['style="dashed"'] if 'link' in fopts or '<=' in fd[FieldDesc] else []
                    if s['links'] or not edge_attrs:
                        edge_attrs += [f'label="{fd[FieldName]}"'] if s['edge_label'] else []
                        if s['multiplicity']:
                            opts_f = multiplicity_str(ftopts_s2d(fd[FieldOptions])[0])
                            opts_r = m.group(1) if (m := re.search(r'\[([^\]]+)\]', fd[FieldDesc])) else '1'
                            edge_attrs += [f'headlabel="{opts_f}", taillabel="{opts_r}"']
                        edge_list = ', '.join(edge_attrs)
                        edge = f' [{edge_list}]' if edge_list else ''
                        text += f'    n{nodes[td[TypeName]]} -> n{nodes[fieldtype]}{edge}\n'
    text += '}'
    return text


def dot_dump(schema: dict, fname: str, source: str = '', style: dict=None) -> NoReturn:
    with open(fname, 'w') as f:
        if source:
            f.write(f'"# Generated from {source}, {datetime.ctime(datetime.now())}"\n\n')
        f.write(dot_dumps(schema, style) + '\n')


__all__ = [
    'dot_dump',
    'dot_dumps',
    'dot_style'
]
