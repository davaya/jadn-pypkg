import re
import jsonschema

from copy import deepcopy
from typing import Any, Dict, Callable
from ..definitions import FORMAT_JS_VALIDATE, FORMAT_VALIDATE, FORMAT_SERIALIZE

ValidationFunction = Callable[[Any], Any]
FormatTable = Dict[str, Dict[str, ValidationFunction]]


def _format_ok(val: Any) -> bool:
    return True


# Return validation functions for the specified format keyword and data type
def get_format_validate_function(format_table: FormatTable, base_type: str, format_kw: str) -> ValidationFunction:
    if not format_kw:
        return _format_ok
    try:
        return format_table[base_type][format_kw]
    except KeyError:
        if format_kw in FORMAT_SERIALIZE:
            return _format_ok           # no value constraints on this keyword
        raise


# Regex from https://stackoverflow.com/questions/201323/how-to-validate-an-email-address-using-a-regular-expression
#   A more comprehensive email address validator is available at http://isemail.info/about
def s_email(sval: str) -> str:
    if not isinstance(sval, type('')):
        raise TypeError
    rfc5322_re = (
        r"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"
        r'"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@'
        r"(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])"
        r"|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]"
        r":(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])")
    if re.match(rfc5322_re, sval):
        return sval
    raise ValueError


# From https://stackoverflow.com/questions/2532053/validate-a-hostname-string
def s_hostname(sval: str) -> str:
    if not isinstance(sval, type('')):
        raise TypeError
    hostname = sval[:]      # Copy since we're modifying input
    if hostname[-1] == ".":
        hostname = hostname[:-1]  # strip exactly one dot from the right, if present
    if len(sval) > 253:
        raise ValueError
    allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    if all(allowed.match(x) for x in hostname.split(".")):
        return sval
    raise ValueError


def val_binary(bval: bytes, condition: Callable) -> bytes:
    if not isinstance(bval, bytes):
        raise TypeError
    if condition(bval):
        return bval
    raise ValueError


def b_mac_addr(bval: bytes) -> bytes:       # Length of MAC addr must be 48 or 64 bits
    return val_binary(bval, lambda x: len(x) == 6 or len(x) == 8)


def b_ipv4_addr(bval: bytes) -> bytes:      # IPv4 address
    return val_binary(bval, lambda x: len(x) == 4)


def b_ipv6_addr(bval: bytes) -> bytes:      # IPv4 address
    return val_binary(bval, lambda x: len(x) == 16)


def _ipnet(aval: [bytes, int], condition: Callable[[list], bool]) -> [bytes, int]:
    if not (isinstance(aval, list) and len(aval) == 2 and isinstance(aval[0], bytes) and isinstance(aval[1], int)):
        raise TypeError
    if condition(aval):
        return aval
    raise ValueError


def a_ipv4_net(aval: [bytes, int]) -> [bytes, int]:       # IPv4 address and netmask
    return _ipnet(aval, lambda x: len(x[0]) == 4 and 0 <= x[1] <= 32)


def a_ipv6_net(aval: [bytes, int]) -> [bytes, int]:       # IPv6 address and netmask
    return _ipnet(aval, lambda x: len(x[0]) == 16 and 0 <= x[1] <= 128)


def val_int(ival: int, condition: Callable[[int], bool]) -> int:
    if not isinstance(ival, int):
        raise TypeError
    if condition(ival):
        return ival
    raise ValueError


def i_i8(ival: int) -> int:
    return val_int(ival, lambda x: -2**7 <= x < 2**7)


def i_i16(ival: int) -> int:
    return val_int(ival, lambda x: -2**15 <= x < 2**15)


def i_i32(ival: int) -> int:
    return val_int(ival, lambda x: -2**31 <= x < 2**31)


def i_i64(ival: int) -> int:
    return val_int(ival, lambda x: -2**63 <= x < 2**63)


# Semantic validation functions
FORMAT_VALIDATE_FUNCTIONS = {
    'String': {
        'email': s_email,
        'hostname': s_hostname,
    },
    'Binary': {
        'eui': b_mac_addr,
        'ipv4-addr': b_ipv4_addr,
        'ipv6-addr': b_ipv6_addr,
    },
    'Array': {
        'ipv4-net': a_ipv4_net,
        'ipv6-net': a_ipv6_net,
    },
    'Integer': {
        'i8': i_i8,
        'i16': i_i16,
        'i32': i_i32,
        'i64': i_i64,
    }
}

# Don't need special format functions, use value constraints:
#   Date-Time       - Integer - min and max value for plausible date range
#   Duration        - Integer - min 0, max value for plausible durations
#   Identifier      - String - regex pattern
#   Port            - Integer - min 0, max 65535


# Create a table of validation functions for format keywords
def format_validators() -> FormatTable:  # Generate validation function table
    # Create a closure for a JSON Schema format keyword
    def make_jsonschema_validator(format_kw: str) -> Callable[[str], str]:
        def validate(val: str) -> str:
            try:
                jsonschema.validate(
                    instance=val,
                    schema={'type': 'string', 'format': format_kw},
                    format_checker=jsonschema.draft7_format_checker
                )
            except jsonschema.exceptions.ValidationError as e:
                raise ValueError(e.message)
            return val
        return validate

    # Ensure code is in sync with jadn_defs
    assert set(FORMAT_VALIDATE) == {y for x in FORMAT_VALIDATE_FUNCTIONS.values() for y in x}

    # Add JSON Schema validation functions to those defined here
    validation_functions = deepcopy(FORMAT_VALIDATE_FUNCTIONS)
    validation_functions['String'].update({f: make_jsonschema_validator(f) for f in FORMAT_JS_VALIDATE})
    return validation_functions
