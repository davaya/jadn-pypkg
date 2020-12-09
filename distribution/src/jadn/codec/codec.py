"""
Abstract Object Encoder/Decoder

Object schema is specified in JSON Abstract Data Notation (JADN) format.

Codec currently supports three JSON concrete message formats (verbose,
concise, and minified) but can be extended to support XML or binary formats.

Copyright 2016, 2019 David Kemp
Licensed under the Apache License, Version 2.0
http://www.apache.org/licenses/LICENSE-2.0
"""

import numbers
import re

from typing import Any, Dict, List, Optional, NoReturn
from jadn.utils import raise_error, topts_s2d, ftopts_s2d, get_config
from jadn.definitions import (
    # Field Indexes
    TypeName, BaseType, TypeOptions, Fields, FieldID, FieldName, FieldType, FieldOptions,
    # Const values
    SIMPLE_TYPES, CORE_TYPES
)
from jadn.transform import simplify
from jadn.codec.format_validate import format_validators, get_format_validate_function
from jadn.codec.format_serialize_json import json_format_codecs, get_format_encode_function, get_format_decode_function

__version__ = '0.2'

# TODO: add DEFAULT

# Codec Table fields
C_DEC = 0       # Decode function
C_ENC = 1       # Encode function
C_ETYPE = 2     # Encoded type

# Symbol Table fields
S_TDEF = 0      # JADN type definition
S_ENCODE = 1    # Encoder for this type
S_DECODE = 2    # Decoder for this type
S_ENCTYPE = 3   # Encoded value type
S_TOPTS = 4     # Type Options (dict format)
S_FVALIDATE = 5 # Format semantic validation - returns True if valid
S_FENCODE = 6   # Format encode conversion - returns serialized data representation
S_FDECODE = 7   # Format decode conversion - returns API value
S_DMAP = 8      # Decode: Encoded field key or enum value to API
S_EMAP = 9      # Encode: API field key or enum value to Encoded
S_FLD = 10      # Field entries (definition and decoded options)

# Symbol Table Field Definition fields
SF_DEF = 0      # JADN field definition
SF_OPT = 1      # Field Options (dict format)
SF_CTAG = 2     # Field containing external choice tag (tagid option)


class Codec:
    """
    Serialize (encode) and De-serialize (decode) values, validate against JADN syntax.

    verbose_rec - True: Record types encoded as maps
                 False: Record types encoded as arrays
    verbose_str - True: Identifiers encoded as strings
                 False: Identifiers encoded as integer tags
    """
    schema: dict  # better typing??
    config: dict  # better typing??
    format_validators: dict  # better typing??
    format_codec: dict  # better typing??
    types: Dict[str, list]  # better typing??
    symtab = Dict[str, list]  # better typing??
    verbose_rec: bool
    verbose_str: bool

    def __init__(self, schema: dict, verbose_rec=False, verbose_str=False, config: dict = None):
        assert set(enctab) == set(CORE_TYPES)
        self.schema = simplify(schema)             # Convert extensions to core definitions
        conf = config if config else schema
        self.config = get_config(conf['info'] if 'info' in conf else None)
        self.format_validate = format_validators()      # Initialize format validation functions
        self.format_codec = json_format_codecs()        # Initialize format serialization functions
        self.types = {t[TypeName]: t for t in self.schema['types']}  # pre-index types to allow symtab forward refs
        self.symtab = None                      # Symbol table - pre-computed values for all datatypes
        self.set_mode(verbose_rec, verbose_str)  # Create symbol table based on encoding mode

    def _error(self, msg: str) -> NoReturn:
        raise_error(f'Validation Error: {msg}')

    def decode(self, datatype: str, sval: Any) -> Any:  # Decode serialized value into API value
        ts: list = []
        try:
            ts = self.symtab[datatype]
        except KeyError:
            self._error(f'Decode: datatype "{datatype}" is not defined')
        return ts[S_DECODE](ts, sval, self)     # Dispatch to type-specific decoder

    def encode(self, datatype: str, aval: Any) -> Any:  # Encode API value into serialized value
        ts: list = []
        try:
            ts = self.symtab[datatype]
        except KeyError:
            self._error(f'Encode: datatype "{datatype}" is not defined')
        return ts[S_ENCODE](ts, aval, self)     # Dispatch to type-specific encoder

    def set_mode(self, verbose_rec=False, verbose_str=False):
        # Build symbol table field entries
        def symf(fld: list, fa: int, fnames: dict) -> [list, dict, Optional[int]]:
            fo, to = ftopts_s2d(fld[FieldOptions])
            if to:
                self._error('%s: internal error: unexpected type options: %s' % (fld[FieldName], str(to)))
            fopts = {'minc': 1, 'maxc': 1}
            fopts.update(fo)
            assert fopts['minc'] in (0, 1) and fopts['maxc'] == 1     # Other cardinalities have been simplified
            ctag: Optional[int] = None
            if 'tagid' in fopts:
                ctag = fopts['tagid'] if fa == FieldID else fnames[fopts['tagid']]
            fs = [
                fld,        # SF_DEF: JADN field definition
                fopts,      # SF_OPT: Field options (dict)
                ctag        # SF_CTAG: tagid option
            ]
            return fs

        # Generate TypeRef pattern - concatenate NSID: and TypeName patterns
        def make_typeref_pattern(nsid: str, typename: str) -> dict:
            ns = nsid.lstrip('^').rstrip('$')
            tn = typename.lstrip('^').rstrip('$')
            return {'pattern': '^(' + ns + ':)?' + tn + '$'}

        # Set configurable option values
        def config_opts(opts: List[str]) -> dict:
            op = [(v[0] + self.config[v[1:]]) if len(v) > 1 and v[1] == '$' else v for v in opts]
            return topts_s2d(op)

        def sym(t: list) -> list:  # Build symbol table based on encoding modes
            symval = [
                t,                             # 0: S_TDEF:  JADN type definition
                enctab[t[BaseType]][C_ENC],    # 1: S_ENCODE: Encoder for this type
                enctab[t[BaseType]][C_DEC],    # 2: S_DECODE: Decoder for this type
                enctab[t[BaseType]][C_ETYPE],  # 3: S_ENCTYPE: Encoded value type
                config_opts(t[TypeOptions]),   # 4: S_TOPTS:  Type Options (dict)
                {},                            # 5: S_FVALIDATE: Format semantic validation - returns True if valid
                {},                            # 6: S_FENCODE: Format encode conversion - returns serialized data representation
                {},                            # 7: S_FDECODE: Format decode conversion - returns API value
                {},                            # 8: S_DMAP: Encoded field key or enum value to API
                {},                            # 9: S_EMAP: API field key or enum value to Encoded
                {},                            # 10: S_FLD: Symbol table field entry
            ]

            if t[BaseType] == 'Record':
                symval[S_ENCODE] = _encode_maprec   # if self.verbose_rec else _encode_array
                symval[S_DECODE] = _decode_maprec   # if self.verbose_rec else _decode_array
                symval[S_ENCTYPE] = dict if self.verbose_rec else list
            if t[BaseType] in ('Enumerated', 'Array', 'Choice', 'Map', 'Record'):
                fx = FieldName if 'id' not in symval[S_TOPTS] and t[BaseType] != 'Array' and verbose_str else FieldID
                fa = FieldName if 'id' not in symval[S_TOPTS] else FieldID
                try:
                    symval[S_DMAP] = {f[fx]: f[fa] for f in t[Fields]}
                    symval[S_EMAP] = {f[fa]: f[fx] for f in t[Fields]}
                    fnames = {f[FieldID]: f[FieldName] for f in t[Fields]}
                except IndexError:
                    print('symval index error')
                    raise
                if t[BaseType] != 'Enumerated':
                    symval[S_FLD] = {f[fx]: symf(f, fa, fnames) for f in t[Fields]}
            if t[BaseType] in ('Binary', 'String', 'Array', 'ArrayOf', 'Map', 'MapOf', 'Record'):
                opts = symval[S_TOPTS]
                minv = opts.get('minv', 0)
                maxv = opts.get('maxv', 0)
                if minv < 0 or maxv < 0:
                    self._error(f'{t[TypeName]}: length cannot be negative: {minv}..{maxv}')
                if maxv == 0:
                    maxv = self.config['$MaxElements']
                    if t[BaseType] in ('Binary', 'String'):
                        maxv = self.config[f'$Max{t[BaseType]}']
                opts.update({'minv': minv, 'maxv': maxv})
            fmt = symval[S_TOPTS].get('format', '')
            symval[S_FVALIDATE] = get_format_validate_function(self.format_validate, t[BaseType], fmt)
            symval[S_FENCODE] = get_format_encode_function(self.format_codec, t[BaseType], fmt)
            symval[S_FDECODE] = get_format_decode_function(self.format_codec, t[BaseType], fmt)
            return symval

        self.verbose_rec = verbose_rec
        self.verbose_str = verbose_str
        self.symtab = {t[TypeName]: sym(t) for t in self.schema['types']}
        if 'TypeRef' in self.types:
            self.symtab['TypeRef'][S_TOPTS] = make_typeref_pattern(self.config['$NSID'], self.config['$TypeName'])
        self.symtab.update(
            {t: [
                ['', t],
                enctab[t][C_ENC],
                enctab[t][C_DEC],
                enctab[t][C_ETYPE],
                {},
                get_format_validate_function(self.format_validate, t[BaseType], ''),
                get_format_encode_function(self.format_codec, t[BaseType], ''),
                get_format_decode_function(self.format_codec, t[BaseType], ''),
                {},
                {},
                {},
            ] for t in SIMPLE_TYPES})


def _bad_index(ts: list, k: int, val) -> NoReturn:
    td = ts[S_TDEF]
    raise_error(f'{td[TypeName]}({td[BaseType]}): array index {k} out of bounds ({len(ts[S_FLD])}, {len(val)})')


def _bad_choice(ts: List, val) -> NoReturn:
    td = ts[S_TDEF]
    raise_error(f'{td[TypeName]}: choice must have one value: {val}')


def _bad_value(ts: list, val, fld: list = None) -> NoReturn:
    td = ts[S_TDEF]
    if fld is not None:
        raise_error(f'{td[TypeName]}({td[BaseType]}: missing required field "{fld[FieldName]}": {val}')
    else:
        v = next(iter(val)) if type(val) == dict else val
        raise_error(f'{td[TypeName]}({td[BaseType]}: bad value: {v}')


def _check_type(ts: list, val, vtype, fail=False) -> NoReturn:  # fail forces rejection of boolean vals for number types
    if vtype is not None:
        if fail or not isinstance(val, vtype):
            td = ts[S_TDEF]
            tn = f"{td[TypeName]}({td[BaseType] if td else 'Primitive'})"
            raise_error(f'{tn}: {val} is not {vtype}')


def _format_encode(ts: list, val):
    try:
        ts[S_FVALIDATE](val)
    except ValueError:
        raise_error(f'{ts[S_TDEF][TypeName]}: {val} is not format "{ts[S_TOPTS]["format"]}"')
    return ts[S_FENCODE](val)


def _format_decode(ts: list, val):
    aval = ts[S_FDECODE](val)
    try:
        ts[S_FVALIDATE](aval)
    except ValueError:
        raise_error(f'{ts[S_TDEF][TypeName]}: {val} is not format "{ts[S_TOPTS]["format"]}"')
    return aval


def _check_key(ts: list, val):
    try:
        return int(val) if isinstance(next(iter(ts[S_DMAP])), int) else val
    except ValueError:
        raise_error(f'{ts[S_TDEF][TypeName]}: {val} is not a valid field ID')


def _check_pattern(ts: list, val):
    op = ts[S_TOPTS]
    if 'pattern' in op and not re.match(op['pattern'], val):
        tn = ts[S_TDEF][TypeName]
        raise_error(f'{tn}: string "{val}" does not match {op["pattern"]}')
    return val


def _check_range(ts: list, val):
    op = ts[S_TOPTS]
    tn = ts[S_TDEF][TypeName]
    if 'minv' in op and val < op['minv']:
        raise_error(f'{tn}: {val} < minimum {op["minv"]}')
    if 'maxv' in op and val > op['maxv']:
        raise_error(f'{tn}: {val} < maximum {op["maxv"]}')
    return val


def _check_frange(ts: list, val):
    op = ts[S_TOPTS]
    tn = ts[S_TDEF][TypeName]
    if 'minf' in op and val < op['minf']:
        raise_error(f'{tn}: {val} < minimum {op["minf"]}')
    if 'maxf' in op and val > op['maxf']:
        raise_error(f'{tn}: {val} < maximum {op["maxf"]}')
    return val


def _check_size(ts: list, val):
    op = ts[S_TOPTS]
    tn = ts[S_TDEF][TypeName]
    if 'minv' in op and len(val) < op['minv']:
        raise_error(f'{tn}: length {len(val)} < minimum {op["minv"]}')
    if 'maxv' in op and len(val) > op['maxv']:
        raise_error(f'{tn}: length {len(val)} > maximum {op["maxv"]}')
    return val


def _extra_value(ts: list, val, fld):
    td = ts[S_TDEF]
    raise_error(f'{td[TypeName]}({td[BaseType]}): unexpected field: {val} not in {fld}:')


def _encode_binary(ts: list, aval, codec):    # Encode bytes to string
    _check_type(ts, aval, bytes)
    _check_size(ts, aval)
    return _format_encode(ts, aval)


def _decode_binary(ts: list, sval, codec):    # Decode ASCII string to bytes
    aval = _format_decode(ts, sval)
    _check_type(ts, aval, bytes)        # assert format decode returns correct type
    return _check_size(ts, aval)


def _encode_boolean(ts: list, val, codec):
    _check_type(ts, val, bool)
    return val


def _decode_boolean(ts: list, val, codec):
    _check_type(ts, val, bool)
    return val


def _encode_integer(ts: list, aval, codec):
    _check_type(ts, aval, numbers.Integral, isinstance(aval, bool))
    _check_range(ts, aval)
    return _format_encode(ts, aval)


def _decode_integer(ts: list, sval, codec):
    aval = _format_decode(ts, sval)
    _check_type(ts, aval, numbers.Integral, isinstance(aval, bool))
    return _check_range(ts, aval)


def _encode_number(ts: list, aval, codec):
    _check_type(ts, aval, numbers.Real, isinstance(aval, bool))
    _check_frange(ts, aval)
    return _format_encode(ts, aval)


def _decode_number(ts: list, sval, codec):
    aval = _format_decode(ts, sval)
    _check_type(ts, aval, numbers.Real, isinstance(aval, bool))
    return _check_range(ts, aval)


def _encode_null(ts: list, aval, codec):
    if aval:                            # Treat any false-y value as Null: None, False, 0, '', [], set(), {}
        _bad_value(ts, aval)
    return aval


def _decode_null(ts: list, val, codec):
    if val:
        _bad_value(ts, val)
    return val


def _encode_string(ts: list, aval, codec):
    _check_type(ts, aval, type(''))
    _check_size(ts, aval)
    _check_pattern(ts, aval)
    return _format_encode(ts, aval)


def _decode_string(ts: list, sval, codec):
    aval = _format_decode(ts, sval)
    _check_type(ts, aval, type(''))
    _check_size(ts, aval)
    return _check_pattern(ts, aval)


def _encode_enumerated(ts: list, aval, codec):                # TODO: Serialization
    _check_type(ts, aval, type(next(iter(ts[S_EMAP]))))
    if aval in ts[S_EMAP]:
        return ts[S_EMAP][aval]
    else:
        td = ts[S_TDEF]
        raise_error('%s: %r is not a valid %s' % (td[BaseType], aval, td[TypeName]))


def _decode_enumerated(ts: list, sval, codec):
    _check_type(ts, sval, type(next(iter(ts[S_DMAP]))))
    if sval in ts[S_DMAP]:
        return ts[S_DMAP][sval]
    else:
        td = ts[S_TDEF]
        raise_error('%s: %r is not a valid %s' % (td[BaseType], sval, td[TypeName]))


def _encode_choice(ts: list, val, codec):
    _check_type(ts, val, dict)
    if len(val) != 1:
        _bad_choice(ts, val)
    k, v = next(iter(val.items()))
    if k not in ts[S_EMAP]:
        _bad_value(ts, val)
    k = ts[S_EMAP][k]
    f = ts[S_FLD][k][SF_DEF]
    return {k: codec.encode(f[FieldType], v)}


def _decode_choice(ts: list, val, codec):  # Map Choice:  val == {key: value}
    _check_type(ts, val, dict)
    if len(val) != 1:
        _bad_choice(ts, val)
    k, v = next(iter(val.items()))
    k = _check_key(ts, k)
    if k not in ts[S_DMAP]:
        _bad_value(ts, val)
    f = ts[S_FLD][k][SF_DEF]
    k = ts[S_DMAP][k]
    return {k: codec.decode(f[FieldType], v)}


def _encode_maprec(ts: list, aval, codec):
    _check_type(ts, aval, dict)
    sval = ts[S_ENCTYPE]()
    assert type(sval) in (list, dict)
    fx = FieldName if codec.verbose_str else FieldID  # Verbose or minified identifier strings
    fnames = [f[SF_DEF][FieldName] for f in ts[S_FLD].values()]
    for f in ts[S_TDEF][Fields]:
        fs = ts[S_FLD][f[fx]]  # Symtab entry for field
        fd = fs[SF_DEF]  # JADN field definition from symtab
        fname = fd[FieldName]  # Field name
        fopts = fs[SF_OPT]  # Field options dict
        ctag = fs[SF_CTAG]
        if ctag is not None:  # Type of this field is specified by contents of another field
            e = codec.encode(fd[FieldType], {aval[ctag]: aval[fname]})
            sv = next(iter(e.values()))
        else:
            sv = codec.encode(fd[FieldType], aval[fname]) if fname in aval else None
        if sv is None and ('minc' not in fopts or fopts['minc'] > 0):  # Missing required field
            _bad_value(ts, aval, fd)
        if type(sval) == list:  # Concise Record
            sval.append(sv)
        elif sv is not None:  # Map or Verbose Record
            sval[fd[fx]] = sv

    if set(aval) - set(fnames):
        _extra_value(ts, aval, fnames)
    if type(sval) == list:
        while sval and sval[-1] is None:  # Strip non-populated trailing optional values
            sval.pop()
    return sval


def _decode_maprec(ts: list, sval, codec):
    _check_type(ts, sval, ts[S_ENCTYPE])
    val = sval
    if ts[S_ENCTYPE] == dict:
        val = {_check_key(ts, k): v for k, v in sval.items()}
    aval = dict()
    fx = FieldName if codec.verbose_str else FieldID  # Verbose or minified identifier strings
    fnames = [k for k in ts[S_FLD]]
    for f in ts[S_TDEF][Fields]:
        fs = ts[S_FLD][f[fx]]  # Symtab entry for field
        fd = fs[SF_DEF]  # JADN field definition from symtab
        fopts = fs[SF_OPT]  # Field options dict
        if type(val) == dict:
            fn = f[fx]
            sv = val[fn] if fn in val else None
        else:
            fn = fd[FieldID] - 1
            sv = val[fn] if len(val) > fn else None
        if sv is not None:
            ctag = fs[SF_CTAG]
            if ctag is not None:  # Type of this field is specified by contents of another field
                ct = ctag if type(val) == dict else ts[S_EMAP][ctag] - 1
                av = codec.decode(fd[FieldType], {sval[ct]: sv})
                aval[fd[FieldName]] = next(iter(av.values()))
            else:
                aval[fd[FieldName]] = codec.decode(fd[FieldType], sv)
        else:
            if 'minc' not in fopts or fopts['minc'] > 0:
                _bad_value(ts, val, fd)
    extra = set(val) - set(fnames) if type(val) == dict else len(val) > len(ts[S_FLD])
    if extra:
        _extra_value(ts, val, extra)
    return aval


def _encode_array(ts: list, aval, codec):
    _check_type(ts, aval, list)
    sval = list()
    extra = len(aval) > len(ts[S_FLD])
    if extra:
        _extra_value(ts, aval, extra)
    for fn in ts[S_TDEF][Fields]:
        f = ts[S_FLD][fn[FieldID]][SF_DEF]  # Use symtab field definition
        fx = f[FieldID] - 1
        fopts = ts[S_FLD][fx + 1][SF_OPT]
        av = aval[fx] if len(aval) > fx else None
        if av is not None:
            if 'tagid' in fopts:
                choice_type = aval[int(fopts['tagid']) - 1]
                e = codec.encode(f[FieldType], {choice_type: av})
                sv = e[next(iter(e))]
            else:
                sv = codec.encode(f[FieldType], av)
            sval.append(sv)
        else:
            sval.append(None)
            if 'minc' in fopts and fopts['minc'] > 0:   # Value is required
                _bad_value(ts, aval, f)
    while sval and sval[-1] is None:            # Strip non-populated trailing optional values
        sval.pop()
    return _format_encode(ts, sval)


def _decode_array(ts: list, sval, codec):  # Ordered list of types, returned as a list
    val = _format_decode(ts, sval)
    _check_type(ts, val, list)
    aval = list()
    extra = len(val) > len(ts[S_FLD])
    if extra:
        _extra_value(ts, val, extra)  # TODO: write sensible display of excess values
    for fn in ts[S_TDEF][Fields]:
        f = ts[S_FLD][fn[FieldID]][SF_DEF]  # Use symtab field definition
        fx = f[FieldID] - 1
        fopts = ts[S_FLD][fx + 1][SF_OPT]
        sv = val[fx] if len(val) > fx else None
        if sv is not None:
            if 'tagid' in fopts:
                choice_type = val[int(fopts['tagid']) - 1]
                d = codec.decode(f[FieldType], {choice_type: sv})  # TODO: fix str/int handling of choice
                av = d[next(iter(d))]
            else:
                av = codec.decode(f[FieldType], sv)
            aval.append(av)
        else:
            aval.append(None)
            if 'minc' not in fopts or fopts['minc'] > 0:
                _bad_value(ts, val, f)
    while aval and aval[-1] is None:  # Strip non-populated trailing optional values
        aval.pop()
    return aval


def _encode_array_of(ts: list, val, codec):
    _check_type(ts, val, list)
    _check_size(ts, val)
    return [codec.encode(ts[S_TOPTS]['vtype'], v) for v in val]


def _decode_array_of(ts: list, val, codec):
    _check_type(ts, val, list)
    _check_size(ts, val)
    return [codec.decode(ts[S_TOPTS]['vtype'], v) for v in val]


def _encode_map_of(ts: list, aval, codec):
    _check_type(ts, aval, dict)
    _check_size(ts, aval)
    to = ts[S_TOPTS]
    return {codec.encode(to['ktype'], k): codec.encode(to['vtype'], v) for k, v in aval.items()}


def _decode_map_of(ts: list, sval, codec):
    _check_type(ts, sval, dict)
    _check_size(ts, sval)
    return {k: codec.decode(ts[S_TOPTS]['vtype'], v) for k, v in sval.items()}


enctab = {  # decode, encode, min encoded type
    'Binary': (_decode_binary, _encode_binary, str),
    'Boolean': (_decode_boolean, _encode_boolean, bool),
    'Integer': (_decode_integer, _encode_integer, int),
    'Number': (_decode_number, _encode_number, float),
    'Null': (_decode_null, _encode_null, str),
    'String': (_decode_string, _encode_string, str),
    'Enumerated': (_decode_enumerated, _encode_enumerated, int),
    'Choice': (_decode_choice, _encode_choice, dict),
    'Array': (_decode_array, _encode_array, list),
    'ArrayOf': (_decode_array_of, _encode_array_of, list),
    'Map': (_decode_maprec, _encode_maprec, dict),
    'MapOf': (_decode_map_of, _encode_map_of, dict),
    'Record': (None, None, None),  # Dynamic values
}
