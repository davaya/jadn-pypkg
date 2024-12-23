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
    """
    JADN DataTypes with inheritance options. Errors in schema (marked ERR) or messages:
    
    Class1 - abstract id, name?
    Class2 - final id, name?
    Class3 - abstract, final id, name?
    Person1 - eClass1 +email
    Person2 - abstract, eClass1 +email
    Person3 - ERR eClass2
    Person4 - ERR eClass1 -email
    Person5 - ePerson1 +phone?
    Person6 - ERR ePerson1 +name
    Person7 - rPerson1 +name
    Building1 - rClass1 -name
    Building2 - ERR rClass1 -id
    Building3 - ERR rClass1 -name +addr
    """

    c1 = {'id': 42, 'name': 'Fred'}
    p1 = {'id': 42, 'email': 'fred@example.com'}
    p2 = {'id': 42, 'name': 'Fred', 'email': 'fred@example.com'}
    p3 = {'id': 42, 'email': 'fred@example.com'}
    p4 = {'id': 42, 'name': 'Fred', 'email': 'fred@example.com', 'phone': '010-555-1234'}
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
        self.assertEqual(self.codec.encode('Person5', self.p4), self.p4)  # OK
        self.assertEqual(self.codec.encode('Person5', self.p1), self.p1)  # OK
        self.assertEqual(self.codec.encode('Person7', self.p3), self.p3)  # OK

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
