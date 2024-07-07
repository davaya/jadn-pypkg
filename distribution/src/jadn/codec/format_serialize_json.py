import base64
import binascii
import re
import string

from datetime import datetime, timezone
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Callable, Dict, Tuple
from ..definitions import FORMAT_SERIALIZE

UUID = r'(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89AB][0-9a-f]{3}-[0-9a-f]{12}$'

FormatFunction = Callable[[Any], Any]
FormatTable = Dict[str, Dict[str, Tuple[FormatFunction, FormatFunction]]]
# TODO: Convert a2s_ipvX_net and s2a_ipvX_net functions to use ipaddress.IPvXNetwork


def _format_pass(val: Any) -> Any:
    return val


def _codec_function(format_table: FormatTable, base_type: str, format_kw: str, direction: int) -> FormatFunction:
    try:
        if not format_kw:
            format_kw = {'Binary': 'b', 'Number': 'f64'}[base_type]  # Set default format for type if one exists
        return format_table[base_type][format_kw][direction]
    except KeyError:
        return _format_pass


# Return serialization functions for the specified format keyword and data type
def get_format_encode_function(format_table: FormatTable, base_type: str, format_kw: str) -> FormatFunction:
    return _codec_function(format_table, base_type, format_kw, 0)


def get_format_decode_function(format_table: FormatTable, base_type: str, format_kw: str) -> FormatFunction:
    return _codec_function(format_table, base_type, format_kw, 1)


# Binary to String, String to Binary conversion functions
def b2s_hex(bval: bytes) -> str:      # Convert from binary to hex string
    return base64.b16encode(bval).decode()


def s2b_hex(sval: str) -> bytes:      # Convert from hex string to binary
    try:
        return base64.b16decode(sval)
    except binascii.Error:
        raise TypeError


def b2s_hex_lc(bval: bytes) -> str:      # Convert from binary to hex string
    return base64.b16encode(bval).decode().lower()


def s2b_hex_lc(sval: str) -> bytes:      # Convert from hex string to binary
    try:
        return base64.b16decode(sval, casefold=True)
    except binascii.Error:
        raise TypeError


def b2s_base64url(bval: bytes) -> str:      # Convert from binary to base64url string
    return base64.urlsafe_b64encode(bval).decode().rstrip('=')


def s2b_base64url(sval: str) -> bytes:      # Convert from base64url string to binary
    v = sval
    if mod := len(sval) % 4:  # Pad b64 string out to a multiple of 4 characters
        v = f"{sval}{'=' * (4-mod)}"
    if set(v) - set(string.ascii_letters + string.digits + '-_='):  # Python 2 doesn't support Validate
        raise TypeError('base64decode: bad character')
    return base64.b64decode(str(v), altchars=b'-_')


def b2s_ipv4_addr(bval: bytes) -> str:      # Convert IPv4 address from binary to string
    return IPv4Address(bval).compressed


def b2s_ipv6_addr(bval: bytes) -> str:        # Convert ipv6 address from binary to string
    return IPv6Address(bval).compressed


def s2b_ipv4_addr(sval: str) -> bytes:    # Convert IPv4 addr from string to binary
    return IPv4Address(sval).packed


def s2b_ipv6_addr(sval: str) -> bytes:    # Convert IPv6 address from string to binary
    return IPv6Address(sval).packed


def b2s_uuid(bval: bytes) -> str:   # Convert RFC 4122 UUID from 128 bit value to text representation
    u = b2s_hex_lc(bval)
    us = f'{u[:8]}-{u[8:12]}-{u[12:16]}-{u[16:20]}-{u[20:]}'
    if m := re.match(UUID, us):
        return us
    raise ValueError


def s2b_uuid(sval: str) -> bytes:   # Convert RFC 4122 UUID from text to 128 bit value
    if m := re.match(UUID, sval):
        return s2b_hex_lc(sval.replace('-', ''))
    raise ValueError


FORMAT_CONVERT_BINARY_FUNCTIONS = {
    'b': (b2s_base64url, s2b_base64url),            # Base64url
    'x': (b2s_hex_lc, s2b_hex_lc),                  # Hex lower case
    'X': (b2s_hex, s2b_hex),                        # Hex upper case (RFC conforming)
    'ipv4-addr': (b2s_ipv4_addr, s2b_ipv4_addr),    # IPv4 Address
    'ipv6-addr': (b2s_ipv6_addr, s2b_ipv6_addr),    # IPv6 Address
    'eui': (b2s_hex, s2b_hex),                      # EUI - TODO: write colon-hex A0:32:F9:...
    'uuid': (b2s_uuid, s2b_uuid),                   # 128 bit UUID with RFC 4122 text representation
}


# IP Net (address, prefix length tuple) conversions
def a2s_ipv4_net(aval: [str, int]) -> str:
    if aval[1] < 0 or aval[1] > 32:  # Verify prefix length is valid
        raise ValueError
    sa = b2s_ipv4_addr(aval[0])      # Convert Binary bytes to type-specific string
    return f'{sa}/{aval[1]}' if aval[1] != 32 else sa


def a2s_ipv6_net(aval: [str, int]) -> str:
    if aval[1] < 0 or aval[1] > 128:  # Verify prefix length is valid
        raise ValueError
    sa = b2s_ipv6_addr(aval[0])       # Convert Binary bytes to type-specific string
    return f'{sa}/{aval[1]}' if aval[1] != 128 else sa


def s2a_ipv4_net(sval: str) -> [str, int]:
    sv = sval.split('/', 1)
    sa = s2b_ipv4_addr(sv[0])                  # Convert type-specific string to Binary bytes
    prefix_len = int(sv[1]) if len(sv) > 1 else 32
    if prefix_len < 0 or prefix_len > 32:
        raise ValueError
    return [sa, prefix_len]


def s2a_ipv6_net(sval: str) -> [str, int]:
    sv = sval.split('/', 1)
    sa = s2b_ipv6_addr(sv[0])                  # Convert type-specific string to Binary bytes
    prefix_len = int(sv[1]) if len(sv) > 1 else 128
    if prefix_len < 0 or prefix_len > 128:
        raise ValueError
    return [sa, prefix_len]


def a2s_tag_uuid(aval: [str, str]) -> str:
    return aval[0] + '-' + aval[1]


def s2a_tag_uuid(sval: str) -> [str, str]:
    t, u = sval.split('-', maxsplit=1)
    return [t, u]


FORMAT_CONVERT_MULTIPART_FUNCTIONS = {
    'ipv4-net': (a2s_ipv4_net, s2a_ipv4_net),       # IPv4 Net Address with CIDR prefix length
    'ipv6-net': (a2s_ipv6_net, s2a_ipv6_net),       # IPv6 Net Address with CIDR prefix length
    'tag-uuid': (a2s_tag_uuid, s2a_tag_uuid),       # UUID with tag prefix
}


def int2datems(dt: int) -> str:
    y = datetime.isoformat(datetime.fromtimestamp(dt/1000., timezone.utc))
    if m := re.match(r'^(.+)(\.\d\d\d)(\d\d\d)(.+)$', y):   # strip microseconds to milliseconds
        y = m.group(1) + m.group(2) + m.group(4)
    return y


def datems2int(dts: str) -> int:
    x = datetime.fromisoformat(dts.upper().replace('Z', '+00:00').replace(' ', 'T'))
    return int(1000 * datetime.timestamp(x))


# No special sized integer serialization in JSON.  Define these for packed encoding.
FORMAT_CONVERT_INTEGER_FUNCTIONS = {
    'datetime-ms': (int2datems, datems2int),      # RFC 3339 milliseconds from epoch
    'i8': (_format_pass, _format_pass),
    'i16': (_format_pass, _format_pass),
    'i32': (_format_pass, _format_pass),
    'i64': (_format_pass, _format_pass)
}

# No special serialization in JSON. Define these for CBOR encoding.
FORMAT_CONVERT_NUMBER_FUNCTIONS = {
    'f16': (_format_pass, _format_pass),
    'f32': (_format_pass, _format_pass),
    'f64': (_format_pass, _format_pass)
}


# Create a table listing the serialization functions for each format keyword
def json_format_codecs() -> Dict[str, Dict[str, Tuple[FormatFunction, FormatFunction]]]:  # Return table of JSON format serialization functions
    # Ensure code is in sync with JADN definitions
    assert set(FORMAT_SERIALIZE) == \
           set(FORMAT_CONVERT_BINARY_FUNCTIONS) |\
           set(FORMAT_CONVERT_MULTIPART_FUNCTIONS) |\
           set(FORMAT_CONVERT_INTEGER_FUNCTIONS) |\
           set(FORMAT_CONVERT_NUMBER_FUNCTIONS)

    return {
        'Binary': FORMAT_CONVERT_BINARY_FUNCTIONS,
        'Array': FORMAT_CONVERT_MULTIPART_FUNCTIONS,
        'Integer': FORMAT_CONVERT_INTEGER_FUNCTIONS,
        'Number': FORMAT_CONVERT_NUMBER_FUNCTIONS
    }
