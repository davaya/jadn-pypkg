import base64
import binascii
import socket
import string

from socket import AF_INET, AF_INET6
from jadn.definitions import FORMAT_SERIALIZE

"""
Create a table listing the serialization functions for each format keyword
"""


def json_format_codecs():                              # return table of JSON format serialization functions
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


"""
Return serialization functions for the specified format keyword and data type
"""


def get_format_encode_function(format_table, base_type, format_kw):
    return _codec_function(format_table, base_type, format_kw, 0)


def get_format_decode_function(format_table, base_type, format_kw):
    return _codec_function(format_table, base_type, format_kw, 1)


def _codec_function(format_table, base_type, format_kw, direction):
    try:
        if not format_kw:
            format_kw = {'Binary': 'b', 'Number': 'f64'}[base_type]   # Set default format for type if one exists
        return format_table[base_type][format_kw][direction]
    except KeyError:
        return _format_pass


def _format_pass(val):
    return val


"""
Binary to String, String to Binary conversion functions
"""


def b2s_hex(bval: bytes) -> str:      # Convert from binary to hex string
    return base64.b16encode(bval).decode()


def s2b_hex(sval: str) -> bytes:      # Convert from hex string to binary
    try:
        return base64.b16decode(sval)
    except binascii.Error:
        raise TypeError


def b2s_base64url(bval: bytes) -> str:      # Convert from binary to base64url string
    return base64.urlsafe_b64encode(bval).decode().rstrip('=')


def s2b_base64url(sval: str) -> bytes:      # Convert from base64url string to binary
    v = sval + ((4 - len(sval) % 4) % 4)*'='          # Pad b64 string out to a multiple of 4 characters
    if set(v) - set(string.ascii_letters + string.digits + '-_='):  # Python 2 doesn't support Validate
        raise TypeError('base64decode: bad character')
    return base64.b64decode(str(v), altchars=b'-_')


def b2s_ipv4_addr(bval: bytes) -> str:      # Convert IPv4 address from binary to string
    try:
        return socket.inet_ntop(AF_INET, bval)
    except AttributeError:
        try:
            return socket.inet_ntoa(bval)       # Python 2 doesn't support inet_ntop on Windows
        except IOError:
            raise ValueError
    except OSError:
        raise ValueError


def b2s_ipv6_addr(bval: bytes) -> str:        # Convert ipv6 address from binary to string
    try:
        return socket.inet_ntop(AF_INET6, bval)     # Python 2 doesn't support inet_ntop on Windows
    except OSError:
        raise ValueError


def s2b_ipv4_addr(sval: str) -> bytes:    # Convert IPv4 addr from string to binary
    try:
        return socket.inet_pton(AF_INET, sval)
    except AttributeError:       # Python 2 doesn't support inet_pton on Windows
        try:
            return socket.inet_aton(sval)
        except IOError:
            raise ValueError
    except OSError:
        raise ValueError


def s2b_ipv6_addr(sval: str) -> bytes:    # Convert IPv6 address from string to binary
    try:
        return socket.inet_pton(AF_INET6, sval)
    except OSError:         # Python 2 doesn't support inet_pton on Windows
        raise ValueError


FORMAT_CONVERT_BINARY_FUNCTIONS = {
    'b': (b2s_base64url, s2b_base64url),            # Base64url
    'x': (b2s_hex, s2b_hex),                        # Hex
    'ipv4-addr': (b2s_ipv4_addr, s2b_ipv4_addr),    # IPv4 Address
    'ipv6-addr': (b2s_ipv6_addr, s2b_ipv6_addr),    # IPv6 Address
    'eui': (b2s_hex, s2b_hex),                      # EUI - TODO: write colon-hex A0:32:F9:...
}


"""
IP Net (address, prefix length tuple) conversions
"""


def a2s_ipv4_net(aval: [str, int]) -> str:
    if aval[1] < 0 or aval[1] > 32:         # Verify prefix length is valid
        raise ValueError
    sa = b2s_ipv4_addr(aval[0])             # Convert Binary bytes to type-specific string
    return f'{sa}/{aval[1]}'


def a2s_ipv6_net(aval: [str, int]) -> str:
    if aval[1] < 0 or aval[1] > 128:        # Verify prefix length is valid
        raise ValueError
    sa = b2s_ipv6_addr(aval[0])             # Convert Binary bytes to type-specific string
    return f'{sa}/{aval[1]}'


def s2a_ipv4_net(sval: str) -> [str, int]:
    sa, spl = sval.split('/', 1)
    sa = s2b_ipv4_addr(sa)                  # Convert type-specific string to Binary bytes
    prefix_len = int(spl)
    if prefix_len < 0 or prefix_len > 32:
        raise ValueError
    return [sa, prefix_len]


def s2a_ipv6_net(sval: str) -> [str, int]:
    sa, spl = sval.split('/', 1)
    sa = s2b_ipv6_addr(sa)                  # Convert type-specific string to Binary bytes
    prefix_len = int(spl)
    if prefix_len < 0 or prefix_len > 128:
        raise ValueError
    return [sa, prefix_len]


FORMAT_CONVERT_MULTIPART_FUNCTIONS = {
    'ipv4-net': (a2s_ipv4_net, s2a_ipv4_net),       # IPv4 Net Address with CIDR prefix length
    'ipv6-net': (a2s_ipv6_net, s2a_ipv6_net),       # IPv6 Net Address with CIDR prefix length
}

# No special serialization in JSON.  Define these for packed encoding.
FORMAT_CONVERT_INTEGER_FUNCTIONS = {
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
