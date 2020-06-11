"""
Translate JADN to JSON Schema
"""

import json
from jadn.definitions import *
from jadn.utils import topts_s2d, ftopts_s2d, get_config
from jadn.transform.transform import get_enum_items
from datetime import datetime


def dmerge(*dicts):             # Merge any number of dicts
    rv = {}
    for d in dicts:
        rv.update(d)
    return rv


def get_items(stype, ctx):       # return enumerated items if stype is Enumerated
    td = ctx['type_defs']
    et = stype[1:] if stype[0] == OPTION_ID['enum'] else stype
    if et in td and td[et][BaseType] == 'Enumerated':
        to = topts_s2d(td[et][TypeOptions])
        et = to['enum'] if 'enum' in to else et
    if et in td and \
        td[et][BaseType] in ('Enumerated', 'Array', 'Choice', 'Map', 'Record') and \
        'id' not in topts_s2d(td[et][TypeOptions]):
        return [f[ItemValue] for f in td[et][Fields]]


def spaces(s):                  # Return name with dash and underscore replaced with space
    return s.replace('-', ' ').replace('_', ' ')


def fieldname(name):            # Return TypeName converted to FieldName
    return name.lower().replace('-', '_')

# === Return JSON Schema keywords


def w_td(tname, desc):              # Make type and type description
    return {'type': tname, 'description': desc} if desc else {'type': tname}


def w_def(typ):                     # Make definition reference
    return {'#ref': '#/definitions/' + typ}


def w_kvtype(stype, ctx):            # Make definition from ktype or vtype option
    stypes = {'Boolean': 'boolean', 'Integer': 'integer', 'Number': 'number', 'String': 'string'}
    if stype in stypes:
        return {'type': stypes[stype]}
    if stype[0] in (OPTION_ID['enum'], OPTION_ID['pointer']):
        tdef = ctx['type_defs'][stype[1:]]
        topts = topts_s2d(tdef[TypeOptions])
        fields = get_enum_items(tdef, topts, ctx['type_defs'])
        idopt = 'id' in topts
        return w_enum(fields, FieldID if idopt else FieldName, FieldDesc, idopt, ctx)
    return {'$ref': '#/definitions/' + stype}


def w_enum(fields, vcol, dcol, idopt, ctx):
    def pattern(vals):              # Return an enum regex from a list of values
        return '^(' + '|'.join([str(v) for v in vals]) + ')$'

    def fdesc(fld, desc, idopt):    # Make field description
        return fld[FieldName] + ' - ' + desc if idopt else desc

    values = [f[vcol] for f in fields]
    es = ctx['enum_style']
    assert es in ['enum', 'const', 'regex']
    if es == 'regex':
        return {'type': 'string', 'pattern': pattern(values)}
    elif es == 'const':
        return {'oneOf': [{'const': f[vcol], 'description': fdesc(f, f[dcol], idopt)} for f in fields]}
    else:
        return {'enum': values}

def w_export(exp, ctx):          # Make top-level definition header
    if len(exp) == 1:
        return {'$ref': '#/definitions/' + exp[0]}
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {fieldname(ctx['type_defs'][t][TypeName]): {'$ref': '#/definitions/' + t} for t in exp}
    }

def w_ref(tname, ctx):
    nsid, tn = tname.split(':', maxsplit=1) if ':' in tname else [None, tname]
    assert not is_builtin(tn)
    if nsid:
        imp = {'$ref': ctx['meta_imps'][nsid] + '/definitions/' + tn} if ctx['import_style'] == 'ref' else {}
        ctx['imported_types'][nsid].update({tn: imp})
        return {'$ref': '#/imports/' + nsid + '/' + tn}
    return {'$ref': '#/definitions/' + tn}


def w_fdef(f, ctx):                      # Make field definition
    fopts, topts = ftopts_s2d(f[FieldOptions])
    if is_builtin(f[FieldType]):
        t = w_type(['', f[FieldType], [], f[FieldDesc]], topts, ctx)
    else:
        t = dmerge(w_ref(f[FieldType], ctx), {'description': f[FieldDesc]})

    minv = max(fopts['minc'], 1) if 'minc' in fopts else 1
    maxv = fopts['maxc'] if 'maxc' in fopts else 1
    return t if minv <= 1 and maxv == 1 else dmerge(
        {'type': 'array'},
        {'description': f[FieldDesc]},
        {'uniqueItems': True} if 'unique' in topts else {},
        {'minItems': minv} if minv != 0 else {},
        {'maxItems': maxv} if maxv != 0 else {},
        {'items': t}
    )


def w_format(fmt):                  # Make semantic validation keywords
    jadn_fmt = {
        'x': {'contentEncoding': 'base16'},
        # 'eui': {'pattern': r'^([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}$'},
        'eui': {'pattern': r'^([0-9a-fA-F]{2}[:-]){5}[0-9A-Fa-f]{2}(([:-][0-9A-Fa-f]{2}){2})?$'},
        'ipv4-addr': {'pattern': r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])$'},
        'ipv6-addr': {'pattern': r'^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))(%.+)$'},
        'ipv4-net': {'pattern': r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9]?[0-9])(\/(3[0-2]|[0-2]?[0-9]))?$'},
        'ipv6-net': {'pattern': r'^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))(%.+)?s*(\/([0-9]|[1-9][0-9]|1[0-1][0-9]|12[0-8]))?$'},
        'i8': {'minimum': -128, 'maximum': 127},
        'i16': {'minimum': -32768, 'maximum': 32767},
        'i32': {'minimum': -2147483648, 'maximum': 2147483647}
    }
    return (jadn_fmt[fmt] if fmt in jadn_fmt else {'format': fmt}) if fmt else {}

# ========== JADN Types ==========:


def t_binary(tdef, topts, ctx):
    return dmerge(
        w_td('string', tdef[TypeDesc]),
        w_format(topts['format']) if 'format' in topts else {'contentEncoding': 'base64url'},

        # TODO: Fixme: JSON Schema cannot express length of content-encoded data
        # This would require adjusting string length by 2 for hex and 4/3 for base64
        # Impossible to calculate string length for other string formats
        # {'minLength': topts['minv']} if 'minv' in topts and topts['minv'] > 0 else {},
        # {'maxLength': topts['maxv']} if 'maxv' in topts else {}
    )


def t_boolean(tdef, topts, ctx):
    return w_td('boolean', tdef[TypeDesc])


def t_integer(tdef, topts, ctx):
    return dmerge(
        w_td('integer', tdef[TypeDesc]),
        {'minimum': topts['minv']} if 'minv' in topts else {},
        {'maximum': topts['maxv']} if 'maxv' in topts else {}
    )


def t_number(tdef, topts, ctx):
    return dmerge(
        w_td('number', tdef[TypeDesc]),
        {'minimum': topts['minv']} if 'minv' in topts else {},
        {'maximum': topts['maxv']} if 'maxv' in topts else {}
    )


def t_null(tdef, topts, ctx):
    return {}


def t_string(tdef, topts, ctx):
    return dmerge(
        w_td('string', tdef[TypeDesc]),
        w_format(topts['format']) if 'format' in topts else {},
        {'minLength': topts['minv']} if 'minv' in topts and topts['minv'] != 0 else {},
        {'maxLength': topts['maxv']} if 'maxv' in topts and topts['maxv'] != 0 else {},
        {'pattern': topts['pattern']} if 'pattern' in topts else {}
    )


def t_enumerated(tdef, topts, ctx):
    item, tname = (ItemID, 'integer') if 'id' in topts else (ItemValue, 'string')
    fields = get_enum_items(tdef, topts, ctx['type_defs'])
    dcol = FieldDesc if 'enum' in topts or 'pointer' in topts else ItemDesc
    return dmerge(
        w_td(tname, tdef[TypeDesc]),
        w_enum(fields, item, dcol, 'id' in topts, ctx)
    )


def t_choice(tdef, topts, ctx):
    return dmerge(
        w_td('object', tdef[TypeDesc]),
        {'additionalProperties': False, 'minProperties': 1, 'maxProperties': 1},
        {'properties': {f[FieldName]: w_fdef(f, ctx) for f in tdef[Fields]}}
    )


def t_array(tdef, topts, ctx):
    fmt = w_format(topts['format']) if 'format' in topts else {}
    if fmt:
        return dmerge(w_td('string', tdef[TypeDesc]), fmt)
    return dmerge(
        w_td('array', tdef[TypeDesc]),
        {'additionalItems': False},
        {'minItems': topts['minv']} if 'minv' in topts and topts['minv'] != 0 else {},
        {'maxItems': topts['maxv']} if 'maxv' in topts and topts['maxv'] != 0 else {},
        {'items': [w_fdef(f, ctx) for f in tdef[Fields]]}
    )


def t_array_of(tdef, topts, ctx):
    return dmerge(
        w_td('array', tdef[TypeDesc]),
        {'uniqueItems': True} if 'unique' in topts else {},
        {'minItems': topts['minv']} if 'minv' in topts and topts['minv'] != 0 else {},
        {'maxItems': topts['maxv']} if 'maxv' in topts and topts['maxv'] != 0 else {},
        {'items': w_kvtype(topts['vtype'], ctx)}
    )


def t_map(tdef, topts, ctx):
    def req(f):
        fo, to = ftopts_s2d(f[FieldOptions])
        return fo['minc'] >= 1 if 'minc' in fo else True
    required = [f[FieldName] for f in tdef[Fields] if req(f)]
    return dmerge(
        w_td('object', tdef[TypeDesc]),
        {'additionalProperties': False},
        {'required': required} if required else {},
        {'minProperties': topts['minv']} if 'minv' in topts and topts['minv'] != 0 else {},
        {'maxProperties': topts['maxv']} if 'maxv' in topts and topts['maxv'] != 0 else {},
        {'properties': {f[FieldName]: w_fdef(f, ctx) for f in tdef[Fields]}}
    )


def t_map_of(tdef, topts, ctx):
    items = get_items(topts['ktype'], ctx)
    vtype = w_kvtype(topts['vtype'], ctx)
    return dmerge(
        w_td('object', tdef[TypeDesc]),
        {'additionalProperties': False},
        {'minProperties': topts['minv']} if 'minv' in topts and topts['minv'] != 0 else {},
        {'maxProperties': topts['maxv']} if 'maxv' in topts and topts['maxv'] != 0 else {},
        {'patternProperties': {pattern(items): vtype}} if items and ctx['enum_style'] == 'regex' else
        {'properties': {f: vtype for f in items}} if items else {}
    )


def w_type(tdef, topts, ctx):       # Write a JADN type definition in JSON Schema format
    config_max = {
        'Binary':  '$MaxBinary',
        'String':  '$MaxString',
        'Array':   '$MaxElements',
        'ArrayOf': '$MaxElements',
        'Map':     '$MaxElements',
        'MapOf':   '$MaxElements',
        'Record':  '$MaxElements'
    }
    wtype = {
        'Binary': t_binary,
        'Boolean': t_boolean,
        'Integer': t_integer,
        'Number': t_number,
        'Null': t_null,
        'String': t_string,
        'Enumerated': t_enumerated,
        'Choice': t_choice,
        'Array': t_array,
        'ArrayOf': t_array_of,
        'Map': t_map,
        'MapOf': t_map_of,
        'Record': t_map if ctx['verbose'] else t_array
    }
    if 'maxv' in topts and topts['maxv'] == 0:
        topts['maxv'] = ctx['config'][config_max[tdef[BaseType]]]
    sc = wtype[tdef[BaseType]](tdef, topts, ctx)
    if 'and' in topts:
        return {'allOf': [sc, w_ref(topts['and'], ctx)]}
    if 'or' in topts:
        return {'anyOf': [sc, w_ref(topts['or'], ctx)]}
    return sc

# ========== Make JSON Schema ==========


def json_schema_dumps(jadn, verbose=True, enum_style='enum', import_style='any'):  # TODO: use string IDs if verbose=False
    #  verbose True: Record->object, field Names;  False: Record->array, field IDs
    assert enum_style in ('const', 'enum', 'regex')
    #  const: generate oneOf keyword with const for each item
    #  enum: generate an enum keyword containing all items
    #  regex: generate a regular expression that matches each item
    assert import_style in ('any', 'ref')
    #  any: ignore types defined in other modules, validate anything
    #  ref: generate $ref keywords that must be resolved before the JSON Schema can validate referenced types

    meta = jadn['meta'] if 'meta' in jadn else {}
    td = {t[TypeName]: t for t in jadn['types']}    # Build index of type definitions
    exports = [e for e in meta['exports'] if e in td] if 'exports' in meta else []
    imported_types = {k: {} for k in meta['imports']} if 'imports' in meta else {}
    ctx = {                                         # Translation context
        'config': get_config(meta),
        'type_defs': td,
        'verbose': verbose,
        'enum_style': enum_style,
        'imported_types': imported_types,
        'import_style': import_style,
        'meta_imps': meta['imports'] if 'imports' in meta else None
    }

    def tt(tdef, ctx):                              # Return type definition with title
        topts = topts_s2d(tdef[TypeOptions])
        return dmerge({'title': spaces(tdef[TypeName])}, w_type(tdef, topts, ctx))

    return json.dumps(dmerge(
        {'$schema': 'http://json-schema.org/draft-07/schema#'},
        {'$id': meta['module'] if 'module' in meta else ''},
        {'title': meta['title'] if 'title' in meta else ''},
        {'description': meta['description']} if 'description' in meta else {},
        w_export(exports, ctx),
        {'definitions': {t: tt(td[t], ctx) for t in (exports + [t for t in td if t not in exports])}},
        {'imports': imported_types} if imported_types else {}
    ), indent=2)


def json_schema_dump(jadn, fname, source=None, verbose=True, enum_style='enum', import_style='ref'):
    with open(fname, 'w') as f:
        if source:
            f.write('/* Generated from ' + source + ', ' + datetime.ctime(datetime.now()) + ' */\n\n')
        f.write(json_schema_dumps(jadn, verbose, enum_style, import_style))
