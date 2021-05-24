"""
Translate JADN to Protobuf 3
"""
import json
import re

from datetime import datetime
from typing import NoReturn, Tuple, Union
from urllib.parse import urlparse
from ..definitions import TypeName, BaseType, TypeOptions, TypeDesc, Fields, INFO_ORDER,\
                          ItemID, FieldID, FieldName, FieldOptions, FieldDesc
from ..utils import cleanup_tagid, get_optx, fielddef2jadn, raise_error, typestr2jadn, topts_s2d, ftopts_s2d

# PROTO -> JADN Type regexes
p_tname = r'\s*([-$\w]+)'               # Type Name
p_assign = r'\s*='                      # Type assignment operator
p_tstr = r'\s*(.*?)\s*\{?'             # Type definition
p_tdesc = r'(?:\s*\/\/\s*(.*?)\s*)?'    # Optional Type description

# PROTO -> JADN Field regexes
p_id = r'\s*(\d+)'  # Field ID
p_fname = r'\s+([-:$\w]+\/?)?'  # Field Name with dir/ option (colon is deprecated, allow for now)
p_fstr = r'\s*(.*?)'  # Field definition or Enum value
p_range = r'\s*(?:\[([.*\w]+)\]|(optional))?'  # Multiplicity
p_desc = r'\s*(?:\/\/\s*(.*?)\s*)?'  # Field description, including field name if .id option


def proto_style() -> dict:
    # Return default column positions
    return {
        'comment_pre': True,     # If True, comments on separate line preceding type or field.  If false, inline.
    }


# Convert URI to java-style reversed internet domain name
def uri_to_revid(uri: str) -> str:
    u = urlparse(uri)
    return '.'.join(u.netloc.split(':')[0].split('.')[::-1] + u.path.replace('.', '-').split('/')[1:])


# Convert java-style reversed domain to URI (specify the number of domain components, default=2)
def revid_to_uri(revid: str, hostlen: int=2) -> str:
    o = revid.split('.')
    return f'http://{".".join(o[:hostlen][::-1])}/{"/".join(o[hostlen:])}'


def proto_dumps(schema: dict, style: dict = None) -> str:
    """
    Convert JADN schema to Protobuf 3

    :param dict schema: JADN schema
    :param dict style: Override default column widths if specified
    :return: Protobuf text
    :rtype: str
    """
    w = proto_style()
    if style:
        w.update(style)   # Override any specified column widths

    text = 'syntax = "proto3";\n'
    info = schema['info'] if 'info' in schema else {}
    mlist = [k for k in INFO_ORDER if k in info]
    for k in mlist + list(set(info) - set(mlist)):              # Display info elements in fixed order
        if k == 'package':
            text += f'package {uri_to_revid(info[k])};\n'
        else:
            text += f'// {k:>{w["info"]}}: {json.dumps(info[k])}\n'  # TODO: wrap to page width, parse continuation

    for td in schema['types']:
        topts = topts_s2d(td[TypeOptions])
        if td[TypeDesc]:
            text += f'// {td[TypeDesc]}\n'
        if td[BaseType] in ('Record', 'Map', 'Array'):
            text += f'message {td[TypeName]} {{  // ${td[BaseType]} {topts}\n'
        elif td[BaseType] == 'Enumerated':
            text += f'enum {td[TypeName]} {{  // ${topts}\n'
        else:
            text += f'// ${td[TypeName]}({td[BaseType]}) {topts}\n'

        for fd in td[Fields] if len(td) > Fields else []:       # TODO: constant-length types
            fopts, ftopts = ftopts_s2d(fd[FieldOptions])
            if fd[FieldDesc]:
                text += f'// {fd[FieldDesc]}\n'

        if td[BaseType] in ('Record', 'Map', 'Array', 'Enumerated', 'Choice'):
            text += '}\n\n'
    return text


def proto_dump(schema: dict, fname: Union[bytes, str, int], source='', style=None) -> NoReturn:
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write(f'/* Generated from {source}, {datetime.ctime(datetime.now())} */\n\n')
        f.write(proto_dumps(schema, style))


# Convert PROTO to JADN
def line2jadn(line: str, tdef: list) -> Tuple[str, list]:
    if line.split('//', maxsplit=1)[0].strip():
        p_info = r'^\s*([-\w]+):\s*(.+?)\s*$'
        if m := re.match(p_info, line):
            return 'M', [m.group(1), m.group(2)]

        p_type = fr'^{p_tname}{p_assign}{p_tstr}{p_tdesc}$'
        if m := re.match(p_type, line):
            btype, topts, fo = typestr2jadn(m.group(2))
            assert fo == []                     # field options MUST not be included in typedefs
            newtype = [m.group(1), btype, topts, m.group(3) if m.group(3) else '', []]
            return 'T', newtype

        if tdef:        # looking for fields
            pn = '()' if (get_optx(tdef[TypeOptions], 'id') is not None or tdef[BaseType] == 'Array') else p_fname
            if tdef[BaseType] == 'Enumerated':      # Parse Enumerated Item
                pattern = fr'^{p_id}{p_fstr}{p_desc}$'
                if m := re.match(pattern, line):
                    return 'F', fielddef2jadn(int(m.group(1)), m.group(2), '', '', m.group(3) if m.group(3) else '')
            else:                                   # Parse Field
                pattern = f'^{p_id}{pn}{p_fstr}{p_range}{p_desc}$'
                if m := re.match(pattern, line):
                    m_range = '0..1' if m.group(5) else m.group(4)        # Convert 'optional' to range
                    fdesc = m.group(6) if m.group(6) else ''
                    return 'F', fielddef2jadn(int(m.group(1)), m.group(2), m.group(3), m_range if m_range else '', fdesc)
        else:
            raise_error(f'PROTO Load - field with no type: {repr(line)}')

    return '', []


def proto_loads(doc: str) -> dict:
    info = {}
    types = []
    fields = None
    for line in doc.splitlines():
        if line:
            t, v = line2jadn(line, types[-1] if types else None)    # Parse a PROTO line
            if t == 'F':
                fields.append(v)
            elif fields:
                cleanup_tagid(fields)
                fields = None
            if t == 'M':
                info.update({v[0]: json.loads(v[1])})
            elif t == 'T':
                types.append(v)
                fields = types[-1][Fields]
    return {'info': info, 'types': types} if info else {'types': types}


def proto_load(fname: Union[bytes, str, int]) -> dict:
    with open(fname, 'r') as f:
        return proto_loads(f.read())


__all__ = [
    'proto_dump',
    'proto_dumps',
    'proto_load',
    'proto_loads',
    'proto_style'
]
