import jadn
import json
import jsonschema
import os

print(f'Installed JADN version: {jadn.__version__}')

"""
Define and validate a JADN schema
"""
schema_data = {     # This is a Python value. Avoiding double quotes reduces chance of confusion with JSON strings.
    'types': [      # Python values allow comments, single quoted strings, None, True, False.
        ['Person', 'Record', [], 'JADN equivalent of structure from https://developers.google.com/protocol-buffers', [
            [1, 'name', 'String', [], ''],
            [2, 'id', 'Integer', [], ''],
            [3, 'email', 'String', ['/email', '[0'], '']
        ]
    ]]
}
schema = jadn.check(schema_data)        # jadn.check returns unmodified schema to facilitate chaining
assert schema == schema_data

"""
Convert schema to alternate formats
"""
print('\nSchema:\n------------------')
print(jadn.dumps(schema))

print('\nSchema (JADN IDL):\n------------------')
jidl_doc = jadn.convert.jidl_dumps(schema)
print(jidl_doc)
assert schema == jadn.convert.jidl_loads(jidl_doc)      # Verify lossless round-trip conversion.

print('\nSchema (JADN IDL, adjust columns, truncate comments):\n------------------')
print(jadn.convert.jidl_dumps(jadn.transform.strip_comments(schema, width=9), columns={'id':2, 'name':8, 'desc':30}))

print('\nSchema (HTML):\n------------------')
html_doc = jadn.convert.html_dumps(schema)
print(html_doc)
theme = os.path.join(jadn.data_dir(), 'dtheme.css')
with open(theme) as f:
    print(f' (Render with {theme}: {f.read(50)} ...)')
assert schema == jadn.convert.html_loads(html_doc)      # Verify lossless round-trip conversion.
                                        # schema options must be canonical to avoid spurious mismatch.

print('\nSchema (Markdown):\n------------------')
print(jadn.convert.table_dumps(schema))

print('\nSchema (JSON Schema):\n------------------')
schema.update({                 # JSON Schema conversion needs root type (Person) and namespace $id
    'meta': {
        'module': 'http://example.com/rolodex/v1.0',
        'exports': ['Person']
    }
})
js_schema = jadn.translate.json_schema_dumps(schema)
print(js_schema)

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
        {'email': '@joe.mailbox.com', 'name': 'Joe', 'id': 14912},          # Bad: Not a valid email address
    ]

    for n, v in enumerate(data, start=1):
        try:
            encoded_data = json.dumps(codec.encode('Person', v))    # Validate that data is an instance of Person
            print(f'{n:>3} Valid: {encoded_data}')
        except (ValueError, TypeError) as err:                      # Validation errors raise an exception
            print(f'{n:>3} Error: {err}')

        try:                                                        # Validate same data using generated JSON Schema
            jsonschema.validate(v, json.loads(js_schema), format_checker=jsonschema.draft7_format_checker)
        except jsonschema.exceptions.ValidationError as err:
            print(f'     JSON Schema: {err.message}')               # jsonschema author refuses to validate email syntax


print('\nSerialized Data:\n----------------')
print('Verbose JSON:')          # Create a codec from schema, Validate and encode as verbose JSON
print_encoded_data(jadn.codec.Codec(schema, verbose_rec=True, verbose_str=True))

print('\nMinimized JSON:')      # Create a codec from schema, Validate and encode as optimized JSON
print_encoded_data(jadn.codec.Codec(schema, verbose_rec=False, verbose_str=False))
