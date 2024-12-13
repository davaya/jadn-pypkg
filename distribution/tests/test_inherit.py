"""
Test JADN Codec
"""
import unittest
import jadn


class Inherit(unittest.TestCase):

    def setUp(self):
        with open('jadn-v2.0-inherit.jadn') as fp:
            self.schema = jadn.load(fp)
        sa = jadn.analyze(self.schema)
        if sa['undefined']:
            print('Warning - undefined:', sa['undefined'])
        self.codec = jadn.codec.Codec(self.schema, verbose_rec=True, verbose_str=True)

    c1 = {'id': 42, 'name': 'Fred'}
    p1 = {'id': 42, 'email': 'fred@example.com'}
    p2 = {'id': 42, 'name': 'Fred', 'email': 'fred@example.com'}
    b1 = {'id': 42}
    b2 = {}
    b3 = {'id': 42, 'addr': "Spring Street"}

    def test_schema(self):     # Schema error
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Person3', self.c1), self.c1)  # Can't extend final type
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Person4', self.c1), self.c1)  # Extend can't remove fields
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Building2', self.c1), self.c1)  # Can't remove required field
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Building3', self.c1), self.c1)  # Restrict can't add fields

    def test_extend(self):
        self.assertEqual(self.codec.encode('Person1', self.c1), self.c1)  # OK
        self.assertEqual(self.codec.encode('Person1', self.p1), self.p1)  # OK
        self.assertEqual(self.codec.encode('Person1', self.p2), self.p2)  # OK
        self.assertEqual(self.codec.encode('Person2', self.c1), self.c1)  # OK
        self.assertEqual(self.codec.encode('Person2', self.p1), self.p1)  # OK
        self.assertEqual(self.codec.encode('Person2', self.p2), self.p2)  # OK

    def test_restrict(self):
        self.assertEqual(self.codec.encode('Building1', self.b1), self.b1)  # OK
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Building', self.c1), self.c1)  # Optional "name" removed
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Building2', self.b1), self.b1)  # Cannot remove "id"
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Building2', self.b2), self.b2)  # Cannot remove "id"
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Building3', self.b1), self.b1)  # Cannot extend "addr"
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Building3', self.b3), self.b3)  # Cannot extend "addr"

    def test_abstract(self):
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Class1', self.c1), self.c1)  # Can't instantiate abstract type
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Class3', self.c1), self.c1)  # Can't instantiate abstract type

    def test_final(self):
        self.assertEqual(self.codec.encode('Class2', self.c1), self.c1)  # Can instantiate final type
        with self.assertRaises(ValueError):
            self.assertEqual(self.codec.encode('Person3', self.p1), self.p1)  # Cannot extend final type


if __name__ == '__main__':
    unittest.main()
