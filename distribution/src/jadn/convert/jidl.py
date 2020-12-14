"""
Translate JADN to JADN Interface Definition Language
"""
import json
import re

from datetime import datetime
from typing import NoReturn, Tuple, Union
from ..definitions import TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemID, FieldID, INFO_ORDER
from ..utils import cleanup_tagid, get_optx, fielddef2jadn, jadn2fielddef, jadn2typestr, raise_error, typestr2jadn


# Convert JADN to JIDL
def jidl_columns() -> dict:
    return {
        'info': 12,     # Width of info name column (e.g., module:)
        'id': 4,        # Width of Field Id column
        'name': 16,     # Width of Field Name column
        'type': 35,     # Width of Field Type column
        'desc': None,   # Fixed-position descriptions - overrides type-dependent default if specified
        'page': None    # Truncate to specified page width if specified
    }


def jidl_dumps(schema: dict, columns: dict = None) -> str:
    """
    Convert JADN schema to JADN-IDL

    :param dict schema: JADN schema
    :param dict columns: Override default column widths if specified
    :return: JADN-IDL text
    :rtype: str
    """
    w = jidl_columns()
    if columns:
        w.update(columns)   # Override any specified column widths

    text = ''
    info = schema['info'] if 'info' in schema else {}
    mlist = [k for k in INFO_ORDER if k in info]
    for k in mlist + list(set(info) - set(mlist)):              # Display info elements in fixed order
        text += f'{k:>{w["info"]}}: {json.dumps(info[k])}\n'    # TODO: wrap to page width, continuation-line parser

    wt = w['desc'] if w['desc'] else w['id'] + w['name'] + w['type']
    for td in schema['types']:
        tdef = f'{td[TypeName]} = {jadn2typestr(td[BaseType], td[TypeOptions])}'
        tdesc = '// ' + td[TypeDesc] if td[TypeDesc] else ''
        text += f'\n{tdef:<{wt}}{tdesc}'[:w['page']].rstrip() + '\n'
        idt = td[BaseType] == 'Array' or get_optx(td[TypeOptions], 'id') is not None
        for fd in td[Fields] if len(td) > Fields else []:       # TODO: constant-length types
            fname, fdef, fmult, fdesc = jadn2fielddef(fd, td)
            if td[BaseType] == 'Enumerated':
                fdesc = '// ' + fdesc if fdesc else ''
                fs = f'{fd[ItemID]:>{w["id"]}} {fname}'
                wf = w['id'] + w['name'] + 2
            else:
                fdef += '' if fmult == '1' else ' optional' if fmult == '0..1' else ' [' + fmult + ']'
                fdesc = '// ' + fdesc if fdesc else ''
                wn = 0 if idt else w['name']
                fs = f'{fd[FieldID]:>{w["id"]}} {fname:<{wn}} {fdef}'
                wf = w['id'] + w['type'] if idt else wt
            wf = w['desc'] if w['desc'] else wf
            text += f'{fs:{wf}}{fdesc}'[:w['page']].rstrip() + '\n'
    return text


def jidl_dump(schema: dict, fname: Union[bytes, str, int], source='', columns=None) -> NoReturn:
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write(f'/* Generated from {source}, {datetime.ctime(datetime.now())} */\n\n')
        f.write(jidl_dumps(schema, columns))


# Convert JIDL to JADN
def line2jadn(line: str, tdef: list) -> Tuple[str, list]:
    if line:
        p_info = r'^\s*([-\w]+):\s*(.+?)\s*$'
        if m := re.match(p_info, line):
            return 'M', [m.group(1), m.group(2)]

        p_tname = r'\s*([-$\w]+)'               # Type Name
        p_assign = r'\s*='                      # Type assignment operator
        p_tstr  = r'\s*(.*?)\s*\{?'             # Type definition
        p_tdesc = r'(?:\s*\/\/\s*(.*?)\s*)?'    # Optional Type description
        p_type = fr'^{p_tname}{p_assign}{p_tstr}{p_tdesc}$'
        if m := re.match(p_type, line):
            btype, topts, fo = typestr2jadn(m.group(2))
            assert fo == []                     # field options MUST not be included in typedefs
            newtype = [m.group(1), btype, topts, m.group(3) if m.group(3) else '', []]
            return 'T', newtype

        p_id = r'\s*(\d+)'                      # Field ID
        p_fname = r'\s+([-:$\w]+\/?)?'          # Field Name with dir/ option (colon is deprecated, allow for now)
        p_fstr = r'\s*(.*?)'                    # Field definition or Enum value
        p_range = r'\s*(?:\[([.*\w]+)\]|(optional))?'     # Multiplicity
        p_desc = r'\s*(?:\/\/\s*(.*?)\s*)?'     # Field description, including field name if .id option
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

        if line.strip() not in ('', '}'):
            raise_error(f'JIDL load{repr(line)}')
    return '', []


def jidl_loads(doc: str) -> dict:
    info = {}
    types = []
    fields = None
    for line in doc.splitlines():
        if line:
            t, v = line2jadn(line, types[-1] if types else None)    # Parse a JIDL line
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


def jidl_load(fname: Union[bytes, str, int]) -> dict:
    with open(fname, 'r') as f:
        return jidl_loads(f.read())
