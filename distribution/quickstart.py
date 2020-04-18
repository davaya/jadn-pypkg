import json
from jadn.core import jadn_check, jadn_dumps, Codec
from jadn.convert.w_jidl import jidl_dumps
from jadn.translate.w_jsonschema import json_schema_dumps
from jadn.transform.transform import jadn_strip

"""
Define and validate a JADN schema
"""
schema_data = {
    'types': [
        ['Person', 'Record', [], 'JADN equivalent of structure from https://developers.google.com/protocol-buffers', [
            [1, 'name', 'String', [], ''],
            [2, 'id', 'Integer', [], ''],
            [3, 'email', 'String', ['[0', '/email'], '']
        ]
    ]]
}
schema = jadn_check(schema_data)
assert schema == schema_data            # jadn_check returns unmodified schema for chaining

"""
Convert schema to alternate formats
"""
print('\nSchema (Generic JSON):\n----------------------')
print(json.dumps(schema, indent=1))     # Display schema as generic JSON data
print('\nSchema (JADN-formatted JSON):\n-----------------------------')
print(jadn_dumps(schema))               # Display schema as JADN-formatted JSON data
print('\nSchema (JADN IDL):\n------------------')
print(jidl_dumps(schema))               # Display schema as IDL text
print('\nSchema (JADN IDL with truncated comments):\n------------------')
print(jidl_dumps(jadn_strip(schema, width=32)))

print('\nSchema (JSON Schema):\n------------------')
schema.update({                         # JSON Schema conversion needs a designated root type (Person)
    'meta': {
        'module': 'http://example.com/rolodex/v1.0',
        'exports': ['Person']
    }
})
print(json_schema_dumps(schema))

"""
Validate and serialize test data
"""
def print_encoded_data(codec):
    p1 = {'id': 14912, 'name': 'Joe'}                                   # Valid "Person" record
    p2 = {'name': 'Joe', 'id': '123-45-6789'}                           # Bad: ID must be an Integer
    p3 = {'name': 'Joe', 'email': 'joe@mailbox.com'}                    # Bad: ID is required
    p4 = {'email': 'joe.mailbox.com', 'name': 'Joe', 'id': 14912}       # Bad: Not a valid email address
    for name, data in {'p1': p1, 'p2': p2, 'p3': p3, 'p4': p4}.items():
        try:
            encoded_data = json.dumps(codec.encode('Person', data))     # Validate that data is an instance of Person
            print(f'Valid {name}: {encoded_data}')
        except (ValueError, TypeError) as err:                          # Validation errors raise an exception
            print(f'Error {name}: {err}')


print('\nSerialized Data:\n----------------')
print('Verbose JSON:')          # Create a codec from schema, Validate and encode as verbose JSON
print_encoded_data(Codec(schema, verbose_rec=True, verbose_str=True))

print('\nMinimized JSON:')      # Create a codec from schema, Validate and encode as optimized JSON
print_encoded_data(Codec(schema, verbose_rec=False, verbose_str=False))
