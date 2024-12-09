"""
 JADN Definitions

A JSON Abstract Data Notation (JADN) file contains a list of datatype definitions.  Each type definition
has a specified format - a list of four or five columns depending on whether the type is primitive or
structure: (name, base type, type options, type description [, fields]).

For the enumerated type each field definition is a list of three items: (tag, name, description).

For other structure types (array, choice, map, record) each field definition is a list of five items:
(tag, name, type, field options, field description).
"""
from copy import deepcopy
from dataclasses import Field, dataclass, field
from inspect import isfunction
from typing import List, Optional, Tuple, Union


class BasicDataclass:
    __annotations__: dict
    __default__: dict
    __keyindex__: Tuple[str, ...]

    def __init_subclass__(cls, **kwargs):
        cls.__keyindex__ = tuple(cls.__annotations__)
        cls.__default__ = {}
        for k in cls.__keyindex__:
            v = getattr(cls, k, None)
            if isinstance(v, Field):
                if isfunction(v.default):
                    cls.__default__[k] = v.default()
                elif isfunction(v.default_factory):
                    cls.__default__[k] = v.default_factory()
                else:
                    cls.__default__[k] = None
            else:
                cls.__default__[k] = v if isinstance(v, (int, float, str)) else deepcopy(v)

    def __getitem__(self, key: Union[int, slice, str]):
        if isinstance(key, slice):
            return [self[k] for k in self.__keyindex__[key]]
        if isinstance(key, int):
            key = list(self.__keyindex__)[key]
        return object.__getattribute__(self, key)

    def __setitem__(self, key: Union[int, str], val: any):
        if isinstance(key, int):
            key = list(self.__keyindex__)[key]
        return object.__setattr__(self, key, val)

    def __delitem__(self, key: Union[int, str]):
        if isinstance(key, int):
            key = list(self.__keyindex__)[key]
        object.__setattr__(self, self.__default__[key], self.__default__[key])

    def __len__(self):
        return len(self.__keyindex__)


# Datatype Definition columns
TypeName = 0            # Name of the type being defined
CoreType = 1            # Core type of the type being defined
TypeOptions = 2         # An array of zero or more TYPE_OPTIONS
TypeDesc = 3            # A non-normative description of the type
Fields = 4              # List of one or more items or fields

# Enumerated Item Definition columns
ItemID = 0              # Integer item identifier
ItemValue = 1           # String value of the item
ItemDesc = 2            # A non-normative description of the Enumerated item

# Field Definition columns
FieldID = 0             # Integer field identifier
FieldName = 1           # Name or label of the field
FieldType = 2           # Type of the field
FieldOptions = 3        # An array of zero or more FIELD_OPTIONS (and TYPE_OPTIONS if extended)
FieldDesc = 4           # A non-normative description of the field


# Dataclass Helpers
@dataclass
class EnumFieldDefinition(BasicDataclass):
    ItemID: int = 0
    ItemValue: str = ''
    ItemDesc: str = ''


@dataclass
class GenFieldDefinition(BasicDataclass):
    FieldID: int = 0
    FieldName: str = 'FieldName'
    FieldType: str = 'FieldType'
    FieldOptions: List[str] = field(default_factory=lambda: [])
    FieldDesc: str = ''


@dataclass
class TypeDefinition(BasicDataclass):
    TypeName: str = 'DefinitionName'
    CoreType: str = 'DefinitionType'
    TypeOptions: List[str] = field(default_factory=lambda: [])
    TypeDesc: str = ''
    Fields: Optional[Union[List[GenFieldDefinition], List[EnumFieldDefinition]]] = field(default_factory=lambda: [])


# Core datatypes
PRIMITIVE_TYPES = (
    'Binary',
    'Boolean',
    'Integer',
    'Number',
    'String',
)

COMPOUND_TYPES = (
    'Array',
    'ArrayOf',          # (value_type): instance is a container but definition has no fields
    'Map',
    'MapOf',            # (key_type, value_type): instance is a container but definition has no fields
    'Record',
)

UNION_TYPES = (
    'Enumerated',       # enum option specifies fields derived from a defined type
    'Choice',
)

CORE_TYPES = PRIMITIVE_TYPES + COMPOUND_TYPES + UNION_TYPES

FIELD_LENGTH = {
    'Binary': 0,
    'Boolean': 0,
    'Integer': 0,
    'Number': 0,
    'String': 0,
    'Enumerated': 3,    # 0 if Enumerated type definition contains enum or pointer option
    'Choice': 5,
    'Array': 5,
    'ArrayOf': 0,
    'Map': 5,
    'MapOf': 0,
    'Record': 5,
}


def is_builtin(t: str) -> bool:      # Is a core type
    return t in CORE_TYPES


def has_fields(t: str) -> bool:      # Is a type with fields listed in definition
    return FIELD_LENGTH[t] == 5 if is_builtin(t) else False


# Option Tags/Keys
#   JADN TypeOptions and FieldOptions contain a list of strings, each of which is an option.
#   The first character of an option string is the type ID; the remaining characters are the value.
#   The option string is converted into a Name: Value pair before use.
#   The tables list the unicode codepoint of the ID and the corresponding Name and value type.

TYPE_OPTIONS = {        # Option ID: (name, value type, canonical order) # ASCII ID
    0x3d: ('id', lambda x: True, 1),          # '=', Enumerated type and Choice/Map/Record keys are ID not Name
    0x2a: ('vtype', lambda x: x, 2),          # '*', Value type for ArrayOf and MapOf
    0x2b: ('ktype', lambda x: x, 3),          # '+', Key type for MapOf
    0x23: ('enum', lambda x: x, 4),           # '#', enumeration derived from Array/Choice/Map/Record type
    0x3e: ('pointer', lambda x: x, 5),        # '>', enumeration of pointers derived from Array/Choice/Map/Record type
    0x2f: ('format', lambda x: x, 6),         # '/', semantic validation keyword, may affect serialization
    0x25: ('pattern', lambda x: x, 7),        # '%', regular expression that a string must match
    0x77: ('minExclusive', None, 8),          # 'w', minimum numeric/string value, excluding bound
    0x78: ('maxExclusive', None, 9),          # 'x', maximum numeric/string value, excluding bound
    0x79: ('minInclusive', None, 10),         # 'y', minimum numeric/string value
    0x7a: ('maxInclusive', None, 11),         # 'z', maximum numeric/string value
    0x7b: ('minLength', int, 12),             # '{', minimum byte or text string length, collection item count
    0x7d: ('maxLength', int, 13),             # '}', maximum byte or text string length, collection item count
    0x71: ('unique', lambda x: True, 14),     # 'q', ArrayOf instance must not contain duplicates
    0x73: ('set', lambda x: True, 15),        # 's', ArrayOf instance is unordered and unique (set)
    0x62: ('unordered', lambda x: True, 16),  # 'b', ArrayOf instance is unordered and not unique (bag)
    0x6f: ('sequence', lambda x: True, 17),   # 'o', Map, MapOr or Record instance is ordered and unique (ordered set)
    0x43: ('combine', lambda x: x, 18),       # 'C', Choice instance is a logical combination (anyOf, allOf, oneOf)
    0x61: ('abstract', lambda x: True, 19),   # 'a', Inheritance: abstract, non-instantiatable
    0x72: ('restricts', lambda x: x, 20),     # 'r', Inheritance: restriction - subset of referenced type
    0x65: ('extends', lambda x: x, 21),    # 'e', Inheritance: extension - superset of referenced type
    0x66: ('final', lambda x: True, 22),      # 'f', Inheritance: final - cannot have subtype
    0x21: ('default', lambda x: x, 23),       # '!', Default value
}

FIELD_OPTIONS = {
    0x5b: ('minOccurs', int, 24),             # '[', min cardinality, default = 1, 0 = field is optional
    0x5d: ('maxOccurs', int, 25),             # ']', max cardinality, default = 1, <0 = inherited or none, not 1 = array
    0x26: ('tagid', int, 26),                 # '&', field that specifies the type of this field
    0x3c: ('dir', lambda x: True, 27),        # '<', pointer enumeration treats field as a collection
    0x4b: ('key', lambda x: True, 28),        # 'K', field is a primary key for this type
    0x4c: ('link', lambda x: True, 29),       # 'L', field is a link (foreign key) to an instance of FieldType
}

OPTION_ID = {   # Pre-computed reverse index - MUST match TYPE_OPTIONS and FIELD_OPTIONS
    'id':       chr(61),
    'vtype':    chr(42),
    'ktype':    chr(43),
    'enum':     chr(35),
    'pointer':  chr(62),
    'format':   chr(47),
    'pattern':  chr(37),
    'minExclusive': chr(119),
    'maxExclusive': chr(120),
    'minInclusive': chr(121),
    'maxInclusive': chr(122),
    'minLength':    chr(123),
    'maxLength':    chr(125),
    'unique':   chr(113),
    'set':      chr(115),
    'unordered': chr(98),
    'sequence': chr(111),
    'combine':  chr(67),
    'abstract': chr(97),
    'restricts': chr(114),
    'extends':  chr(101),
    'final': chr(102),
    'default':  chr(33),
    'minOccurs':    chr(91),
    'maxOccurs':    chr(93),
    'tagid':    chr(38),
    'dir':      chr(60),
    'key':      chr(75),
    'link':     chr(76),
}

MAX_DEFAULT = -1            # maxOccurs sentinel value: Upper size limit defaults to JADN or package limit
MAX_UNLIMITED = -2          # maxOccurs sentinel value: Upper size limit does not exist

REQUIRED_TYPE_OPTIONS = {
    'Binary': [],
    'Boolean': [],
    'Integer': [],
    'Number': [],
    'String': [],
    'Enumerated': [],
    'Choice': [],
    'Array': [],
    'ArrayOf': ['vtype'],
    'Map': [],
    'MapOf': ['ktype', 'vtype'],
    'Record': [],
}

ALLOWED_TYPE_OPTIONS_ALL = ['default', 'abstract', 'extends', 'restricts', 'final']

ALLOWED_TYPE_OPTIONS = {
    'Binary': ['format', 'minLength', 'maxLength'],
    'Boolean': [],
    'Integer': ['format', 'minInclusive', 'maxInclusive', 'minExclusive', 'maxExclusive'],
    'Number': ['format', 'minInclusive', 'maxInclusive', 'minExclusive', 'maxExclusive'],
    'String': ['format', 'pattern', 'minLength', 'maxLength'],
    'Enumerated': ['id', 'enum', 'pointer'],
    'Choice': ['id', 'combine'],
    'Array': ['format', 'minLength', 'maxLength'],
    'ArrayOf': ['vtype', 'minLength', 'maxLength', 'unique', 'set', 'unordered'],
    'Map': ['id', 'minLength', 'maxLength', 'sequence'],
    'MapOf': ['ktype', 'vtype', 'minLength', 'maxLength', 'sequence'],
    'Record': ['minLength', 'maxLength', 'sequence'],
}

# Ensure jsonschema prerequisite packages are installed, e.g., rfc3987 for uri/iri validation
FORMAT_JS_VALIDATE = {      # Semantic validation formats defined by JSON Schema 2019-09 Sec 7.3
    'date-time': 'String',
    'date': 'String',
    'time': 'String',
    'duration': 'String',
    # 'email': 'String',        # jsonschema package has deliberately buggy email - won't be fixed
    'idn-email': 'String',
    # 'hostname': 'String',     # jsonschema package needs bug fix
    'idn-hostname': 'String',
    'ipv4': 'String',           # doesn't allow netmask prefix length
    'ipv6': 'String',           # doesn't allow netmask prefix length
    'uri': 'String',
    'uri-reference': 'String',
    'iri': 'String',
    'iri-reference': 'String',
    # 'uuid': 'String',
    'uri-template': 'String',
    'json-pointer': 'String',
    'relative-json-pointer': 'String',
    'regex': 'String'
}

FORMAT_VALIDATE = {         # Semantic validation formats defined by JADN
    'email': 'String',          # Use this instead of jsonschema
    'hostname': 'String',       # Use this instead of jsonschema
    'eui': 'Binary',            # IEEE Extended Unique Identifier, 48 bits or 64 bits
    'uuid': 'Binary',           # Use this instead of jsonschema
    'tag-uuid': 'Array',        # Prefixed UUID, e.g., "action-b254a45e-d0d3-4e17-b65a-3002f86ee836"
    'ipv4-addr': 'Binary',      # IPv4 address as specified in RFC 791 Section 3.1
    'ipv6-addr': 'Binary',      # IPv6 address as specified in RFC 8200 Section 3
    'ipv4-net': 'Array',        # Binary IPv4 address and Integer prefix length, RFC 4632 Section 3.1
    'ipv6-net': 'Array',        # Binary IPv6 address and Integer prefix length, RFC 4291 Section 2.3
    'i8': 'Integer',            # Signed 8 bit integer [-128 .. 127]
    'i16': 'Integer',           # Signed 16 bit integer [-32768 .. 32767]
    'i32': 'Integer',           # Signed 32 bit integer [-2147483648 .. 2147483647]
    'i64': 'Integer',           # Signed 64 bit integer [-2^63 .. 2^63 -1]
    # 'u#': 'Integer',            # Unsigned '#'-bit integer or bit field where #>0, [0 .. 2^# -1]
}

FORMAT_SERIALIZE = {        # Data representation formats for one or more serializations
    'eui': 'Binary',            # IEEE EUI, 'hex-byte-colon' text representation, (e.g., 00:1B:44:11:3A:B7)
    'uuid': 'Binary',           # RFC 4122 UUID with text, (e.g., e81415a7-4c8d-45cd-a658-6b51b7a8f45d)
    'tag-uuid': 'Array',        # UUID with prefixed tag, (e.g., action-e81415a7-4c8d-45cd-a658-6b51b7a8f45d)
    'ipv4-addr': 'Binary',      # IPv4 'dotted-quad' text representation, RFC 2673 Section 3.2
    'ipv6-addr': 'Binary',      # IPv6 text representation, RFC 4291 Section 2.2
    'ipv4-net': 'Array',        # IPv4 Network Address CIDR text string, RFC 4632 Section 3.1
    'ipv6-net': 'Array',        # IPv6 Network Address CIDR text string, RFC 4291 Section 2.3
    'b': 'Binary',              # Base64url - RFC 4648 Section 5 (default text representation of Binary type)
    'x': 'Binary',              # Hex - base16 - lowercase out, case-folding in
    'X': 'Binary',              # Hex - RFC 4648 Section 8 - uppercase only
    'datetime-ms': 'Integer',   # Milliseconds from the epoch, RFC 3339 date-time text representation
    'i8': 'Integer',            # 8 bit field - these affect packed (RFC 791 style) serializations
    'i16': 'Integer',           # 16 bit field
    'i32': 'Integer',           # 32 bit field
    'i64': 'Integer',           # 64 bit field
    # 'u#': 'Integer',            # #-bit field
    'f16': 'Number',            # IEEE 754 Half-Precision Float - these affect CBOR serialization
    'f32': 'Number',            # IEEE 754 Single-Precision Float
    'f64': 'Number',            # IEEE 754 Double-Precision Float (default binary representation of Number type)
}

VALID_FORMATS = {**FORMAT_JS_VALIDATE, **FORMAT_VALIDATE, **FORMAT_SERIALIZE}

DEFAULT_CONFIG = {          # Configuration values to use if not specified in schema
    '$MaxBinary': 255,          # Maximum number of octets for Binary types
    '$MaxString': 255,          # Maximum number of characters for String types
    '$MaxElements': 255,        # Maximum number of items/properties for container types
    '$Sys': '.',                # System reserved character for TypeName
    '$TypeName': '^[A-Z][-.A-Za-z0-9]{0,63}$',     # Type Name regex
    '$FieldName': '^[a-z][_A-Za-z0-9]{0,63}$',     # Field Name regex
    '$NSID': '^([A-Za-z][A-Za-z0-9]{0,7})?$',      # Namespace ID regex
    '$TypeRef': '^$'            # Placeholder.  Actual pattern is ($NSID ':')? $TypeName
}

EXTENSIONS = {
    'AnonymousType',            # TYPE_OPTIONS included in FieldOptions
    'Multiplicity',             # maxOccurs other than 1, or minLength other than 0 (optional) or 1 (required)
    'DerivedEnum',              # enum and pointer/dir options, create Enumerated type of fields or JSON Pointers
    'MapOfEnum',                # ktype option specifies an Enumerated type
    'Link',                     # key and link options
}

META_ORDER = ('title', 'package', 'version', 'description', 'comments',
              'copyright', 'license', 'namespaces', 'roots', 'config')    # Display order

GRAPH_DETAIL = ('conceptual', 'logical', 'information')

# Type Hinting
OPTION_TYPES = Union[int, float, str]
