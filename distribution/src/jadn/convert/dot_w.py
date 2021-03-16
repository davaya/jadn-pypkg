"""
Translate a JADN schema into a GraphViz (https://graphviz.org/) graph display file
"""

from typing import NoReturn
from ..definitions import TypeName, Fields, FieldName, FieldType, FieldOptions


# TODO: Wrap typenames at word boundaries to minimize node width, using a max of "lines" lines.
def wrapstr(ss: str, lines: int=3) -> str:
    return ss


dot_header = """
digraph G {
  graph [fontname = "Handlee"];
  node [shape=box, fontsize=8, fontname = "Arial", style=filled, fillcolor=lightskyblue];
  edge [fontsize=7, fontname = "Arial"];
  bgcolor=transparent;
"""


def dot_dumps(schema: dict, style: dict={'edge_label': True}) -> str:
    dd = ''
    for k, v in schema["info"].items():
        dd += f'# {k}: {v}\n'
    dd += dot_header
    nodes = {tdef[TypeName]: k for k, tdef in enumerate(schema['types'])}
    for td in schema['types']:
        dd += f'  n{nodes[td[TypeName]]} [label="{wrapstr(td[TypeName])}"]\n'
        for fd in td[Fields]:
            if fd[FieldType] in nodes:
                label = f' [label="{fd[FieldName]}"]' if style['edge_label'] else ''
                dd += f'    n{nodes[td[TypeName]]} -> n{nodes[fd[FieldType]]}{label}\n'
    dd += '}'
    return dd


def dot_dump(schema: dict, fname: str, source: str = '') -> NoReturn:
    with open(fname, 'w') as f:
        if source:
            f.write(f'"# Generated from {source}, {datetime.ctime(datetime.now())}"\n\n')
        f.write(dot_dumps(schema) + '\n')


__all__ = [
    'dot_dump',
    'dot_dumps'
]