import numbers
import re

from dataclasses import dataclass
from frozendict import frozendict
from typing import Any, Callable, Dict, NoReturn, Optional, Union
from ..utils import raise_error
from ..definitions import FieldID, FieldName, BasicDataclass, TypeDefinition, GenFieldDefinition
# TODO: add DEFAULT to dataclasses


def echo(val: Any) -> Any:
    return val


# Symbol Table Field Definition fields
@dataclass
class SymbolTableFieldDefinition(BasicDataclass):
    Def: GenFieldDefinition     # 0: JADN field definition
    Opt: dict                   # 1: Field Options (dict format)
    cTag: Optional[int]         # 2: Field containing external choice tag (tagid option)


# Symbol Table fields
@dataclass
class SymbolTableField(BasicDataclass):
    TypeDef: TypeDefinition                                     # 0: JADN type definition
    Encode: Callable[['SymbolTableField', Any, 'Codec'], Any]   # 1: Encoder for this type
    Decode: Callable[['SymbolTableField', Any, 'Codec'], Any]   # 2: Decoder for this type
    EncType: type                                               # 3: Encoded value type
    TypeOpts: dict                                              # 4: Type Options (dict format)
    # 5: Format semantic validation - returns True if valid
    FormatValidate: Callable[[Any], Any] = echo
    # 6: Format encode conversion - returns serialized data representation
    FormatEncode: Callable[[Any], Any] = echo
    # 7: Format decode conversion - returns API value
    FormatDecode: Callable[[Any], Any] = echo
    # 8: Decode: Encoded field key or enum value to API
    dMap: Dict[Union[int, str], Union[int, str]] = None
    # 9: Decode: Encode: API field key or enum value to Encoded
    eMap: Dict[Union[int, str], Union[int, str]] = None
    # 10: Field entries (definition and decoded options)
    Fld: Dict[str, SymbolTableFieldDefinition] = None


# Codec Table fields
@dataclass
class CodecTableField(BasicDataclass):
    # 0: Decode function
    Dec: Callable[[SymbolTableField, Any, 'Codec'], Any] = None
    # 1: Encode function
    Enc: Callable[[SymbolTableField, Any, 'Codec'], Any] = None
    # 2: Encoded type
    eType: type = None


def fset(x):
    if isinstance(x, dict):
        return frozendict({k: fset(v) for k, v in x.items()})
    try:
        return frozenset(x) if isinstance(x, (tuple, list, set)) else x
    except TypeError as e:
        return frozenset((fset(v) for v in x))


def _bad_index(ts: SymbolTableField, k: int, val: list) -> NoReturn:
    td = ts.TypeDef
    raise_error(f'{td.TypeName}({td.BaseType}): array index {k} out of bounds ({len(ts.Fld)}, {len(val)})')


def _bad_choice(ts: SymbolTableField, val: Any) -> NoReturn:
    td = ts.TypeDef
    raise_error(f'{td.TypeName}: choice must have one value: {val}')


def _bad_value(ts: SymbolTableField, val: Any, fld: GenFieldDefinition = None) -> NoReturn:
    td = ts.TypeDef
    if fld is not None:
        raise_error(f'{td.TypeName}({td.BaseType}): missing required field "{fld.FieldName}": {val}')
    else:
        v = next(iter(val)) if isinstance(val, dict) else val
        raise_error(f'{td.TypeName}({td.BaseType}): bad value: {v}')


# fail forces rejection of boolean vals for number types
def _check_type(ts: SymbolTableField, val: Any, vtype: type, fail=False) -> NoReturn:
    if vtype is not None:
        if fail or not isinstance(val, vtype):
            td = ts.TypeDef
            tn = f"{td.TypeName}({td.BaseType if td else 'Primitive'})"
            raise_error(f'{tn}: {val} is not {vtype}')


def _format_encode(ts: SymbolTableField, val: Any) -> Any:
    try:
        ts.FormatValidate(val)
    except ValueError:
        raise_error(f'{ts.TypeDef.TypeName}: {val} is not format "{ts.TypeOpts["format"]}"')
    return ts.FormatEncode(val)


def _format_decode(ts: SymbolTableField, val: Any) -> Any:
    aval = ts.FormatDecode(val)
    try:
        ts.FormatValidate(aval)
    except ValueError:
        raise_error(f'{ts.TypeDef.TypeName}: {val} is not format "{ts.TypeOpts["format"]}"')
    return aval


def _check_key(ts: SymbolTableField, val):
    try:
        return int(val) if isinstance(next(iter(ts.dMap)), int) else val
    except ValueError:
        raise_error(f'{ts.TypeDef.TypeName}: {val} is not a valid field ID')


def _check_pattern(ts: SymbolTableField, val):
    op = ts.TypeOpts
    if 'pattern' in op and not re.match(op['pattern'], val):
        tn = ts.TypeDef.TypeName
        raise_error(f'{tn}: string "{val}" does not match {op["pattern"]}')
    return val


def _check_range(ts: SymbolTableField, val):
    op = ts.TypeOpts
    tn = ts.TypeDef.TypeName
    if 'minv' in op and val < op['minv']:
        raise_error(f'{tn}: {val} < minimum {op["minv"]}')
    if 'maxv' in op and val > op['maxv']:
        raise_error(f'{tn}: {val} < maximum {op["maxv"]}')
    return val


def _check_frange(ts: SymbolTableField, val):
    op = ts.TypeOpts
    tn = ts.TypeDef.TypeName
    if 'minf' in op and val < op['minf']:
        raise_error(f'{tn}: {val} < minimum {op["minf"]}')
    if 'maxf' in op and val > op['maxf']:
        raise_error(f'{tn}: {val} < maximum {op["maxf"]}')
    return val


def _check_size(ts: SymbolTableField, val):
    op = ts.TypeOpts
    tn = ts.TypeDef.TypeName
    if 'minv' in op and len(val) < op['minv']:
        raise_error(f'{tn}: length {len(val)} < minimum {op["minv"]}')
    if 'maxv' in op and len(val) > op['maxv']:
        raise_error(f'{tn}: length {len(val)} > maximum {op["maxv"]}')
    return val


def _check_count(ts: SymbolTableField, val):
    op = ts.TypeOpts
    tn = ts.TypeDef.TypeName
    cnt = len([k for k in val if k is not None])
    if 'minv' in op and cnt < op['minv']:
        raise_error(f'{tn}: length {cnt} < minimum {op["minv"]}')
    if 'maxv' in op and cnt > op['maxv']:
        raise_error(f'{tn}: length {len(val)} > maximum {op["maxv"]}')
    return val


def _extra_value(ts: SymbolTableField, val, extra: set):
    td = ts.TypeDef
    raise_error(f'{td.TypeName}({td.BaseType}): unexpected field: \"{", ".join(str(k) for k in extra)}\"')


def _encode_binary(ts: SymbolTableField, aval, codec: 'Codec'):    # Encode bytes to string
    _check_type(ts, aval, bytes)
    _check_size(ts, aval)
    return _format_encode(ts, aval)


def _decode_binary(ts: SymbolTableField, sval, codec: 'Codec'):    # Decode ASCII string to bytes
    aval = _format_decode(ts, sval)
    _check_type(ts, aval, bytes)        # assert format decode returns correct type
    return _check_size(ts, aval)


def _encode_boolean(ts: SymbolTableField, val, codec: 'Codec'):
    _check_type(ts, val, bool)
    return val


def _decode_boolean(ts: SymbolTableField, val, codec: 'Codec'):
    _check_type(ts, val, bool)
    return val


def _encode_integer(ts: SymbolTableField, aval, codec: 'Codec'):
    _check_type(ts, aval, numbers.Integral, isinstance(aval, bool))
    _check_range(ts, aval)
    return _format_encode(ts, aval)


def _decode_integer(ts: SymbolTableField, sval, codec: 'Codec'):
    aval = _format_decode(ts, sval)
    _check_type(ts, aval, numbers.Integral, isinstance(aval, bool))
    return _check_range(ts, aval)


def _encode_number(ts: SymbolTableField, aval, codec: 'Codec'):
    _check_type(ts, aval, numbers.Real, isinstance(aval, bool))
    _check_frange(ts, aval)
    return _format_encode(ts, aval)


def _decode_number(ts: SymbolTableField, sval, codec: 'Codec'):
    aval = _format_decode(ts, sval)
    _check_type(ts, aval, numbers.Real, isinstance(aval, bool))
    return _check_range(ts, aval)


def _encode_string(ts: SymbolTableField, aval, codec: 'Codec'):
    _check_type(ts, aval, type(''))
    _check_size(ts, aval)
    _check_pattern(ts, aval)
    return _format_encode(ts, aval)


def _decode_string(ts: SymbolTableField, sval, codec: 'Codec'):
    aval = _format_decode(ts, sval)
    _check_type(ts, aval, type(''))
    _check_size(ts, aval)
    return _check_pattern(ts, aval)


def _encode_enumerated(ts: SymbolTableField, aval, codec: 'Codec'):  # pylint: disable=R1710
    # TODO: Serialization
    _check_type(ts, aval, type(next(iter(ts.eMap))))
    if aval in ts.eMap:
        return ts.eMap[aval]
    td = ts.TypeDef
    raise_error(f'{td.BaseType}: {aval} is not a valid {td.TypeName}')


def _decode_enumerated(ts: SymbolTableField, sval, codec: 'Codec'):  # pylint: disable=R1710
    _check_type(ts, sval, type(next(iter(ts.dMap))))
    if sval in ts.dMap:
        return ts.dMap[sval]
    td = ts.TypeDef
    raise_error(f'{td.BaseType}: {sval} is not a valid {td.TypeName}')


def _encode_choice(ts: SymbolTableField, val, codec: 'Codec'):
    _check_type(ts, val, dict)
    if len(val) != 1:
        _bad_choice(ts, val)
    k, v = next(iter(val.items()))
    if k not in ts.eMap:
        _bad_value(ts, val)
    k = ts.eMap[k]
    f = ts.Fld[k].Def
    return {k: codec.encode(f.FieldType, v)}


def _decode_choice(ts: SymbolTableField, val, codec: 'Codec'):  # Map Choice:  val == {key: value}
    _check_type(ts, val, dict)
    if len(val) != 1:
        _bad_choice(ts, val)
    k, v = next(iter(val.items()))
    k = _check_key(ts, k)
    if k not in ts.dMap:
        _bad_value(ts, val)
    f = ts.Fld[k].Def
    k = ts.dMap[k]
    return {k: codec.decode(f.FieldType, v)}


def _encode_maprec(ts: SymbolTableField, aval, codec: 'Codec'):
    _check_type(ts, aval, dict)
    _check_size(ts, aval)
    sval = ts.EncType()
    assert isinstance(sval, (list, dict))
    fx = FieldName if codec.verbose_str else FieldID  # Verbose or minified identifier strings
    fnames = [f.Def.FieldName for f in ts.Fld.values()]
    for f in ts.TypeDef.Fields:
        fs = ts.Fld[f[fx]]  # Symtab entry for field
        fd = fs.Def  # JADN field definition from symtab
        fname = fd[FieldName]  # Field name
        fopts = fs.Opt  # Field options dict
        ctag = fs.cTag
        if ctag is not None:  # Type of this field is specified by contents of another field
            e = codec.encode(fd.FieldType, {aval[ctag]: aval[fname]})
            sv = next(iter(e.values()))
        else:
            sv = codec.encode(fd.FieldType, aval[fname]) if fname in aval else None
        if sv is None and ('minc' not in fopts or fopts['minc'] > 0):  # Missing required field
            _bad_value(ts, aval, fd)
        if isinstance(sval, list):  # Concise Record
            sval.append(sv)
        elif sv is not None:  # Map or Verbose Record
            sval[fd[fx]] = sv

    if extras := set(aval) - set(fnames):
        _extra_value(ts, aval, extras)
    if isinstance(sval, list):
        while sval and sval[-1] is None:  # Strip non-populated trailing optional values
            sval.pop()
    return sval


def _decode_maprec(ts: SymbolTableField, sval, codec: 'Codec'):
    _check_type(ts, sval, ts.EncType)
    _check_size(ts, sval)   # TODO: _check_count() for concise records
    val = sval
    if ts.EncType == dict:
        val = {_check_key(ts, k): v for k, v in sval.items()}
    aval = dict()
    fx = FieldName if codec.verbose_str else FieldID  # Verbose or minified identifier strings
    fnames = list(ts.Fld)
    for f in ts.TypeDef.Fields:
        fs = ts.Fld[f[fx]]  # Symtab entry for field
        fd = fs.Def  # JADN field definition from symtab
        fopts = fs.Opt  # Field options dict
        if isinstance(val, dict):
            fn = f[fx]
            sv = val[fn] if fn in val else None
        else:
            fn = fd[FieldID] - 1
            sv = val[fn] if len(val) > fn else None
        if sv is not None:
            ctag = fs.cTag
            if ctag is not None:  # Type of this field is specified by contents of another field
                ct = ctag if isinstance(val, dict) else ts.eMap[ctag] - 1
                av = codec.decode(fd.FieldType, {sval[ct]: sv})
                aval[fd[FieldName]] = next(iter(av.values()))
            else:
                aval[fd[FieldName]] = codec.decode(fd.FieldType, sv)
        else:
            if 'minc' not in fopts or fopts['minc'] > 0:
                _bad_value(ts, val, fd)
    extra = set(val) - set(fnames) if isinstance(val, dict) else set(val[len(ts.Fld):])
    if extra:
        _extra_value(ts, val, extra)
    return aval


def _encode_array(ts: SymbolTableField, aval, codec: 'Codec'):
    _check_type(ts, aval, list)
    _check_count(ts, aval)
    sval = list()
    if len(aval) > len(ts.Fld):
        _extra_value(ts, aval, set(aval[len(ts.Fld):]))
    for fn in ts.TypeDef.Fields:
        f = ts.Fld[fn.FieldID].Def  # Use symtab field definition
        fx = f.FieldID - 1
        fopts = ts.Fld[fx + 1].Opt
        av = aval[fx] if len(aval) > fx else None
        if av is not None:
            if 'tagid' in fopts:
                choice_type = aval[int(fopts['tagid']) - 1]
                e = codec.encode(f.FieldType, {choice_type: av})
                sv = e[next(iter(e))]
            else:
                sv = codec.encode(f.FieldType, av)
            sval.append(sv)
        else:
            sval.append(None)
            if 'minc' in fopts and fopts['minc'] > 0:   # Value is required
                _bad_value(ts, aval, f)
    while sval and sval[-1] is None:            # Strip non-populated trailing optional values
        sval.pop()
    return _format_encode(ts, sval)


def _decode_array(ts: SymbolTableField, sval, codec: 'Codec'):  # Ordered list of types, returned as a list
    val = _format_decode(ts, sval)
    _check_type(ts, val, list)
    _check_count(ts, sval)
    aval = list()
    if len(val) > len(ts.Fld):
        _extra_value(ts, val, set(aval[len(ts.Fld):]))
    for fn in ts.TypeDef.Fields:
        f = ts.Fld[fn[FieldID]].Def  # Use symtab field definition
        fx = f[FieldID] - 1
        fopts = ts.Fld[fx + 1].Opt
        sv = val[fx] if len(val) > fx else None
        if sv is not None:
            if 'tagid' in fopts:
                choice_type = val[int(fopts['tagid']) - 1]
                d = codec.decode(f.FieldType, {choice_type: sv})  # TODO: fix str/int handling of choice
                av = d[next(iter(d))]
            else:
                av = codec.decode(f.FieldType, sv)
            aval.append(av)
        else:
            aval.append(None)
            if 'minc' not in fopts or fopts['minc'] > 0:
                _bad_value(ts, val, f)
    while aval and aval[-1] is None:  # Strip non-populated trailing optional values
        aval.pop()
    return aval


def _encode_array_of(ts: SymbolTableField, val, codec: 'Codec'):
    _check_type(ts, val, list)
    _check_size(ts, val)
    if 'set' in ts.TypeOpts or 'unique' in ts.TypeOpts:
        if len(val) != len(fset(val)):
            _bad_value(ts, val)
    return [codec.encode(ts.TypeOpts['vtype'], v) for v in val]


def _decode_array_of(ts: SymbolTableField, val, codec: 'Codec'):
    _check_type(ts, val, list)
    _check_size(ts, val)
    if 'set' in ts.TypeOpts or 'unique' in ts.TypeOpts:
        if len(val) != len(fset(val)):
            _bad_value(ts, val)
    return [codec.decode(ts.TypeOpts['vtype'], v) for v in val]


def _encode_map_of(ts: SymbolTableField, aval, codec: 'Codec'):
    _check_type(ts, aval, dict)
    _check_size(ts, aval)
    to = ts.TypeOpts
    return {codec.encode(to['ktype'], k): codec.encode(to['vtype'], v) for k, v in aval.items()}


def _decode_map_of(ts: SymbolTableField, sval, codec: 'Codec'):
    _check_type(ts, sval, dict)
    _check_size(ts, sval)
    return {k: codec.decode(ts.TypeOpts['vtype'], v) for k, v in sval.items()}


enctab: Dict[str, CodecTableField] = {  # decode, encode, min encoded type
    'Binary': CodecTableField(_decode_binary, _encode_binary, str),
    'Boolean': CodecTableField(_decode_boolean, _encode_boolean, bool),
    'Integer': CodecTableField(_decode_integer, _encode_integer, int),
    'Number': CodecTableField(_decode_number, _encode_number, float),
    'String': CodecTableField(_decode_string, _encode_string, str),
    'Enumerated': CodecTableField(_decode_enumerated, _encode_enumerated, int),
    'Choice': CodecTableField(_decode_choice, _encode_choice, dict),
    'Array': CodecTableField(_decode_array, _encode_array, list),
    'ArrayOf': CodecTableField(_decode_array_of, _encode_array_of, list),
    'Map': CodecTableField(_decode_maprec, _encode_maprec, dict),
    'MapOf': CodecTableField(_decode_map_of, _encode_map_of, dict),
    'Record': CodecTableField(),  # Dynamic values
}
