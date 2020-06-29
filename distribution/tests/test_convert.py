import jadn
import os
import unittest


# TODO: Read and Write JIDL and HTML, Write Markdown, JSON Schema, XSD, CDDL

class JidlConvert(unittest.TestCase):

    schema = {
    }

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.Codec(self.schema, verbose_rec=False, verbose_str=False)


class HtmlConvert(unittest.TestCase):

    def test_example(self):
        schema = jadn.load(os.path.join(jadn.data_dir(), 'convert_test.jadn'))
        html_doc = jadn.convert.html_dumps(schema)
        self.maxDiff = None
        self.assertEqual(schema, jadn.convert.html_loads(html_doc))

    def test_quickstart(self):
        self.maxDiff = None
        schema = jadn.check(
        {   'types': [
                ['Person', 'Record', [],
                 'JADN equivalent of structure from https://developers.google.com/protocol-buffers', [
                     [1, 'name', 'String', [], ''],
                     [2, 'id', 'Integer', [], ''],
                     [3, 'email', 'String', ['/email', '[0'], '']]]]}
        )
        html_doc = jadn.convert.html_dumps(schema)
        self.assertEqual(schema, jadn.convert.html_loads(html_doc))


if __name__ == '__main__':
    unittest.main()
