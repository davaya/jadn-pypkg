"""
Translate JADN to JSON Schema
"""
import json
import re

from datetime import datetime
from typing import Callable, Optional, Union
from ..definitions import (
    TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemID, ItemValue, ItemDesc, FieldID, FieldName, FieldType,
    FieldOptions, FieldDesc, OPTION_ID, is_builtin
)
from ..transform.transform import get_enum_items
from ..utils import dmerge, topts_s2d, ftopts_s2d, get_config


# Consts
JADN_FMT = {
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

CONFIG_MAX = {
    'Binary': '$MaxBinary',
    'String': '$MaxString',
    'Array': '$MaxElements',
    'ArrayOf': '$MaxElements',
    'Map': '$MaxElements',
    'MapOf': '$MaxElements',
    'Record': '$MaxElements'
}


# Util Functions
def get_items(stype: str, ctx: dict) -> Optional[list]:  # pylint: disable=R1710
    """
    return enumerated items if stype is Enumerated
    """
    td = ctx['type_defs']
    et = stype[1:] if stype[0] == OPTION_ID['enum'] else stype
    if et in td and td[et][BaseType] == 'Enumerated':
        to = topts_s2d(td[et][TypeOptions])
        et = to['enum'] if 'enum' in to else et

    to = topts_s2d(td[et][TypeOptions])
    if et in td and td[et][BaseType] in ('Enumerated', 'Array', 'Choice', 'Map', 'Record') and 'id' not in to:
        return [f[ItemValue] for f in td[et][Fields]]


def spaces(s: str) -> str:
    """
    Return name with dash and underscore replaced with space
    """
    return re.sub(r'[\-_]', ' ', s)


def fieldname(name: str) -> str:
    """
    Return TypeName converted to FieldName
    """
    return name.lower().replace('-', '_')


def pattern(vals: list) -> str:
    """
    Return a regex string from a list of values
    """

    return f"^({'|'.join(map(str, vals))})$"


# === Return JSON Schema keywords
def w_td(tname: str, desc: str) -> dict:
    """
    Make type and type description
    """
    return dmerge(
        {'type': tname},
        {'description': desc} if desc else {}
    )


def w_def(typ: str) -> dict:
    """
    Make definition reference
    """
    return {'#ref': f'#/definitions/{typ}'}


def w_kvtype(stype: str, ctx: dict) -> dict:
    """
    Make definition from ktype or vtype option
    """
    stypes = {'Boolean': 'boolean', 'Integer': 'integer', 'Number': 'number', 'String': 'string'}
    if stype in stypes:
        return {'type': stypes[stype]}
    if stype[0] in (OPTION_ID['enum'], OPTION_ID['pointer']):
        tdef = ctx['type_defs'][stype[1:]]
        topts = topts_s2d(tdef[TypeOptions])
        fields = get_enum_items(tdef, topts, ctx['type_defs'])
        idopt = 'id' in topts
        return w_enum(fields, FieldID if idopt else FieldName, FieldDesc, idopt, ctx)
    return {'$ref': f'#/definitions/{stype}'}


def w_enum(fields: list, vcol: int, dcol: int, idopt: bool, ctx: dict) -> dict:
    def fdesc(fld: list, desc: str, idopt: bool) -> str:
        """
        Make field description
        """
        return f'{fld[FieldName]} - {desc}' if idopt else desc

    values = [f[vcol] for f in fields]
    es = ctx['enum_style']
    assert es in ['enum', 'const', 'regex']
    if es == 'regex':
        return {'type': 'string', 'pattern': pattern(values)}
    if es == 'const':
        return {'oneOf': [{'const': f[vcol], 'description': fdesc(f, f[dcol], idopt)} for f in fields]}
    return {'enum': values}


def w_export(exp: list, ctx: dict) -> dict:
    """
    Make top-level definition header
    """
    if len(exp) == 1:
        return {'$ref': f'#/definitions/{exp[0]}'}
    return {
        'type': 'object',
        'additionalProperties': False,
        'properties': {fieldname(ctx['type_defs'][t][TypeName]): {'$ref': f'#/definitions/{t}'} for t in exp}
    }


def w_ref(tname: str, ctx: dict) -> dict:
    nsid, tn = tname.split(':', maxsplit=1) if ':' in tname else [None, tname]
    assert not is_builtin(tn)
    if nsid:
        imp = {'$ref': f"{ctx['info_imps'][nsid]}/definitions/{tn}"} if ctx['import_style'] == 'ref' and ctx['info_imps'] is not None else {}
        ctx['imported_types'][nsid].update({tn: imp})
        return {'$ref': f'#/imports/{nsid}/{tn}'}
    return {'$ref': f'#/definitions/{tn}'}


def w_fdef(f: list, ctx: dict) -> dict:
    """
    Make field definition
    """
    fopts, topts = ftopts_s2d(f[FieldOptions])
    if is_builtin(f[FieldType]):
        t = w_type(['', f[FieldType], [], f[FieldDesc]], topts, ctx)
    else:
        t = dmerge(w_ref(f[FieldType], ctx), {'description': f[FieldDesc]})

    minv = max(fopts.get('minc', 1), 1)
    maxv = fopts.get('maxc', 1)
    return t if minv <= 1 and maxv == 1 else dmerge(
        {'type': 'array'},
        {'description': f[FieldDesc]},
        {'uniqueItems': True} if 'unique' in topts else {},
        {'minItems': minv} if minv != 0 else {},
        {'maxItems': maxv} if maxv != 0 else {},
        {'items': t}
    )


def w_format(fmt: str) -> dict:
    """
    Make semantic validation keywords
    """
    if fmt:
        if jadn_fmt := JADN_FMT.get(fmt, None):
            return jadn_fmt
        return {'format': fmt}
    return {}


# ========== JADN Types ==========:
def t_binary(tdef: list, topts: dict, ctx: dict) -> dict:
    return dmerge(
        w_td('string', tdef[TypeDesc]),
        w_format(topts['format']) if 'format' in topts else {'contentEncoding': 'base64url'},
        # TODO: Fixme: JSON Schema cannot express length of content-encoded data
        # This would require adjusting string length by 2 for hex and 4/3 for base64
        # Impossible to calculate string length for other string formats
        # {'minLength': topts['minv']} if 'minv' in topts and topts['minv'] > 0 else {},
        # {'maxLength': topts['maxv']} if 'maxv' in topts else {}
    )


def t_boolean(tdef: list, topts: dict, ctx: dict) -> dict:
    return w_td('boolean', tdef[TypeDesc])


def t_integer(tdef: list, topts: dict, ctx: dict) -> dict:
    return dmerge(
        w_td('integer', tdef[TypeDesc]),
        {'minimum': topts['minv']} if 'minv' in topts else {},
        {'maximum': topts['maxv']} if 'maxv' in topts else {}
    )


def t_number(tdef: list, topts: dict, ctx: dict) -> dict:
    return dmerge(
        w_td('number', tdef[TypeDesc]),
        {'minimum': topts['minf']} if 'minf' in topts else {},
        {'maximum': topts['maxf']} if 'maxf' in topts else {}
    )


def t_null(tdef: list, topts: dict, ctx: dict) -> dict:
    return {}


def t_string(tdef: list, topts: dict, ctx: dict) -> dict:
    return dmerge(
        w_td('string', tdef[TypeDesc]),
        w_format(topts['format']) if 'format' in topts else {},
        {'minLength': topts['minv']} if 'minv' in topts and topts['minv'] != 0 else {},
        {'maxLength': topts['maxv']} if 'maxv' in topts else {},
        {'pattern': topts['pattern']} if 'pattern' in topts else {}
    )


def t_enumerated(tdef: list, topts: dict, ctx: dict) -> dict:
    item, tname = (ItemID, 'integer') if 'id' in topts else (ItemValue, 'string')
    fields = get_enum_items(tdef, topts, ctx['type_defs'])
    dcol = FieldDesc if 'enum' in topts or 'pointer' in topts else ItemDesc
    return dmerge(
        w_td(tname, tdef[TypeDesc]),
        w_enum(fields, item, dcol, 'id' in topts, ctx)
    )


def t_choice(tdef: list, topts: dict, ctx: dict) -> dict:
    if combine := topts.get('combine'):
        c = {'O': 'anyOf', 'A': 'allOf', 'X': 'oneOf'}[combine]
        return {c: [w_ref(f[FieldType], ctx) for f in tdef[Fields]]}

    return dmerge(
        w_td('object', tdef[TypeDesc]),
        {
            'additionalProperties': False,
            'minProperties': 1,
            'maxProperties': 1,
            'properties': {f[FieldName]: w_fdef(f, ctx) for f in tdef[Fields]}
        }
    )


def t_array(tdef: list, topts: dict, ctx: dict) -> dict:
    fmt = w_format(topts['format']) if 'format' in topts else {}
    if fmt:
        return dmerge(w_td('string', tdef[TypeDesc]), fmt)
    return dmerge(
        w_td('array', tdef[TypeDesc]),
        {'additionalItems': False},
        {'minItems': topts['minv']} if topts.get('minv', 0) != 0 else {},
        {'maxItems': topts['maxv']} if 'maxv' in topts else {},
        {'items': [w_fdef(f, ctx) for f in tdef[Fields]]}
    )


def t_array_of(tdef: list, topts: dict, ctx: dict) -> dict:
    return dmerge(
        w_td('array', tdef[TypeDesc]),
        {'uniqueItems': True} if 'unique' in topts else {},
        {'minItems': topts['minv']} if topts.get('minv', 0) != 0 else {},
        {'maxItems': topts['maxv']} if 'maxv' in topts else {},
        {'items': w_kvtype(topts['vtype'], ctx)}
    )


def t_map(tdef: list, topts: dict, ctx: dict) -> dict:
    def req(f: list) -> bool:
        fo = ftopts_s2d(f[FieldOptions])[0]
        return fo['minc'] >= 1 if 'minc' in fo else True

    required = [f[FieldName] for f in tdef[Fields] if req(f)]
    return dmerge(
        w_td('object', tdef[TypeDesc]),
        {'additionalProperties': False},
        {'required': required} if required else {},
        {'minProperties': topts['minv']} if topts.get('minv', 0) != 0 else {},
        {'maxProperties': topts['maxv']} if 'maxv' in topts else {},
        {'properties': {f[FieldName]: w_fdef(f, ctx) for f in tdef[Fields]}}
    )


def t_map_of(tdef: list, topts: dict, ctx: dict) -> dict:
    items = get_items(topts['ktype'], ctx)
    vtype = w_kvtype(topts['vtype'], ctx)
    ktype = w_kvtype(topts['ktype'], ctx)
    
    opts = tdef[TypeOptions]
    k_opt = opts[0]
    k_name = k_opt[1:]
    
    v_opt = opts[1]
    v_name = v_opt[1:]
    
    key_array = ctx.get('type_defs', {}).get(k_name)
    key_type = key_array[1]
    
    merged = {}
    if key_type == 'String':
        merged = dmerge(
            w_td('object', tdef[TypeDesc]),
            {'additionalProperties': False},
            {'minProperties': topts['minv']} if topts.get('minv', 0) != 0 else {},
            {'maxProperties': topts['maxv']} if 'maxv' in topts else {},
            {'patternProperties': {pattern(items): vtype}} if items and ctx['enum_style'] == 'regex' else {}
        )
        
        properties = {
            k_name : ktype,
            v_name : vtype
        }        
        
        merged['properties'] = properties
    else:
        merged = dmerge(
            w_td('array', tdef[TypeDesc]),
            {'additionalItems': False},
            {'uniqueItems': True},
            {'minItems': topts['minv']} if topts.get('minv', 0) != 0 else {},
            {'maxItems': topts['maxv']} if 'maxv' in topts else {},
        )
        
        prefix_items = [
            {k_name : ktype},
            {v_name : vtype}
        ]
        
        merged['items'] = prefix_items        
    
    return merged


# Type Map Util
TYPE_WRITERS = {
    'Binary': t_binary,
    'Boolean': t_boolean,
    'Integer': t_integer,
    'Number': t_number,
    'String': t_string,
    'Enumerated': t_enumerated,
    'Choice': t_choice,
    'Array': t_array,
    'ArrayOf': t_array_of,
    'Map': t_map,
    'MapOf': t_map_of
}


def get_writer(btype: str, verbose=False) -> Callable[[list, dict, dict], dict]:
    if writer := TYPE_WRITERS.get(btype, None):
        return writer
    if btype == 'Record':
        return t_map if verbose else t_array
    raise TypeError(f'{btype} is not a valid base type')


def w_type(tdef: list, topts: dict, ctx: dict) -> dict:
    """
    Write a JADN type definition in JSON Schema format
    """
    if 'maxv' not in topts and tdef[BaseType] in CONFIG_MAX:
        topts['maxv'] = ctx['config'][CONFIG_MAX[tdef[BaseType]]]
    sc = get_writer(tdef[BaseType], ctx['verbose'])(tdef, topts, ctx)
    return sc


# ========== Make JSON Schema ==========
# TODO: use string IDs if verbose=False
def json_schema_dumps(schema: dict, verbose=True, enum_style='enum', import_style='any'):
    #  verbose True: Record->object, field Names;  False: Record->array, field IDs
    assert enum_style in ('const', 'enum', 'regex')
    #  const: generate oneOf keyword with const for each item
    #  enum: generate an enum keyword containing all items
    #  regex: generate a regular expression that matches each item
    assert import_style in ('any', 'ref')
    #  any: ignore types defined in other modules, validate anything
    #  ref: generate $ref keywords that must be resolved before the JSON Schema can validate referenced types

    info = schema.get('info', {})
    td = {t[TypeName]: t for t in schema['types']}    # Build index of type definitions
    exports = [e for e in info.get('exports', []) if e in td]
    if isinstance(ns := info.get('namespaces', {}), dict):
        imported_types = {k: {} for k in ns}
    elif isinstance(ns, list):
        imported_types = {k[0]: {} for k in ns}
    ctx = {  # Translation context
        'config': get_config(info),
        'type_defs': td,
        'verbose': verbose,
        'enum_style': enum_style,
        'imported_types': imported_types,
        'import_style': import_style,
        'info_imps': info['imports'] if 'imports' in info else None
    }

    def tt(tdef: list, ctx: dict):  # Return type definition with title
        return dmerge(
            {'title': spaces(tdef[TypeName])},
            w_type(tdef, topts_s2d(tdef[TypeOptions]), ctx)
        )

    return json.dumps(dmerge(
        {'$schema': 'http://json-schema.org/draft-07/schema#'},
        {'$id': info['package']} if 'package' in info else {},
        {'title': info['title']} if 'title' in info else {},    # TODO: use items from INFO_ORDER
        {'version': info['version']} if 'version' in info else {},
        {'description': info['description']} if 'description' in info else {},
        {'comments': info['comments']} if 'comments' in info else {},
        {'copyright': info['copyright']} if 'copyright' in info else {},
        {'license': info['license']} if 'license' in info else {},
        w_export(exports, ctx),
        {'definitions': {t: tt(td[t], ctx) for t in (exports + [t for t in td if t not in exports])}},
        {'imports': imported_types} if imported_types else {}
    ), indent=2)


def json_schema_dump(jadn: dict, fname: Union[str, bytes, int], source=None, verbose=True, enum_style='enum', import_style='ref'):
    with open(fname, 'w') as f:
        if source:
            f.write(f'/* Generated from {source}, {datetime.ctime(datetime.now())} */\n\n')
        f.write(json_schema_dumps(jadn, verbose, enum_style, import_style))
