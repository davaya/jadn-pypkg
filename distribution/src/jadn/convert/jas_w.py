"""
Translate JADN to JAS (JADN Abstract Syntax)
"""

from jadn import topts_s2d, ftopts_s2d
from jadn.definitions import *
from copy import deepcopy
from datetime import datetime
from textwrap import fill

stype_map = {                   # Map JADN built-in types to JAS type names (Equivalent ASN.1 types in comments)
    'Binary': 'BINARY',         # OCTET STRING
    'Boolean': 'BOOLEAN',       # BOOLEAN
    'Integer': 'INTEGER',       # INTEGER
    'Number': 'REAL',           # REAL
    'Null': 'NULL',             # NULL
    'String': 'STRING',         # UTF8String
    'Array': 'ARRAY',           # SEQUENCE
    'ArrayOf': 'ARRAY_OF',      # SEQUENCE OF
    'Choice': 'CHOICE',         # CHOICE
    'Enumerated': 'ENUMERATED', # ENUMERATED
    'Map': 'MAP',               # SET
    'MapOf': 'MAP_OF',          #
    'Record': 'RECORD'          # SEQUENCE
}


def stype(jtype):
    return stype_map[jtype] if jtype in stype_map else jtype


def jas_dumps(schema):
    """
    Produce JAS module from JADN structure

    JAS represents features available in both JADN and ASN.1 using ASN.1 syntax, but adds
    extended datatypes (Record, Map) for JADN types not directly representable in ASN.1.
    With appropriate encoding rules (which do not yet exist), SEQUENCE could replace Record.
    Map could be implemented using ASN.1 table constraints, but for the purpose of representing
    JSON objects, the Map first-class type in JAS is easier to use.
    """

    jas = '/*\n'
    meta = schema['info']
    mlist = [k for k in INFO_ORDER if k in meta]
    for h in mlist + list(set(meta) - set(mlist)):
        if h == 'description':
            jas += fill(meta[h], width=80, initial_indent='{0:14} '.format(h+':'), subsequent_indent=15*' ') + '\n'
        elif h == 'imports':
            hh = '{:14} '.format(h+':')
            for imp in meta[h]:
                jas += hh + '{}: {}\n'.format(*imp)
                hh = 15*' '
        elif h == 'exports':
            jas += '{:14} {}\n'.format(h+':', ', '.join(meta[h]))
        else:
            jas += '{:14} {}\n'.format(h+':', meta[h])
    jas += '*/\n'

    assert set(stype_map) == set(CORE_TYPES)         # Ensure type list is up to date
    tolist = ['id', 'vtype', 'ktype', 'enum', 'pointer', 'format', 'pattern',
              'minv', 'maxv', 'minf', 'maxf', 'unique', 'and', 'or']
    assert {x[0] for x in TYPE_OPTIONS.values()} == set(tolist)                # Ensure type options list is up to date
    folist = ['minc', 'maxc', 'tagid', 'dir', 'default']
    assert {x[0] for x in FIELD_OPTIONS.values()} == set(folist)               # Ensure field options list is up to date
    for td in schema['types']:                    # 0:type name, 1:base type, 2:type opts, 3:type desc, 4:fields
        tname = td[TypeName]
        ttype = td[BaseType]
        topts = topts_s2d(td[TypeOptions])
        tostr = ''
        range = ''
        if 'minv' in topts or 'maxv' in topts:          # TODO: use jadn2typestr
            lo = topts['minv'] if 'minv' in topts else 0
            hi = topts['maxv'] if 'maxv' in topts else 0
            if lo or hi:
                range = '(' + str(lo) + '..' + (str(hi) if hi else 'MAX') + ')'
        for opt in tolist:
            if opt in topts:
                ov = topts[opt]
                if opt == 'id':
                    tostr += '.ID'
                elif opt =='vtype':
                    tostr += '(' + ov + ')'
                elif opt == 'ktype':
                    pass            # fix MapOf(ktype, vtype)
                elif opt == 'pattern':
                    tostr += ' (PATTERN ("' + ov + '"))'
                elif opt == 'format':
                    tostr += ' (CONSTRAINED BY {' + ov + '})'
                elif opt in ('minv', 'maxv'):     # TODO fix to handle both
                    if range:
                        if ttype in ('Integer', 'Number'):
                            tostr += ' ' + range
                        elif ttype in ('Binary', 'String', 'Array', 'ArrayOf', 'Map', 'MapOf', 'Record'):
                            tostr += ' (Size ' + range + ')'
                        else:
                            assert False        # Should never get here
                    range = ''
                else:
                    tostr += ' %' + opt + ': ' + str(ov) + '%'
        tdesc = '    -- ' + td[TypeDesc] if td[TypeDesc] else ''
        jas += '\n' + tname + ' ::= ' + stype(ttype) + tostr
        if len(td) > Fields:
            titems = deepcopy(td[Fields])
            for n, i in enumerate(titems):      # 0:tag, 1:enum item name, 2:enum item desc  (enumerated), or
                if len(i) > FieldOptions:              # 0:tag, 1:field name, 2:field type, 3: field opts, 4:field desc
                    desc = i[FieldDesc]
                    i[FieldType] = stype(i[FieldType])
                else:
                    desc = i[ItemDesc]
                desc = '    -- ' + desc if desc else ''
                i.append(',' + desc if n < len(titems) - 1 else (' ' + desc if desc else ''))   # TODO: fix hacked desc for join
            flen = min(32, max(12, max([len(i[FieldName]) for i in titems]) + 1 if titems else 0))
            jas += ' {' + tdesc + '\n'
            if ttype.lower() == 'enumerated':
                fmt = '    {1:' + str(flen) + '} ({0:d}){3}'
                jas += '\n'.join([fmt.format(*i) for i in titems])
            else:
                fmt = '    {1:' + str(flen) + '} [{0:d}] {2}{3}{4}'
                if ttype.lower() == 'record':
                    fmt = '    {1:' + str(flen) + '} {2}{3}{4}'
                items = []
                for n, i in enumerate(titems):                          # TODO: Convert to use jadn2fielddef
                    ostr = ''
                    opts, ftopts = ftopts_s2d(i[FieldOptions])
                    if 'tagid' in opts:
                        ostr += '(Tag(' + str(opts['tagid']) + '))'    # TODO: lookup field name
                        del opts['tagid']
                    if 'vtype' in opts:
                        ostr += '.*'
                        del opts['vtype']
                    if 'minc' in opts:
                        if opts['minc'] == 0:         # TODO: handle array fields (max != 1)
                            ostr += ' OPTIONAL'
                        del opts['minc']
                    items += [fmt.format(i[FieldID], i[FieldName], i[FieldType], ostr, i[5]) + (' %' + str(opts) if opts else '')]
                jas += '\n'.join(items)
            jas += '\n}\n' if titems else '}\n'
        else:
            jas += tdesc + '\n'
    return jas


def jas_dump(schema, fname, source=''):
    with open(fname, 'w') as f:
        if source:
            f.write('-- Generated from ' + source + ', ' + datetime.ctime(datetime.now()) + '\n\n')
        f.write(jas_dumps(schema))
