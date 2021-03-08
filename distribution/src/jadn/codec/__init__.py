"""
Abstract Object Encoder/Decoder

Object schema is specified in JSON Abstract Data Notation (JADN) format.

Codec currently supports three JSON concrete message formats (verbose,
concise, and minified) but can be extended to support XML or binary formats.

Copyright 2016, 2021 David Kemp
Licensed under the Apache License, Version 2.0
http://www.apache.org/licenses/LICENSE-2.0
"""
from typing import Any, Callable, Dict, List, Optional
from .codec import SymbolTableField, SymbolTableFieldDefinition, enctab, _decode_maprec, _encode_maprec
from .format_serialize_json import json_format_codecs, get_format_encode_function, get_format_decode_function
from .format_validate import format_validators, get_format_validate_function
from ..utils import ftopts_s2d, get_config, object_types, raise_error, topts_s2d
from ..definitions import (
    # Field Indexes
    BaseType, FieldID, FieldName,
    # Const values
    PRIMITIVE_TYPES, CORE_TYPES,
    # Dataclass
    TypeDefinition, GenFieldDefinition
)
from ..transform import simplify


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
    format_validators: Dict[str, Dict[str, Callable[[Any], Any]]]
    format_codec: dict  # better typing??
    types: Dict[str, TypeDefinition]
    symtab = Dict[str, SymbolTableField]
    verbose_rec: bool
    verbose_str: bool

    def __init__(self, schema: dict, verbose_rec=False, verbose_str=False, config: dict = None):
        assert set(enctab) == set(CORE_TYPES)
        self.schema = simplify(schema)             # Convert extensions to core definitions
        conf = config if config else schema
        self.config = get_config(conf['info'] if 'info' in conf else None)
        self.format_validate = format_validators()      # Initialize format validation functions
        self.format_codec = json_format_codecs()        # Initialize format serialization functions
        # pre-index types to allow symtab forward refs
        self.types = {t.TypeName: t for t in object_types(self.schema['types'])}
        self.symtab = {}                         # Symbol table - pre-computed values for all datatypes
        self.set_mode(verbose_rec, verbose_str)  # Create symbol table based on encoding mode

    def decode(self, datatype: str, sval: Any) -> Any:  # Decode serialized value into API value
        try:
            ts = self.symtab[datatype]
        except KeyError:
            raise_error(f'Validation Error: Decode: datatype "{datatype}" is not defined')
        return ts.Decode(ts, sval, self)     # Dispatch to type-specific decoder

    def encode(self, datatype: str, aval: Any) -> Any:  # Encode API value into serialized value
        try:
            ts = self.symtab[datatype]
        except KeyError:
            raise_error(f'Validation Error: Encode: datatype "{datatype}" is not defined')
        return ts.Encode(ts, aval, self)     # Dispatch to type-specific encoder

    def set_mode(self, verbose_rec=False, verbose_str=False):
        # Build symbol table field entries
        def symf(fld: GenFieldDefinition, fa: int, fnames: dict) -> SymbolTableFieldDefinition:
            fo, to = ftopts_s2d(fld.FieldOptions)
            if to:
                raise_error(f'Validation Error: {fld.FieldName}: internal error: unexpected type options: {to}')
            fopts = {'minc': 1, 'maxc': 1, **fo}
            assert fopts['minc'] in (0, 1) and fopts['maxc'] == 1     # Other cardinalities have been simplified
            ctag: Optional[int] = None
            if 'tagid' in fopts:
                ctag = fopts['tagid'] if fa == FieldID else fnames[fopts['tagid']]
            return SymbolTableFieldDefinition(
                fld,        # SF_DEF: JADN field definition
                fopts,      # SF_OPT: Field options (dict)
                ctag        # SF_CTAG: tagid option
            )

        # Generate TypeRef pattern - concatenate NSID: and TypeName patterns
        def make_typeref_pattern(nsid: str, typename: str) -> dict:
            ns = nsid.lstrip('^').rstrip('$')
            tn = typename.lstrip('^').rstrip('$')
            return {'pattern': fr'^({ns}:)?{tn}$'}

        # Set configurable option values
        def config_opts(opts: List[str]) -> dict:
            op = [(v[0] + self.config[v[1:]]) if len(v) > 1 and v[1] == '$' else v for v in opts]
            return topts_s2d(op)

        def sym(t: TypeDefinition) -> SymbolTableField:  # Build symbol table based on encoding modes
            symval = SymbolTableField(
                t,                             # 0: S_TDEF:  JADN type definition
                enctab[t.BaseType].Enc,        # 1: S_ENCODE: Encoder for this type
                enctab[t.BaseType].Dec,        # 2: S_DECODE: Decoder for this type
                enctab[t.BaseType].eType,      # 3: S_ENCTYPE: Encoded value type
                config_opts(t.TypeOptions),    # 4: S_TOPTS:  Type Options (dict)
            )

            if t.BaseType == 'Record':
                symval.Encode = _encode_maprec   # if self.verbose_rec else _encode_array
                symval.Decode = _decode_maprec   # if self.verbose_rec else _decode_array
                symval.EncType = dict if self.verbose_rec else list
            if t.BaseType in ('Enumerated', 'Array', 'Choice', 'Map', 'Record'):
                fx = FieldName if 'id' not in symval.TypeOpts and t.BaseType != 'Array' and verbose_str else FieldID
                fa = FieldName if 'id' not in symval.TypeOpts else FieldID
                try:
                    symval.dMap = {f[fx]: f[fa] for f in t.Fields}
                    symval.eMap = {f[fa]: f[fx] for f in t.Fields}
                    fnames = {f[FieldID]: f[FieldName] for f in t.Fields}
                except IndexError as e:
                    raise IndexError(f'symval index error: {e}')
                if t.BaseType != 'Enumerated':
                    symval.Fld = {f[fx]: symf(f, fa, fnames) for f in t.Fields}
            if t.BaseType in ('Binary', 'String', 'Array', 'ArrayOf', 'Map', 'MapOf', 'Record'):
                minv = symval.TypeOpts.get('minv', 0)
                maxv = symval.TypeOpts.get('maxv', 0)
                if minv < 0 or maxv < 0:
                    raise_error(f'Validation Error: {t.TypeName}: length cannot be negative: {minv}..{maxv}')
                if maxv == 0:
                    maxv = self.config['$MaxElements']
                    if t.BaseType in ('Binary', 'String'):
                        maxv = self.config[f'$Max{t.BaseType}']
                symval.TypeOpts.update({'minv': minv, 'maxv': maxv})
            fmt = symval.TypeOpts.get('format', '')
            symval.FormatValidate = get_format_validate_function(self.format_validate, t.BaseType, fmt)
            symval.FormatEncode = get_format_encode_function(self.format_codec, t.BaseType, fmt)
            symval.FormatDecode = get_format_decode_function(self.format_codec, t.BaseType, fmt)
            return symval

        self.verbose_rec = verbose_rec
        self.verbose_str = verbose_str
        self.symtab = {t.TypeName: sym(t) for t in object_types(self.schema['types'])}
        if 'TypeRef' in self.types:
            self.symtab['TypeRef'].TypeOpts = make_typeref_pattern(self.config['$NSID'], self.config['$TypeName'])
        for t in PRIMITIVE_TYPES:
            self.symtab[t] = SymbolTableField(
                TypeDef=TypeDefinition('', t),
                Encode=enctab[t].Enc,
                Decode=enctab[t].Dec,
                EncType=enctab[t].eType,
                TypeOpts={},
                # TODO: check if t[BaseType] should just be t
                FormatValidate=get_format_validate_function(self.format_validate, t[BaseType], ''),
                FormatEncode=get_format_encode_function(self.format_codec, t[BaseType], ''),
                FormatDecode=get_format_decode_function(self.format_codec, t[BaseType], '')
            )


__all__ = ['Codec']
