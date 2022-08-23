"""
Test JADN Schema transformations
Transformation -> Reduce Complexity
"""
from unittest import main, TestCase

import jadn
from jadn.definitions import EXTENSIONS


class Resolve(TestCase):
    schema = {}  # TODO: test Merge imported definitions

    # def test_resolve(self):


class StripComments(TestCase):
    schema = {
        'types': [
            ['Person', 'Record', [], 'JADN equivalent of structure from https://developers.google.com/protocol-buffers', [
                [1, 'name', 'String', [], 'The person\'s name.'],
                [2, 'id', 'Integer', [], 'A person\'s unique id'],
                [3, 'email', 'String', ['[0', '/email'], 'An email address for the person.']
            ]]
        ]
    }
    stripped_schema = {
        'types': [
            ['Person', 'Record', [], '', [
                [1, 'name', 'String', [], ''],
                [2, 'id', 'Integer', [], ''],
                [3, 'email', 'String', ['[0', '/email'], '']
            ]
             ]]
    }
    trunc20_schema = {
        'types': [
            ['Person', 'Record',                     [], 'JADN equivalent of..', [
                [1, 'name', 'String',                [], 'The person\'s name.'],
                [2, 'id', 'Integer',                 [], 'A person\'s unique id'],
                [3, 'email', 'String', ['[0', '/email'], 'An email address f..']
            ]]
        ]
    }

    def test_strip_comments(self):
        jadn.check(self.schema)
        jadn.check(self.stripped_schema)
        ss = jadn.transform.strip_comments(self.schema)
        self.assertEqual(ss['types'], self.stripped_schema['types'])

    def test_truncate_comments(self):
        jadn.check(self.schema)
        jadn.check(self.trunc20_schema)
        ss = jadn.transform.strip_comments(self.schema, width=20)
        self.assertEqual(ss['types'], self.trunc20_schema['types'])


class UnfoldExtensions(TestCase):
    def do_unfold_test(self, folded_schema, unfolded_schema, extensions=EXTENSIONS):
        jadn.check(folded_schema)
        jadn.check(unfolded_schema)
        us = jadn.transform.unfold_extensions(folded_schema, extensions)
        self.assertEqual(us['types'], unfolded_schema['types'])

    """
    Type Definition in Fields Extension
    """
    schema_anon_folded = {       # id, vtype, ktype, enum, pointer, format, pattern, minv, maxv, unique
        'types': [
            ['Color', 'Map', [], '', [
                [1, 'red', 'Integer', [], ''],
                [2, 'green', 'Integer', [], ''],
                [3, 'blue', 'Integer', [], '']
            ]],
            ['Dir', 'Record', [], '', [
                [1, 'a', 'String', [], ''],
                [2, 'b', 'Subdir', ['<'], '']
            ]],
            ['Subdir', 'Map', [], '', [
                [1, 'foo', 'Number', [], ''],
                [2, 'bar', 'String', [], '']
            ]],
            ['T-anon', 'Record', [], '', [
                [1, 'id', 'Enumerated', ['#Color', '='], ''],
                [2, 'enum', 'Enumerated', ['#Color', '[0'], ''],
                [3, 'vtype', 'ArrayOf', ['*#Color'], ''],
                [4, 'kvtype', 'MapOf', ['+#Color', '*String'], ''],
                [5, 'pointer', 'Enumerated', ['>Dir'], ''],
                [6, 'format', 'String', ['/idn-email', '[0'], ''],
                [7, 'pattern', 'String', ['%\\d+'], ''],
                [8, 'mult', 'ArrayOf', ['*Color', '{2', '}5'], ''],
                [9, 'unique', 'ArrayOf', ['*String', 'q'], '']
            ]]
        ]
    }
    schema_anon_unfolded = {
        'types': [
            ['Color', 'Map', [], '', [
                [1, 'red', 'Integer', [], ''],
                [2, 'green', 'Integer', [], ''],
                [3, 'blue', 'Integer', [], '']
            ]],
            ['Dir', 'Record', [], '', [
                [1, 'a', 'String', [], ''],
                [2, 'b', 'Subdir', ['<'], '']
            ]],
            ['Subdir', 'Map', [], '', [
                [1, 'foo', 'Number', [], ''],
                [2, 'bar', 'String', [], '']
            ]],
            ['T-anon', 'Record', [], '', [
                [1, 'id', 'Color$Enum-Id', [], ''],
                [2, 'enum', 'Color$Enum', ['[0'], ''],
                [3, 'vtype', 'T-anon$vtype', [], ''],
                [4, 'kvtype', 'T-anon$kvtype', [], ''],
                [5, 'pointer', 'Dir$Pointer', [], ''],
                [6, 'format', 'T-anon$format', ['[0'], ''],
                [7, 'pattern', 'T-anon$pattern', [], ''],
                [8, 'mult', 'T-anon$mult', [], ''],
                [9, 'unique', 'T-anon$unique', [], '']
            ]],
            ['Color$Enum-Id', 'Enumerated', ['#Color', '='], ''],
            ['Color$Enum', 'Enumerated', ['#Color'], ''],
            ['T-anon$vtype', 'ArrayOf', ['*#Color'], ''],
            ['T-anon$kvtype', 'MapOf', ['+#Color', '*String'], ''],
            ['Dir$Pointer', 'Enumerated', ['>Dir'], ''],
            ['T-anon$format', 'String', ['/idn-email'], ''],
            ['T-anon$pattern', 'String', ['%\\d+'], ''],
            ['T-anon$mult', 'ArrayOf', ['*Color', '{2', '}5'], ''],
            ['T-anon$unique', 'ArrayOf', ['*String', 'q'], ''],
        ]
    }
    schema_anon_unfolded_all = {
        'types': [
            ['Color', 'Map', [], '', [
                [1, 'red', 'Integer', [], ''],
                [2, 'green', 'Integer', [], ''],
                [3, 'blue', 'Integer', [], '']
            ]],
            ['Dir', 'Record', [], '', [
                [1, 'a', 'String', [], ''],
                [2, 'b', 'Subdir', ['<'], '']
            ]],
            ['Subdir', 'Map', [], '', [
                [1, 'foo', 'Number', [], ''],
                [2, 'bar', 'String', [], '']
            ]],
            ['T-anon', 'Record', [], '', [
                [1, 'id', 'Color$Enum-Id', [], ''],
                [2, 'enum', 'Color$Enum', ['[0'], ''],
                [3, 'vtype', 'T-anon$vtype', [], ''],
                [4, 'kvtype', 'T-anon$kvtype', [], ''],
                [5, 'pointer', 'Dir$Pointer', [], ''],
                [6, 'format', 'T-anon$format', ['[0'], ''],
                [7, 'pattern', 'T-anon$pattern', [], ''],
                [8, 'mult', 'T-anon$mult', [], ''],
                [9, 'unique', 'T-anon$unique', [], '']
            ]],
            ['Color$Enum-Id', 'Enumerated', ['='], '', [
                [1, 'red', ''],
                [2, 'green', ''],
                [3, 'blue', '']
            ]],
            ['Color$Enum', 'Enumerated', [], '', [
                [1, 'red', ''],
                [2, 'green', ''],
                [3, 'blue', '']
            ]],
            ['T-anon$vtype', 'ArrayOf', ['*Color$Enum'], ''],
            ['T-anon$kvtype', 'Map', [], '', [
                [1, 'red', 'String', [], ''],
                [2, 'green', 'String', [], ''],
                [3, 'blue', 'String', [], '']
            ]],
            ['Dir$Pointer', 'Enumerated', [], '', [
                [1, 'a', ''],
                [2, 'b/foo', ''],
                [3, 'b/bar', '']
            ]],
            ['T-anon$format', 'String', ['/idn-email'], ''],
            ['T-anon$pattern', 'String', ['%\\d+'], ''],
            ['T-anon$mult', 'ArrayOf', ['*Color', '{2', '}5'], ''],
            ['T-anon$unique', 'ArrayOf', ['*String', 'q'], ''],
        ]
    }

    def test_anon(self):
        self.do_unfold_test(self.schema_anon_folded, self.schema_anon_unfolded, {'AnonymousType'})

    def test_anon_all(self):
        self.do_unfold_test(self.schema_anon_folded, self.schema_anon_unfolded_all)

    """
    Field Multiplicity Extension
    """
    schema_mult_folded = {  # JADN schema for fields with cardinality > 1 (e.g., list of x)
        'types': [
            ['T-opt-list1', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'T-array1', ['[0'], '']  # Min = 0, Max default = 1 (Undefined type OK for Extension tests)
            ]],
            ['T-list-1-2', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'String', [']2'], '']           # Min default = 1, Max = 2
            ]],
            ['T-list-0-2', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'String', ['[0', ']2'], '']     # Min = 0, Max = 2 (Array is optional, empty is invalid)
            ]],
            ['T-list-2-3', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'String', ['[2', ']3'], '']     # Min = 2, Max = 3
            ]],
            ['T-list-1-n', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'String', [']0'], '']           # Min default = 1, Max = 0 -> n
            ]]
        ]}
    schema_mult_unfolded = {  # JADN schema for fields with cardinality > 1 (e.g., list of x)
        'types': [
            ['T-opt-list1', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'T-array1', ['[0'], '']  # Min = 0, Max default = 1 (Undefined type OK for Extension tests)
            ]],
            ['T-list-1-2', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'T-list-1-2$list', [], '']      # Min default = 1 required
            ]],
            ['T-list-0-2', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'T-list-0-2$list', ['[0'], '']  # Min = 0 optional
            ]],
            ['T-list-2-3', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'T-list-2-3$list', [], '']      # Min default = 1 required
            ]],
            ['T-list-1-n', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'T-list-1-n$list', [], '']
            ]],
            ['T-list-1-2$list', 'ArrayOf', ['*String', '{1', '}2'], ''],    # Min = 1, Max = 2 (options are unordered)
            ['T-list-0-2$list', 'ArrayOf', ['*String', '{1', '}2'], ''],    # Min = 1, Max = 2
            ['T-list-2-3$list', 'ArrayOf', ['*String', '{2', '}3'], ''],    # Min = 2, Max = 3
            ['T-list-1-n$list', 'ArrayOf', ['*String', '{1'], '']           # Min = 1, Max default *
        ]}

    def test_multiplicity(self):
        self.do_unfold_test(self.schema_mult_folded, self.schema_mult_unfolded, {'Multiplicity'})

    def test_multiplicity_all(self):
        self.do_unfold_test(self.schema_mult_folded, self.schema_mult_unfolded)

    """
    Derived Enumeration Extension
    """
    schema_enum1_folded = {
        'types': [
            ['Pixel1', 'Record', [], '', [
                [1, 'red', 'Integer', [], 'rojo'],
                [2, 'green', 'Integer', [], 'verde'],
                [3, 'blue', 'Integer', [], '']
            ]],
            ['Channel', 'Enumerated', ['#Pixel1'], '', []],          # Derived enumeration (explicitly named)
            ['ChannelId', 'Enumerated', ['#Pixel1', '='], '', []],   # Derived enumeration with ID option
            ['ChannelMask', 'ArrayOf', ['*#Pixel1'], '', []],        # Array of items from named derived enum
        ]
    }

    schema_enum2_folded = {
        'types': [
            ['Pixel2', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['Channel2', 'Enumerated', ['#Pixel2'], '', []],  # Derived enumeration (explicitly named)
            ['ChannelId2', 'Enumerated', ['#Pixel2', '='], '', []],  # Derived enumeration with ID option
            ['ChannelMask2', 'ArrayOf', ['*#Pixel2'], '', []],  # Array of items from named derived enum
        ]
    }

    schema_enum3_folded = {
        'types': [
            ['Pixel3', 'Map', ['='], '', [
                [1, 'yellow', 'Integer', [], ''],
                [2, 'orange', 'Integer', [], ''],
                [3, 'purple', 'Integer', [], '']
            ]],
            ['ChannelMask3', 'ArrayOf', ['*#Pixel3'], '', []],      # Array of items from generated derived enum

            ['Foo', 'Array', [], '', [
                [1, 'type', 'Enumerated', ['#Menu'], ''],           # Derived enumeration in a field
                [2, 'value', 'String', [], '']
            ]],
            ['Menu', 'Choice', [], '', [
                [1, 'open', 'String', [], ''],
                [2, 'close', 'String', [], '']
            ]]
        ]
    }

    schema_enum1_unfolded = {
        'types': [
            ['Pixel1', 'Record', [], '', [
                [1, 'red', 'Integer', [], 'rojo'],
                [2, 'green', 'Integer', [], 'verde'],
                [3, 'blue', 'Integer', [], '']
            ]],
            ['Channel', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['ChannelId', 'Enumerated', ['='], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['ChannelMask', 'ArrayOf', ['*Channel'], '', []],
        ]
    }

    schema_enum1_unfolded_all = {
        'types': [
            ['Pixel1', 'Record', [], '', [
                [1, 'red', 'Integer', [], 'rojo'],
                [2, 'green', 'Integer', [], 'verde'],
                [3, 'blue', 'Integer', [], '']
            ]],
            ['Channel', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['ChannelId', 'Enumerated', ['='], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['ChannelMask', 'ArrayOf', ['*Channel'], '', []],
        ]
    }

    schema_enum2_unfolded = {
        'types': [
            ['Pixel2', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['Channel2', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['ChannelId2', 'Enumerated', ['='], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['ChannelMask2', 'ArrayOf', ['*Channel2'], '', []],
        ]
    }

    schema_enum2_unfolded_all = {
        'types': [
            ['Pixel2', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['Channel2', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['ChannelId2', 'Enumerated', ['='], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['ChannelMask2', 'ArrayOf', ['*Channel2'], '', []],
        ]
    }

    schema_enum3_unfolded = {
        'types': [
            ['Pixel3', 'Map', ['='], '', [
                [1, 'yellow', 'Integer', [], ''],
                [2, 'orange', 'Integer', [], ''],
                [3, 'purple', 'Integer', [], '']
            ]],
            ['ChannelMask3', 'ArrayOf', ['*Pixel3$Enum'], '', []],      # Array of items from generated derived enum

            ['Foo', 'Array', [], '', [                                  # Derived enumeration in a field
                [1, 'type', 'Enumerated', ['#Menu'], ''],
                [2, 'value', 'String', [], '']
            ]],
            ['Menu', 'Choice', [], '', [
                [1, 'open', 'String', [], ''],
                [2, 'close', 'String', [], '']
            ]],
            ['Pixel3$Enum', 'Enumerated', [], '', [                     # Generated derived enum - Id not propogated
                [1, 'yellow', ''],
                [2, 'orange', ''],
                [3, 'purple', '']
            ]],
        ]
    }

    schema_enum3_unfolded_all = {
        'types': [
            ['Pixel3', 'Map', ['='], '', [
                [1, 'yellow', 'Integer', [], ''],
                [2, 'orange', 'Integer', [], ''],
                [3, 'purple', 'Integer', [], '']
            ]],
            ['ChannelMask3', 'ArrayOf', ['*Pixel3$Enum'], '', []],      # Array of items from generated derived enum

            ['Foo', 'Array', [], '', [                                  # Derived enumeration in a field
                [1, 'type', 'Menu$Enum', [], ''],
                [2, 'value', 'String', [], '']
            ]],
            ['Menu', 'Choice', [], '', [
                [1, 'open', 'String', [], ''],
                [2, 'close', 'String', [], '']
            ]],
            ['Menu$Enum', 'Enumerated', [], '', [
                [1, 'open', ''],
                [2, 'close', '']
            ]],
            ['Pixel2$Enum', 'Enumerated', [], '', [                     # Generated derived enum - Id not propogated
                [1, 'yellow', ''],
                [2, 'orange', ''],
                [3, 'purple', '']
            ]],
        ]
    }

    def test_derived_enum(self):
        self.do_unfold_test(self.schema_enum1_folded, self.schema_enum1_unfolded, {'DerivedEnum'})
        self.do_unfold_test(self.schema_enum2_folded, self.schema_enum2_unfolded, {'DerivedEnum'})
        self.do_unfold_test(self.schema_enum3_folded, self.schema_enum3_unfolded, {'DerivedEnum'})

    def test_derived_enum_all(self):
        self.do_unfold_test(self.schema_enum1_folded, self.schema_enum1_unfolded_all)
        self.do_unfold_test(self.schema_enum2_folded, self.schema_enum2_unfolded_all)
        self.do_unfold_test(self.schema_enum3_folded, self.schema_enum3_unfolded_all)

    """
    MapOf Enumerated Key Extension
    """
    schema_mapof_folded = {
        'types': [
            ['Colors-Enum', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['Colors-Map', 'MapOf', ['+Colors-Enum', '*Number'], '']
        ]
    }
    schema_mapof_unfolded = {
        'types': [
            ['Colors-Enum', 'Enumerated', [], '', [
                [1, 'red', 'rojo'],
                [2, 'green', 'verde'],
                [3, 'blue', '']
            ]],
            ['Colors-Map', 'Map', [], '', [
                [1, 'red', 'Number', [], 'rojo'],
                [2, 'green', 'Number', [], 'verde'],
                [3, 'blue', 'Number', [], '']
            ]]
        ]
    }

    def test_mapof(self):
        self.do_unfold_test(self.schema_mapof_folded, self.schema_mapof_unfolded, {'MapOfEnum'})

    def test_mapof_all(self):
        self.do_unfold_test(self.schema_mapof_folded, self.schema_mapof_unfolded)

    """
    Pointers Extension
    """
    schema_pointer_folded = {
        'types': [
            ['Catalog', 'Record', [], '', [
                [1, 'a', 'TypeA', [], 'Leaf field (e.g., file)'],
                [2, 'b', 'TypeB', ['<'], 'Collection field (e.g., dir)']
            ]],
            ['TypeA', 'Record', [], '', [
                [1, 'x', 'Number', [], ''],
                [2, 'y', 'Number', [], '']
            ]],
            ['TypeB', 'Record', [], '', [
                [1, 'foo', 'String', [], 'Type'],
                [2, 'bar', 'Integer', [], 'Size']
            ]],
            ['Fields', 'Enumerated', ['#Catalog'], 'Enumerated type with list of fields'],
            ['Paths', 'Enumerated', ['>Catalog'], 'Enumerated type with list of JSON Pointers'],
            ['Simple', 'String', [], 'A type without fields'],
            ['Empty-Fields', 'Enumerated', ['#Simple'], ''],
            ['Empty-Paths', 'Enumerated', ['>Simple'], '']
        ]
    }
    schema_pointer_unfolded = {
        'types': [
            ['Catalog', 'Record', [], '', [
                [1, 'a', 'TypeA', [], 'Leaf field (e.g., file)'],
                [2, 'b', 'TypeB', ['<'], 'Collection field (e.g., dir)']
            ]],
            ['TypeA', 'Record', [], '', [
                [1, 'x', 'Number', [], ''],
                [2, 'y', 'Number', [], '']
            ]],
            ['TypeB', 'Record', [], '', [
                [1, 'foo', 'String', [], 'Type'],
                [2, 'bar', 'Integer', [], 'Size']
            ]],
            ['Fields', 'Enumerated', [], 'Enumerated type with list of fields', [
                [1, 'a', 'Leaf field (e.g., file)'],
                [2, 'b', 'Collection field (e.g., dir)']
            ]],
            ['Paths', 'Enumerated', [], 'Enumerated type with list of JSON Pointers', [
                [1, 'a', 'Leaf field (e.g., file)'],
                [2, 'b/foo', 'Type'],
                [3, 'b/bar', 'Size']
            ]],
            ['Simple', 'String', [], 'A type without fields'],
            ['Empty-Fields', 'Enumerated', [], '', []],
            ['Empty-Paths', 'Enumerated', [], '', []]
        ]
    }

    def test_pointer(self):
        self.do_unfold_test(self.schema_pointer_folded, self.schema_pointer_unfolded, {'DerivedEnum'})

    def test_pointer_all(self):
        self.do_unfold_test(self.schema_pointer_folded, self.schema_pointer_unfolded)

    """
    Link Extension
    """
    schema_link_folded = {
        'types': [
            ['Person', 'Record', [], '', [
                [1, 'id', 'Integer', ['K'], ''],
                [2, 'name', 'String', [], ''],
                [3, 'mother', 'Person', ['L'], ''],
                [4, 'father', 'Person', ['L'], ''],
                [5, 'siblings', 'Person', ['L', '[0', ']0'], ''],
                [6, 'friends', 'Person', ['L', '[0', ']0'], ''],
                [7, 'employer', 'Organization', ['L', '[0'], '']
            ]],
            ['Organization', 'Record', [], '', [
                [1, 'name', 'String', [], ''],
                [2, 'ein', 'String', ['K', '}10', '{10'], '']
            ]]
        ]
    }
    schema_link_unfolded = {
        'types': [
            ['Person', 'Record', [], '', [
                [1, 'id', 'Person$id', [], ''],
                [2, 'name', 'String', [], ''],
                [3, 'mother', 'Person$id', [], ''],
                [4, 'father', 'Person$id', [], ''],
                [5, 'siblings', 'Person$id', ['[0', ']0'], ''],
                [6, 'friends', 'Person$id', ['[0', ']0'], ''],
                [7, 'employer', 'Organization$ein', ['[0'], '']
            ]],
            ['Organization', 'Record', [], '', [
                [1, 'name', 'String', [], ''],
                [2, 'ein', 'Organization$ein', [], '']
            ]],
            ['Person$id', 'Integer', [], '', []],
            ['Organization$ein', 'String', ['}10', '{10'], '']
        ]
    }
    schema_link_unfolded_all = {
        'types': [
            ['Person', 'Record', [], '', [
                [1, 'id', 'Person$id', [], ''],
                [2, 'name', 'String', [], ''],
                [3, 'mother', 'Person$id', [], ''],
                [4, 'father', 'Person$id', [], ''],
                [5, 'siblings', 'Person$siblings', ['[0'], ''],
                [6, 'friends', 'Person$friends', ['[0'], ''],
                [7, 'employer', 'Organization$ein', ['[0'], '']
            ]],
            ['Organization', 'Record', [], '', [
                [1, 'name', 'String', [], ''],
                [2, 'ein', 'Organization$ein', [], '']
            ]],
            ['Person$id', 'Integer', [], '', []],
            ['Organization$ein', 'String', ['}10', '{10'], ''],
            ['Person$siblings', 'ArrayOf', ['*Person$id', '{1'], '', []],
            ['Person$friends', 'ArrayOf', ['*Person$id', '{1']]
        ]
    }

    def test_link(self):
        self.do_unfold_test(self.schema_link_folded, self.schema_link_unfolded, {'Link'})

    def test_link_all(self):
        self.do_unfold_test(self.schema_link_folded, self.schema_link_unfolded_all)


if __name__ == '__main__':
    main()
