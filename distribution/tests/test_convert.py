import jadn
import os
import unittest


# TODO: Read and Write JIDL and HTML, Write Markdown, JSON Schema, XSD, CDDL


quickstart_schema = {
    'types': [
        ['Person', 'Record', [],
         'JADN equivalent of structure from https://developers.google.com/protocol-buffers', [
             [1, 'name', 'String', [], ''],
             [2, 'id', 'Integer', [], ''],
             [3, 'email', 'String', ['/email', '[0'], '']]]]
    }

class HtmlConvert(unittest.TestCase):

    def _html_convert(self, schema):
        html_doc = jadn.convert.html_dumps(schema)
        schema_new = jadn.convert.html_loads(html_doc)
        self.assertEqual(schema, jadn.canonicalize(schema_new))

    def test_0_quickstart(self):
        self._html_convert(jadn.check(quickstart_schema))

    def test_1_types(self):
        self._html_convert(jadn.load('convert_types.jadn'))

    def test_2_jadn(self):
        self._html_convert(jadn.load(os.path.join(jadn.data_dir(), 'jadn_v1.0_schema.jadn')))

    def test_3_examples(self):
        self._html_convert(jadn.load('jadn-v1.0-examples.jadn'))


class JidlConvert(unittest.TestCase):

    def _jidl_convert(self, schema):
        jidl_doc = jadn.convert.jidl_dumps(schema)
        schema_new = jadn.convert.jidl_loads(jidl_doc)
        self.maxDiff = None
        self.assertEqual(schema, jadn.canonicalize(schema_new))

    def test_0_quickstart(self):
        self._jidl_convert(jadn.check(quickstart_schema))

    def test_1_types(self):
        self._jidl_convert(jadn.load('convert_types.jadn'))

    def test_2_jadn(self):
        self._jidl_convert(jadn.load(os.path.join(jadn.data_dir(), 'jadn_v1.0_schema.jadn')))

    def test_3_examples(self):
        self._jidl_convert(jadn.load('jadn-v1.0-examples.jadn'))


if __name__ == '__main__':
    unittest.main()
