"""
Translate JADN to JAS (JADN Abstract Syntax)
"""
from copy import deepcopy
from datetime import datetime
from textwrap import fill
from typing import NoReturn, Union
from ..definitions import (
    TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemDesc, FieldID, FieldName, FieldType, FieldOptions, FieldDesc,
    CORE_TYPES, INFO_ORDER, TYPE_OPTIONS, FIELD_OPTIONS
)
from ..utils import ftopts_s2d, topts_s2d

stype_map = {                   # Map JADN built-in types to JAS type names (Equivalent ASN.1 types in comments)
    'Binary': 'BINARY',         # OCTET STRING
    'Boolean': 'BOOLEAN',       # BOOLEAN
    'Integer': 'INTEGER',       # INTEGER
    'Number': 'REAL',           # REAL
    'String': 'STRING',         # UTF8String
    'Array': 'ARRAY',           # SEQUENCE
    'ArrayOf': 'ARRAY_OF',      # SEQUENCE OF
    'Choice': 'CHOICE',         # CHOICE
    'Enumerated': 'ENUMERATED', # ENUMERATED
    'Map': 'MAP',               # SET
    'MapOf': 'MAP_OF',          #
    'Record': 'RECORD'          # SEQUENCE
}


def stype(jtype: str) -> str:
    return stype_map.get(jtype, jtype)


# TODO: simplify function??
def jas_dumps(schema: dict) -> str:
    """
    Produce JAS module from JADN structure

    JAS represents features available in both JADN and ASN.1 using ASN.1 syntax, but adds
    extended datatypes (Record, Map) for JADN types not directly representable in ASN.1.
    With appropriate encoding rules (which do not yet exist), SEQUENCE could replace Record.
    Map could be implemented using ASN.1 table constraints, but for the purpose of representing
    JSON objects, the Map first-class type in JAS is easier to use.
    """
    jas = ''

    # Convert Meta
    if info := schema.get('info'):
        jas += '/*\n'
        mlist = [k for k in INFO_ORDER if k in info]
        for h in mlist + list(set(info) - set(mlist)):
            if h == 'description':
                jas += fill(info[h], width=80, initial_indent='{0:14} '.format(h+':'), subsequent_indent=15*' ') + '\n'
            elif h == 'imports':
                hh = '{:14} '.format(f'{h}:')
                for imp in info[h]:
                    jas += '{}{}: {}\n'.format(hh, *imp)
                    hh = 15*' '
            elif h == 'exports':
                jas += '{:14} {}\n'.format(f'{h}:', ', '.join(info[h]))
            else:
                jas += '{:14} {}\n'.format(f'{h}:', info[h])
        jas += '*/\n'

    assert set(stype_map) == set(CORE_TYPES)         # Ensure type list is up to date
    tolist = {'id', 'vtype', 'ktype', 'enum', 'pointer', 'format', 'pattern', 'minv', 'maxv', 'minf', 'maxf', 'unique', 'and', 'or'}
    assert {x[0] for x in TYPE_OPTIONS.values()} == tolist                # Ensure type options list is up to date
    folist = {'minc', 'maxc', 'tagid', 'dir', 'key', 'link', 'default'}
    assert {x[0] for x in FIELD_OPTIONS.values()} == folist               # Ensure field options list is up to date

    # Convert Types
    for td in schema['types']:  # 0:type name, 1:base type, 2:type opts, 3:type desc, 4:fields
        topts = topts_s2d(td[TypeOptions])
        tostr = ''
        v_range = ''
        if 'minv' in topts or 'maxv' in topts:          # TODO: use jadn2typestr
            lo = topts.get('minv', 0)
            hi = topts.get('maxv', 0)
            if lo or hi:
                v_range = f"({lo}..{hi if hi else 'MAX'})"
        for opt in tolist:
            if opt in topts:
                ov = topts[opt]
                if opt == 'id':
                    tostr += '.ID'
                elif opt == 'vtype':
                    tostr += f'({ov})'
                elif opt == 'ktype':
                    pass            # fix MapOf(ktype, vtype)
                elif opt == 'pattern':
                    tostr += f' (PATTERN ("{ov}"))'
                elif opt == 'format':
                    tostr += f' (CONSTRAINED BY {{{ov}}})'
                elif opt in ('minv', 'maxv'):     # TODO fix to handle both
                    if v_range:
                        if td[BaseType] in ('Integer', 'Number'):
                            tostr += f' {v_range}'
                        elif td[BaseType] in ('Binary', 'String', 'Array', 'ArrayOf', 'Map', 'MapOf', 'Record'):
                            tostr += f' (Size {v_range})'
                        else:
                            assert False        # Should never get here
                    v_range = ''
                else:
                    tostr += f' %{opt}: {ov}%'
        tdesc = f'    -- {td[TypeDesc]}' if td[TypeDesc] else ''
        jas += f'\n{td[TypeName]} ::= {stype(td[BaseType])}{tostr}'
        if len(td) > Fields:
            titems = deepcopy(td[Fields])
            for n, i in enumerate(titems):      # 0:tag, 1:enum item name, 2:enum item desc  (enumerated), or
                if len(i) > FieldOptions:              # 0:tag, 1:field name, 2:field type, 3: field opts, 4:field desc
                    desc = i[FieldDesc]
                    i[FieldType] = stype(i[FieldType])
                else:
                    desc = i[ItemDesc]
                desc = f'    -- {desc}' if desc else ''
                i.append(',' + desc if n < len(titems) - 1 else (' ' + desc if desc else ''))  # TODO: fix hacked desc for join
            flen = min(32, max(12, max([len(i[FieldName]) for i in titems]) + 1 if titems else 0))
            jas += ' {' + tdesc + '\n'
            if td[BaseType].lower() == 'enumerated':
                fmt = '    {1:' + str(flen) + '} ({0:d}){3}'
                jas += '\n'.join([fmt.format(*i) for i in titems])
            else:
                fmt = '    {1:' + str(flen) + '} [{0:d}] {2}{3}{4}'
                if td[BaseType].lower() == 'record':
                    fmt = '    {1:' + str(flen) + '} {2}{3}{4}'
                items = []
                for n, i in enumerate(titems):                          # TODO: Convert to use jadn2fielddef
                    ostr = ''
                    opts = ftopts_s2d(i[FieldOptions])[0]
                    if 'tagid' in opts:
                        ostr += f"(Tag({opts['tagid']}))"    # TODO: lookup field name
                        del opts['tagid']
                    if 'vtype' in opts:
                        ostr += '.*'
                        del opts['vtype']
                    if 'minc' in opts:
                        if opts['minc'] == 0:         # TODO: handle array fields (max != 1)
                            ostr += ' OPTIONAL'
                        del opts['minc']
                    items += [fmt.format(i[FieldID], i[FieldName], i[FieldType], ostr, i[5]) + (f' %{opts}' if opts else '')]
                jas += '\n'.join(items)
            jas += '\n}\n' if titems else '}\n'
        else:
            jas += tdesc + '\n'
    return jas


def jas_dump(schema: dict, fname: Union[bytes, str, int], source='') -> NoReturn:
    with open(fname, 'w') as f:
        if source:
            f.write(f'-- Generated from {source}, {datetime.ctime(datetime.now())}\n\n')
        f.write(jas_dumps(schema))


__all__ = [
    'jas_dump',
    'jas_dumps'
]
