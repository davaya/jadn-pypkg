"""
Translate a JADN schema into a GraphViz (https://graphviz.org/) graph display file
"""

import re
from typing import NoReturn
from ..definitions import (TypeName, BaseType, TypeDesc, Fields, FieldName, FieldType, FieldOptions, FieldDesc,
                           PRIMITIVE_TYPES)
from ..utils import ftopts_s2d


# Wrap typenames at word boundaries to minimize node width, using a max of "lines" lines.
def wrapstr(ss: str, lines: int=3) -> str:
    p = 0
    bp = len(ss)/lines
    wrapped = ''
    for w in re.findall(r'[A-Z][a-z0-9]+', ss):
        if p > 0 and p + len(w)/2 > bp:
            wrapped += '\\n'
            bp += len(ss)/lines
        wrapped += w
        p += len(w)
    return wrapped


def multiplicity_str(ops: dict) -> str:
    lo = ops.get('minc', 1)
    hi = ops.get('maxc', 1)
    hs = '*' if hi < 1 else str(hi)
    return f'{lo}..{hs}' if lo != 1 or hi != 1 else '1'


def dot_style() -> dict:
    # Return default GraphViz generation options and graph style attributes
    return {
        'edge_label': True,
        'multiplicity': True,
        'dotfile': {
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
                'labeldistance': 0.75
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
    for k, v in schema["info"].items():
        text += f'# {k}: {v}\n'
    text += f'\n{dot_header(s["dotfile"])}\n'

    nodes = {tdef[TypeName]: k for k, tdef in enumerate(schema['types'])}
    for td in schema['types']:
        node_type = ', shape="ellipse", fillcolor="palegreen"' if td[BaseType] in (*PRIMITIVE_TYPES,'Enumerated') else ''
        node_type = ', shape="hexagon"' if '<->' in td[TypeDesc] else node_type
        text += f'  n{nodes[td[TypeName]]} [label="{wrapstr(td[TypeName])}"{node_type}]\n'
        for fd in td[Fields]:
            if fd[FieldType] in nodes:
                if s['multiplicity']:
                    opts_f = multiplicity_str(ftopts_s2d(fd[FieldOptions])[0])
                    opts_r = m.group(1) if (m := re.search(r'\[([^\]]+)\]', fd[FieldDesc])) else ''
                    mult = f', headlabel="{opts_f}", taillabel="{opts_r}"' if s['multiplicity'] else ''
                label = f' [label="{fd[FieldName]}"{mult}]' if s['edge_label'] else ''
                text += f'    n{nodes[td[TypeName]]} -> n{nodes[fd[FieldType]]}{label}\n'
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