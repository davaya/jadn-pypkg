import json
import jadn
import os
from jadn.codec import Codec
from jadn.transform import strip_comments
from jadn.convert import jidl_dumps, table_dumps, html_dumps
from jadn.translate import json_schema_dumps

"""
Define and validate a JADN schema
"""
schema_data = {     # This is a Python literal, not JSON. It is a value as returned by json.load() or jadn.load()
    'types': [
        ['Person', 'Record', [], 'JADN equivalent of structure from https://developers.google.com/protocol-buffers', [
            [1, 'name', 'String', [], ''],
            [2, 'id', 'Integer', [], ''],
            [3, 'email', 'String', ['[0', '/email'], '']
        ]
    ]]
}
schema = jadn.check(schema_data)
assert schema == schema_data            # jadn.check returns unmodified schema to facilitate chaining

"""
Convert schema to alternate formats
"""
print('\nSchema (Generic JSON):\n----------------------')
print(json.dumps(schema, indent=1))

print('\nSchema (JADN-formatted JSON):\n-----------------------------')
print(jadn.dumps(schema))

print('\nSchema (JADN IDL):\n------------------')
print(jidl_dumps(schema))

print('\nSchema (JADN IDL with truncated comments):\n------------------')
print(jidl_dumps(strip_comments(schema, width=32)))

print('\nSchema (HTML):\n------------------')
print(html_dumps(schema))
theme = os.path.join(jadn.data_dir(), 'dtheme.css')
with open(theme) as f:
    print(f' (Render with {theme}: {f.read(50)} ...)')

print('\nSchema (Markdown):\n------------------')
print(table_dumps(schema))

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
    data = [
        {'id': 14912, 'name': 'Joe'},                                       # Valid "Person" record
        {'name': 'Karen', 'id': 37145, 'email': 'karen@symphony.org'},      # Valid "Person" record
        {'email': 'alf@hotmail.com', 'id': 20443, 'name': 'Lester'},        # Valid "Person" record
        {'name': 'Joe', 'id': '123-45-6789'},                               # Bad: ID must be an Integer
        {'name': 'Joe', 'email': 'joe@mailbox.com'},                        # Bad: ID is required
        {'email': 'joe.mailbox.com', 'name': 'Joe', 'id': 14912},           # Bad: Not a valid email address
    ]

    for n, v in enumerate(data, start=1):
        try:
            encoded_data = json.dumps(codec.encode('Person', v))    # Validate that data is an instance of Person
            print(f'{n:>3} Valid: {encoded_data}')
        except (ValueError, TypeError) as err:                      # Validation errors raise an exception
            print(f'{n:>3} Error: {err}')


print('\nSerialized Data:\n----------------')
print('Verbose JSON:')          # Create a codec from schema, Validate and encode as verbose JSON
print_encoded_data(Codec(schema, verbose_rec=True, verbose_str=True))

print('\nMinimized JSON:')      # Create a codec from schema, Validate and encode as optimized JSON
print_encoded_data(Codec(schema, verbose_rec=False, verbose_str=False))
