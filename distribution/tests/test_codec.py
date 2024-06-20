"""
Test JADN Codec
"""
import json
import binascii
import unittest
import jadn
from collections import Counter


# Encode and decode data to verify that numeric object keys work properly when JSON converts them to strings
def _j(data):
    return json.loads(json.dumps(data))


class BasicTypes(unittest.TestCase):
    schema = {                # JADN schema for datatypes used in Basic Types tests
        'types': [
            ['T-bool', 'Boolean', [], ''],
            ['T-int', 'Integer', [], ''],
            ['T-num', 'Number', [], ''],
            ['T-str', 'String', [], ''],
            ['T-bin', 'Binary', [], ''],
            ['T-arrayof', 'ArrayOf', ['*Integer'], ''],
            ['T-arrayof-set', 'ArrayOf', ['*Integer', 's']],
            ['T-arrayof-unique', 'ArrayOf', ['*Integer', 'q']],
            ['T-arrayof-unordered', 'ArrayOf', ['*Integer', 'b']],
            ['T-array', 'Array', [], '', [
                [1, 'f_bool', 'Boolean', ['[0'], ''],
                [2, 'f_int', 'Integer', [], ''],
                [3, 'f_num', 'Number', [], ''],
                [4, 'f_str', 'String', ['[0'], ''],
                [5, 'f_arr', 'T-aa', ['[0'], ''],
                [6, 'f_ao', 'T-arrayof', ['[0'], '']
            ]],
            ['T-aa', 'Array', [], '', [
                [1, 'a', 'Integer', [], ''],
                [2, 'b', 'String', [], '']
            ]],
            ['T-choice', 'Choice', [], '', [
                [1, 'f_str', 'String', [], ''],
                [4, 'f_bool', 'Boolean', [], ''],
                [7, 'f_int', 'Integer', [], '']
            ]],
            ['T-choice-id', 'Choice', ['='], '', [       # Choice.ID - API key = tag
                [1, 'f_str', 'String', [], ''],
                [4, 'f_bool', 'Boolean', [], ''],
                [7, 'f_int', 'Integer', [], '']
            ]],
            ['T-enum', 'Enumerated', [], '', [
                [1, 'first', ''],
                [15, 'extra', ''],
                [8, 'Chunk', '']
            ]],
            ['T-enum-c', 'Enumerated', ['='], '', [
                [1, 'first', ''],
                [15, 'extra', ''],
                [8, 'Chunk', '']
            ]],
            ['T-map-rgba', 'Map', [], '', [
                [2, 'red', 'Integer', [], ''],
                [4, 'green', 'Integer', ['[0'], ''],
                [6, 'blue', 'Integer', [], ''],
                [9, 'alpha', 'Integer', ['[0'], '']
            ]],
            ['T-arr-rgba', 'Array', [], '', [
                [1, 'red', 'Integer', [], ''],
                [2, 'green', 'Integer', ['[0'], ''],
                [3, 'blue', 'Integer', [], ''],
                [4, 'alpha', 'Integer', ['[0'], '']
            ]],
            ['T-rec-rgba', 'Record', [], '', [
                [1, 'red', 'Integer', [], ''],
                [2, 'green', 'Integer', ['[0'], ''],
                [3, 'blue', 'Integer', [], ''],
                [4, 'alpha', 'Integer', ['[0'], '']
            ]]
        ]}

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.codec.Codec(self.schema, verbose_rec=False, verbose_str=False)

    def test_primitive(self):   # Non-composed types (bool, int, num, str)
        self.assertEqual(self.tc.decode('T-bool', True), True)
        self.assertEqual(self.tc.decode('T-bool', False), False)
        self.assertEqual(self.tc.encode('T-bool', True), True)
        self.assertEqual(self.tc.encode('T-bool', False), False)
        with self.assertRaises(ValueError):
            self.tc.decode('T-bool', 'True')
        with self.assertRaises(ValueError):
            self.tc.decode('T-bool', 1)
        with self.assertRaises(ValueError):
            self.tc.encode('T-bool', 'True')
        with self.assertRaises(ValueError):
            self.tc.encode('T-bool', 1)

        self.assertEqual(self.tc.decode('T-int', 35), 35)
        self.assertEqual(self.tc.encode('T-int', 35), 35)
        with self.assertRaises(ValueError):
            self.tc.decode('T-int', 35.4)
        with self.assertRaises(ValueError):
            self.tc.decode('T-int', True)
        with self.assertRaises(ValueError):
            self.tc.decode('T-int', 'hello')
        with self.assertRaises(ValueError):
            self.tc.encode('T-int', 35.4)
        with self.assertRaises(ValueError):
            self.tc.encode('T-int', True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-int', 'hello')

        self.assertEqual(self.tc.decode('T-num', 25.96), 25.96)
        self.assertEqual(self.tc.decode('T-num', 25), 25)
        self.assertEqual(self.tc.encode('T-num', 25.96), 25.96)
        self.assertEqual(self.tc.encode('T-num', 25), 25)
        with self.assertRaises(ValueError):
            self.tc.decode('T-num', True)
        with self.assertRaises(ValueError):
            self.tc.decode('T-num', 'hello')
        with self.assertRaises(ValueError):
            self.tc.encode('T-num', True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-num', 'hello')

        self.assertEqual(self.tc.decode('T-str', 'parrot'), 'parrot')
        self.assertEqual(self.tc.encode('T-str', 'parrot'), 'parrot')
        with self.assertRaises(ValueError):
            self.tc.decode('T-str', True)
        with self.assertRaises(ValueError):
            self.tc.decode('T-str', 1)
        with self.assertRaises(ValueError):
            self.tc.encode('T-str', True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-str', 1)

    def test_arrayof(self):                 # ordered, non-unique
        self.assertEqual(self.tc.decode('T-arrayof', [1, 4, 4, 16]), [1, 4, 4, 16])
        self.assertEqual(self.tc.encode('T-arrayof', [1, 4, 4, 16]), [1, 4, 4, 16])
        self.assertNotEqual(self.tc.decode('T-arrayof', [1, 4, 9, 16]), [4, 9, 1, 16])
        self.assertNotEqual(self.tc.encode('T-arrayof', [1, 4, 9, 16]), [4, 9, 1, 16])
        with self.assertRaises(ValueError):
            self.tc.decode('T-arrayof', [1, '4', 4, 16])
        with self.assertRaises(ValueError):
            self.tc.decode('T-arrayof', 9)
        with self.assertRaises(ValueError):
            self.tc.encode('T-arrayof', [1, '4', 4, 16])
        with self.assertRaises(ValueError):
            self.tc.encode('T-arrayof', 9)

    def test_arrayof_unique(self):          # ordered, unique
        self.assertEqual(self.tc.decode('T-arrayof-unique', [1, 4, 9, 16]), [1, 4, 9, 16])
        self.assertEqual(self.tc.encode('T-arrayof-unique', [1, 4, 9, 16]), [1, 4, 9, 16])
        self.assertNotEqual(self.tc.decode('T-arrayof-unique', [1, 4, 9, 16]), [4, 9, 1, 16])
        self.assertNotEqual(self.tc.encode('T-arrayof-unique', [1, 4, 9, 16]), [4, 9, 1, 16])
        with self.assertRaises(ValueError):
            self.tc.decode('T-arrayof-unique', [1, 4, 4, 16])
        with self.assertRaises(ValueError):
            self.tc.encode('T-arrayof-unique', [1, 4, 4, 16])

    def test_arrayof_set(self):             # unordered, unique
        self.assertEqual(self.tc.decode('T-arrayof-set', [1, 4, 9, 16]), [1, 4, 9, 16])
        self.assertEqual(self.tc.encode('T-arrayof-set', [1, 4, 9, 16]), [1, 4, 9, 16])
        with self.assertRaises(ValueError):
            self.tc.decode('T-arrayof-set', [1, 4, 4, 16])
        with self.assertRaises(ValueError):
            self.tc.encode('T-arrayof-set', [1, 4, 4, 16])

    def test_arrayof_unordered(self):       # unordered, non-unique
        self.assertEqual(self.tc.decode('T-arrayof-unordered', [1, 4, 9, 16]), [1, 4, 9, 16])
        self.assertEqual(self.tc.encode('T-arrayof-unordered', [1, 4, 9, 16]), [1, 4, 9, 16])
        # Codec does not do value comparison so it cannot validate unordered behavior
        # Python Counter type is an unordered non-unique collection ("Bag")
        self.assertEqual(Counter([1, 4, 4, 9, 16]), Counter([4, 9, 1, 16, 4]))
        self.assertNotEqual(Counter([1, 4, 4, 9, 16]), Counter([9, 9, 1, 16, 4]))

    B1b = b'data to be encoded'
    B1s = 'ZGF0YSB0byBiZSBlbmNvZGVk'
    B2b = 'data\nto be ëncoded 旅程'.encode(encoding='UTF-8')
    B2s = 'ZGF0YQp0byBiZSDDq25jb2RlZCDml4XnqIs'
    B3b = binascii.a2b_hex('18e0c9987b8f32417ca6744f544b815ad2a6b4adca69d2c310bd033c57d363e3')
    B3s = 'GODJmHuPMkF8pnRPVEuBWtKmtK3KadLDEL0DPFfTY-M'
    B_bad1b = 'string'
    B_bad2b = 394
    B_bad3b = True
    B_bad1s = 'ZgF%&0B++'

    def test_binary(self):
        self.assertEqual(self.tc.decode('T-bin', self.B1s), self.B1b)
        self.assertEqual(self.tc.decode('T-bin', self.B2s), self.B2b)
        self.assertEqual(self.tc.decode('T-bin', self.B3s), self.B3b)
        self.assertEqual(self.tc.encode('T-bin', self.B1b), self.B1s)
        self.assertEqual(self.tc.encode('T-bin', self.B2b), self.B2s)
        self.assertEqual(self.tc.encode('T-bin', self.B3b), self.B3s)
        with self.assertRaises((TypeError, binascii.Error)):
            self.tc.decode('T-bin', self.B_bad1s)
        with self.assertRaises(ValueError):
            self.tc.encode('T-bin', self.B_bad1b)
        with self.assertRaises(ValueError):
            self.tc.encode('T-bin', self.B_bad2b)
        with self.assertRaises(ValueError):
            self.tc.encode('T-bin', self.B_bad3b)

    C1a = {'f_str': 'foo'}  # Choice - API keys are names
    C2a = {'f_bool': False}
    C3a = {'f_int': 42}
    C1m = {1: 'foo'}
    C2m = {4: False}
    C3m = {7: 42}
    C1_bad1a = {'f_str': 15}
    C1_bad2a = {'type5': 'foo'}
    C1_bad3a = {'f_str': 'foo', 'f_bool': False}
    C1_bad1m = {1: 15}
    C1_bad2m = {3: 'foo'}
    C1_bad3m = {1: 'foo', '4': False}
    C1_bad4m = {'one': 'foo'}

    Cc1a = {1: 'foo'}       # Choice.ID - API keys are IDs
    Cc2a = {4: False}
    Cc3a = {7: 42}
    Cc1m = {1: 'foo'}
    Cc2m = {4: False}
    Cc3m = {7: 42}
    Cc1_bad1a = {1: 15}
    Cc1_bad2a = {8: 'foo'}
    Cc1_bad3a = {1: 'foo', 4: False}
    Cc1_bad1m = {1: 15}
    Cc1_bad2m = {3: 'foo'}
    Cc1_bad3m = {1: 'foo', '4': False}
    Cc1_bad4m = {'one': 'foo'}

    def test_choice_min(self):
        self.assertEqual(self.tc.encode('T-choice', self.C1a), self.C1m)
        self.assertEqual(self.tc.decode('T-choice', self.C1m), self.C1a)
        self.assertEqual(self.tc.decode('T-choice', _j(self.C1m)), self.C1a)
        self.assertEqual(self.tc.encode('T-choice', self.C2a), self.C2m)
        self.assertEqual(self.tc.decode('T-choice', self.C2m), self.C2a)
        self.assertEqual(self.tc.decode('T-choice', _j(self.C2m)), self.C2a)
        self.assertEqual(self.tc.encode('T-choice', self.C3a), self.C3m)
        self.assertEqual(self.tc.decode('T-choice', self.C3m), self.C3a)
        self.assertEqual(self.tc.decode('T-choice', _j(self.C3m)), self.C3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice', self.C1_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice', self.C1_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice', self.C1_bad3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice', self.C1_bad1m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice', self.C1_bad2m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice', self.C1_bad3m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice', self.C1_bad4m)

    def test_choice_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertEqual(self.tc.encode('T-choice', self.C1a), self.C1a)
        self.assertEqual(self.tc.decode('T-choice', self.C1a), self.C1a)
        self.assertEqual(self.tc.encode('T-choice', self.C2a), self.C2a)
        self.assertEqual(self.tc.decode('T-choice', self.C2a), self.C2a)
        self.assertEqual(self.tc.encode('T-choice', self.C3a), self.C3a)
        self.assertEqual(self.tc.decode('T-choice', self.C3a), self.C3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice', self.C1_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice', self.C1_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice', self.C1_bad3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice', self.C1_bad1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice', self.C1_bad2a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice', self.C1_bad3a)

    def test_choice_id_min(self):
        self.assertEqual(self.tc.encode('T-choice-id', self.Cc1a), self.Cc1m)
        self.assertEqual(self.tc.decode('T-choice-id', self.Cc1m), self.Cc1a)
        self.assertEqual(self.tc.decode('T-choice-id', _j(self.Cc1m)), self.Cc1a)
        self.assertEqual(self.tc.encode('T-choice-id', self.Cc2a), self.Cc2m)
        self.assertEqual(self.tc.decode('T-choice-id', self.Cc2m), self.Cc2a)
        self.assertEqual(self.tc.decode('T-choice-id', _j(self.Cc2m)), self.Cc2a)
        self.assertEqual(self.tc.encode('T-choice-id', self.Cc3a), self.Cc3m)
        self.assertEqual(self.tc.decode('T-choice-id', self.Cc3m), self.Cc3a)
        self.assertEqual(self.tc.decode('T-choice-id', _j(self.Cc3m)), self.Cc3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice-id', self.Cc1_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice-id', self.Cc1_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice-id', self.Cc1_bad3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice-id', self.Cc1_bad1m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice-id', self.Cc1_bad2m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice-id', self.Cc1_bad3m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice-id', self.Cc1_bad4m)

    def test_choice_id_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertEqual(self.tc.encode('T-choice-id', self.Cc1a), self.Cc1a)
        self.assertEqual(self.tc.decode('T-choice-id', self.Cc1a), self.Cc1a)
        self.assertEqual(self.tc.encode('T-choice-id', self.Cc2a), self.Cc2a)
        self.assertEqual(self.tc.decode('T-choice-id', self.Cc2a), self.Cc2a)
        self.assertEqual(self.tc.encode('T-choice-id', self.Cc3a), self.Cc3a)
        self.assertEqual(self.tc.decode('T-choice-id', self.Cc3a), self.Cc3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice-id', self.Cc1_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice-id', self.Cc1_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-choice-id', self.Cc1_bad3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice-id', self.Cc1_bad1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice-id', self.Cc1_bad2a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-choice-id', self.Cc1_bad3a)

    def test_enumerated_min(self):
        self.assertEqual(self.tc.encode('T-enum', 'extra'), 15)
        self.assertEqual(self.tc.decode('T-enum', 15), 'extra')
        with self.assertRaises(ValueError):
            self.tc.encode('T-enum', 'foo')
        with self.assertRaises(ValueError):
            self.tc.encode('T-enum', 15)
        with self.assertRaises(ValueError):
            self.tc.encode('T-enum', [1])
        with self.assertRaises(ValueError):
            self.tc.decode('T-enum', 13)
        with self.assertRaises(ValueError):
            self.tc.decode('T-enum', 'extra')
        with self.assertRaises(ValueError):
            self.tc.decode('T-enum', ['first'])

    def test_enumerated_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertEqual(self.tc.encode('T-enum', 'extra'), 'extra')
        self.assertEqual(self.tc.decode('T-enum', 'extra'), 'extra')
        with self.assertRaises(ValueError):
            self.tc.encode('T-enum', 'foo')
        with self.assertRaises(ValueError):
            self.tc.encode('T-enum', 42)
        with self.assertRaises(ValueError):
            self.tc.encode('T-enum', ['first'])
        with self.assertRaises(ValueError):
            self.tc.decode('T-enum', 'foo')
        with self.assertRaises(ValueError):
            self.tc.decode('T-enum', 42)
        with self.assertRaises(ValueError):
            self.tc.decode('T-enum', ['first'])

    def test_enumerated_id_min(self):
        self.assertEqual(self.tc.encode('T-enum-c', 15), 15)
        self.assertEqual(self.tc.decode('T-enum-c', 15), 15)
        with self.assertRaises(ValueError):
            self.tc.encode('T-enum-c', 'extra')
        with self.assertRaises(ValueError):
            self.tc.decode('T-enum-c', 'extra')

    def test_enumerated_id_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertEqual(self.tc.encode('T-enum-c', 15), 15)
        self.assertEqual(self.tc.decode('T-enum-c', 15), 15)
        with self.assertRaises(ValueError):
            self.tc.encode('T-enum-c', 'extra')
        with self.assertRaises(ValueError):
            self.tc.decode('T-enum-c', 'extra')

    RGB1 = {'red': 24, 'green': 120, 'blue': 240}    # API (decoded) and verbose values Map and Record
    RGB2 = {'red': 50, 'blue': 100}
    RGB3 = {'red': 9, 'green': 80, 'blue': 96, 'alpha': 128}
    RGB_bad1a = {'red': 24, 'green': 120}
    RGB_bad2a = {'red': 9, 'green': 80, 'blue': 96, 'beta': 128}
    RGB_bad3a = {'red': 9, 'green': 80, 'blue': 96, 'alpha': 128, 'beta': 196}
    RGB_bad4a = {'red': 'four', 'green': 120, 'blue': 240}
    RGB_bad5a = {'red': 24, 'green': '120', 'blue': 240}
    RGB_bad6a = {'red': 24, 'green': 120, 'bleu': 240}
    RGB_bad7a = {'1': 24, 'green': 120, 'blue': 240}
    RGB_bad8a = {1: 24, 'green': 120, 'blue': 240}

    Map1m = {2: 24, 4: 120, 6: 240}                  # Encoded values Map (minimized and dict/tag mode)
    Map2m = {2: 50, 6: 100}
    Map3m = {2: 9, 4: 80, 6: 96, 9: 128}
    Map_bad1m = {2: 24, 4: 120}
    Map_bad2m = {2: 9, 4: 80, 6: 96, 9: 128, 12: 42}
    Map_bad3m = {2: 'four', 4: 120, 6: 240}
    Map_bad4m = {'two': 24, 4: 120, 6: 240}
    Map_bad5m = [24, 120, 240]

    Rec1m = [24, 120, 240]                          # Encoded values Record (minimized) and API+encoded Array values
    Rec2m = [50, None, 100]
    Rec3m = [9, 80, 96, 128]
    Rec_bad1m = [24, 120]
    Rec_bad2m = [9, 80, 96, 128, 42]
    Rec_bad3m = ['four', 120, 240]

    Rec1n = {1: 24, 2: 120, 3: 240}                  # Encoded values Record (unused dict/tag mode)
    Rec2n = {1: 50, 3: 100}
    Rec3n = {1: 9, 2: 80, 3: 96, 4: 128}
    Rec_bad1n = {1: 24, 2: 120}
    Rec_bad2n = {1: 9, 2: 80, 3: 96, 4: 128, 5: 42}
    Rec_bad3n = {1: 'four', 2: 120, 3: 240}
    Rec_bad4n = {'one': 24, 2: 120, 3: 240}

    RGB1c = [24, 120, 240]                           # Encoded values Record (concise)
    RGB2c = [50, None, 100]
    RGB3c = [9, 80, 96, 128]
    RGB_bad1c = [24, 120]
    RGB_bad2c = [9, 80, 96, 128, 42]
    RGB_bad3c = ['four', 120, 240]

    def test_map_min(self):             # dict structure, identifier tag
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB1), self.Map1m)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.Map1m), self.RGB1)
        self.assertDictEqual(self.tc.decode('T-map-rgba', _j(self.Map1m)), self.RGB1)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB2), self.Map2m)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.Map2m), self.RGB2)
        self.assertDictEqual(self.tc.decode('T-map-rgba', _j(self.Map2m)), self.RGB2)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB3), self.Map3m)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.Map3m), self.RGB3)
        self.assertDictEqual(self.tc.decode('T-map-rgba', _j(self.Map3m)), self.RGB3)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad1m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad2m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad3m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad4m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad5m)

    def test_map_unused(self):         # dict structure, identifier tag
        self.tc.set_mode(verbose_rec=True, verbose_str=False)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB1), self.Map1m)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.Map1m), self.RGB1)
        self.assertDictEqual(self.tc.decode('T-map-rgba', _j(self.Map1m)), self.RGB1)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB2), self.Map2m)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.Map2m), self.RGB2)
        self.assertDictEqual(self.tc.decode('T-map-rgba', _j(self.Map2m)), self.RGB2)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB3), self.Map3m)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.Map3m), self.RGB3)
        self.assertDictEqual(self.tc.decode('T-map-rgba', _j(self.Map3m)), self.RGB3)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad1m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad2m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad3m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.Map_bad4m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', _j(self.Map_bad4m))

    def test_map_concise(self):         # dict structure, identifier name
        self.tc.set_mode(verbose_rec=False, verbose_str=True)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB1), self.RGB1)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.RGB1), self.RGB1)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB2), self.RGB2)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.RGB2), self.RGB2)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB3), self.RGB3)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.RGB3), self.RGB3)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad7a)

    def test_map_verbose(self):     # dict structure, identifier name
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB1), self.RGB1)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.RGB1), self.RGB1)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB2), self.RGB2)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.RGB2), self.RGB2)
        self.assertDictEqual(self.tc.encode('T-map-rgba', self.RGB3), self.RGB3)
        self.assertDictEqual(self.tc.decode('T-map-rgba', self.RGB3), self.RGB3)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-map-rgba', self.RGB_bad8a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-map-rgba', self.RGB_bad8a)

    def test_record_min(self):
        self.assertListEqual(self.tc.encode('T-rec-rgba', self.RGB1), self.Rec1m)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.Rec1m), self.RGB1)
        self.assertListEqual(self.tc.encode('T-rec-rgba', self.RGB2), self.Rec2m)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.Rec2m), self.RGB2)
        self.assertListEqual(self.tc.encode('T-rec-rgba', self.RGB3), self.Rec3m)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.Rec3m), self.RGB3)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.Rec_bad1m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.Rec_bad2m)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.Rec_bad3m)

    def test_record_unused(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=False)
        self.assertDictEqual(self.tc.encode('T-rec-rgba', self.RGB1), self.Rec1n)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.Rec1n), self.RGB1)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', _j(self.Rec1n)), self.RGB1)
        self.assertDictEqual(self.tc.encode('T-rec-rgba', self.RGB2), self.Rec2n)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.Rec2n), self.RGB2)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', _j(self.Rec2n)), self.RGB2)
        self.assertDictEqual(self.tc.encode('T-rec-rgba', self.RGB3), self.Rec3n)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.Rec3n), self.RGB3)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', _j(self.Rec3n)), self.RGB3)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.Rec_bad1n)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.Rec_bad2n)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.Rec_bad3n)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.Rec_bad4n)

    def test_record_concise(self):
        self.tc.set_mode(verbose_rec=False, verbose_str=True)
        self.assertListEqual(self.tc.encode('T-rec-rgba', self.RGB1), self.RGB1c)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.RGB1c), self.RGB1)
        self.assertListEqual(self.tc.encode('T-rec-rgba', self.RGB2), self.RGB2c)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.RGB2c), self.RGB2)
        self.assertListEqual(self.tc.encode('T-rec-rgba', self.RGB3), self.RGB3c)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.RGB3c), self.RGB3)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad1c)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad2c)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad3c)

    def test_record_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('T-rec-rgba', self.RGB1), self.RGB1)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.RGB1), self.RGB1)
        self.assertDictEqual(self.tc.encode('T-rec-rgba', self.RGB2), self.RGB2)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.RGB2), self.RGB2)
        self.assertDictEqual(self.tc.encode('T-rec-rgba', self.RGB3), self.RGB3)
        self.assertDictEqual(self.tc.decode('T-rec-rgba', self.RGB3), self.RGB3)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-rec-rgba', self.RGB_bad8a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad2a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad4a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad5a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad6a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad7a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-rec-rgba', self.RGB_bad8a)

    Arr1 = [None, 3, 2]
    Arr2 = [True, 3, 2.71828, 'Red']
    Arr3 = [True, 3, 2, 'Red', [1, 'Blue'], [2, 3]]
    Arr4 = [True, 3, 2.71828, None, [1, 'Blue'], [2, 3]]
    Arr5 = [True, 3, 2.71828, 'Red', None, []]
    Arr_bad1 = [True, 3, None, 'Red']                   # Third element is required
    Arr_bad2 = [True, 3, False, 'Red']                  # Third element is Number
    Arr_bad3 = [True, 3, 2.71828, 'Red', []]            # Optional arrays are omitted, not empty

    def test_array(self):

        def ta():
            self.assertListEqual(self.tc.encode('T-array', self.Arr1), self.Arr1)
            self.assertListEqual(self.tc.decode('T-array', self.Arr1), self.Arr1)
            self.assertListEqual(self.tc.encode('T-array', self.Arr2), self.Arr2)
            self.assertListEqual(self.tc.decode('T-array', self.Arr2), self.Arr2)
            self.assertListEqual(self.tc.encode('T-array', self.Arr3), self.Arr3)
            self.assertListEqual(self.tc.decode('T-array', self.Arr3), self.Arr3)
            self.assertListEqual(self.tc.encode('T-array', self.Arr4), self.Arr4)
            self.assertListEqual(self.tc.decode('T-array', self.Arr4), self.Arr4)
            self.assertListEqual(self.tc.encode('T-array', self.Arr5), self.Arr5)
            self.assertListEqual(self.tc.decode('T-array', self.Arr5), self.Arr5)
            with self.assertRaises(ValueError):
                self.tc.encode('T-array', self.Arr_bad1)
            with self.assertRaises(ValueError):
                self.tc.decode('T-array', self.Arr_bad1)
            with self.assertRaises(ValueError):
                self.tc.encode('T-array', self.Arr_bad2)
            with self.assertRaises(ValueError):
                self.tc.decode('T-array', self.Arr_bad2)
            with self.assertRaises(ValueError):
                self.tc.encode('T-array', self.Arr_bad3)
            with self.assertRaises(ValueError):
                self.tc.decode('T-array', self.Arr_bad3)

            self.assertListEqual(self.tc.encode('T-arr-rgba', self.Rec1m), self.Rec1m)
            self.assertListEqual(self.tc.decode('T-arr-rgba', self.Rec1m), self.Rec1m)
            self.assertListEqual(self.tc.encode('T-arr-rgba', self.Rec2m), self.Rec2m)
            self.assertListEqual(self.tc.decode('T-arr-rgba', self.Rec2m), self.Rec2m)
            self.assertListEqual(self.tc.encode('T-arr-rgba', self.Rec3m), self.Rec3m)
            self.assertListEqual(self.tc.decode('T-arr-rgba', self.Rec3m), self.Rec3m)
            with self.assertRaises(ValueError):
                self.tc.encode('T-arr-rgba', self.Rec_bad1m)
            with self.assertRaises(ValueError):
                self.tc.decode('T-arr-rgba', self.Rec_bad1m)
            with self.assertRaises(ValueError):
                self.tc.encode('T-arr-rgba', self.Rec_bad2m)
            with self.assertRaises(ValueError):
                self.tc.decode('T-arr-rgba', self.Rec_bad2m)
            with self.assertRaises(ValueError):
                self.tc.encode('T-arr-rgba', self.Rec_bad3m)
            with self.assertRaises(ValueError):
                self.tc.decode('T-arr-rgba', self.Rec_bad3m)

        # Ensure that mode has no effect on array serialization

        self.tc.set_mode(verbose_rec=False, verbose_str=False)
        ta()
        self.tc.set_mode(verbose_rec=False, verbose_str=True)
        ta()
        self.tc.set_mode(verbose_rec=True, verbose_str=False)
        ta()
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        ta()


class Compound(unittest.TestCase):  # TODO: arrayOf(rec,map,array,arrayof,choice), array(), map(), rec()
    schema = {
        'types': [
            ['T-choice', 'Choice', [], '', [
                [10, 'rec', 'T-crec', [], ''],
                [11, 'map', 'T-cmap', [], ''],
                [12, 'array', 'T-carray', [], ''],
                [13, 'choice', 'T-cchoice', [], '']
            ]],
            ['T-crec', 'Record', [], '', [
                [1, 'a', 'Integer', [], ''],
                [2, 'b', 'String', [], '']
            ]],
            ['T-cmap', 'Map', [], '', [
                [4, 'c', 'Integer', [], ''],
                [6, 'd', 'String', [], '']
            ]],
            ['T-carray', 'Array', [], '', [
                [1, 'e', 'Integer', [], ''],
                [2, 'f', 'String', [], '']
            ]],
            ['T-cchoice', 'Choice', [], '', [
                [7, 'g', 'Integer', [], ''],
                [8, 'h', 'String', [], '']
            ]],
        ]}

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.codec.Codec(self.schema)

    C4a = {'rec': {'a': 1, 'b': 'c'}}
    C4m = {10: [1, 'c']}

    def test_choice_rec_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertEqual(self.tc.decode('T-choice', self.C4a), self.C4a)
        self.assertEqual(self.tc.encode('T-choice', self.C4a), self.C4a)

    def test_choice_rec_min(self):
        self.tc.set_mode(verbose_rec=False, verbose_str=False)
        self.assertEqual(self.tc.decode('T-choice', self.C4m), self.C4a)
        self.assertEqual(self.tc.encode('T-choice', self.C4a), self.C4m)


class Selectors(unittest.TestCase):         # TODO: bad schema - verify * field has only Choice type
                                            # TODO: add test cases to decode multiple values for Choice (bad)
    schema = {  # JADN schema for selector tests
        'types': [
            ['T-attr-arr-tag', 'Array', [], '', [
                [1, 'type', 'Enumerated', ['#MenuId', '='], ''],    # ID not propogated from MenuId
                [2, 'value', 'MenuId', ['&1'], '']
            ]],
            ['T-attr-arr-name', 'Array', [], '', [
                [1, 'type', 'Enumerated', ['#Menu'], ''],
                [2, 'value', 'Menu', ['&1'], '']
            ]],
            ['T-attr-rec-name', 'Record', [], '', [
                [1, 'type', 'Enumerated', ['#Menu'], ''],
                [2, 'value', 'Menu', ['&1'], '']
            ]],
            ['T-property-explicit-primitive', 'Record', [], '', [
                [1, 'foo', 'String', [], ''],
                [2, 'data', 'Primitive', [], '']
            ]],
            ['T-property-explicit-category', 'Record', [], '', [
                [1, 'foo', 'String', [], ''],
                [2, 'data', 'Category', [], '']
            ]],
            ['Menu', 'Choice', [], '', [
                [9, 'name', 'String', [], ''],
                [4, 'flag', 'Boolean', [], ''],
                [7, 'count', 'Integer', [], ''],
                [6, 'color', 'Colors', [], ''],
                [5, 'animal', 'Animals', [], ''],
                [10, 'rattr', 'Rattrs', [], ''],
                [11, 'rattrs', 'Rattrs', [']0'], ''],
                [12, 'pair', 'Pair', [], ''],
                [13, 'pairs', 'Pair', [']0'], '']
            ]],
            ['MenuId', 'Choice', ['='], '', [
                [9, 'name', 'String', [], ''],
                [4, 'flag', 'Boolean', [], ''],
                [7, 'count', 'Integer', [], ''],
                [6, 'color', 'Colors', [], ''],
                [5, 'animal', 'Animals', [], ''],
                [10, 'rattr', 'Rattrs', [], ''],
                [11, 'rattrs', 'Rattrs', [']0'], ''],
                [12, 'pair', 'Pair', [], ''],
                [13, 'pairs', 'Pair', [']0'], '']
            ]],
            ['Primitive', 'Choice', [], '', [
                [1, 'name', 'String', [], ''],
                [4, 'flag', 'Boolean', [], ''],
                [7, 'count', 'Integer', [], '']
            ]],
            ['Category', 'Choice', [], '', [
                [2, 'animal', 'Animals', [], ''],
                [6, 'color', 'Colors', [], '']
            ]],
            ['Animals', 'Map', [], '', [
                [3, 'cat', 'String', ['[0'], ''],
                [4, 'dog', 'Integer', ['[0'], ''],
                [5, 'rat', 'Rattrs', ['[0'], '']
            ]],
            ['Colors', 'Enumerated', [], '', [
                [2, 'red', ''],
                [3, 'green', ''],
                [4, 'blue', '']
            ]],
            ['Rattrs', 'Record', [], '', [
                [1, 'length', 'Integer', [], ''],
                [2, 'weight', 'Number', [], '']
            ]],
            ['Pair', 'Array', [], '', [
                [1, 'count', 'Integer', [], ''],
                [2, 'name', 'String', [], '']
            ]]
        ]}

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.codec.Codec(self.schema)

    arr_name1_api = ['count', 17]
    arr_name2_api = ['color', 'green']
    arr_name3_api = ['animal', {'cat': 'Fluffy'}]
    arr_name4_bad_api = ['name', 17]        # name is type String, not Integer
    arr_name5_bad_api = ['universe', 17]    # universe is not a defined type
    # arr_names1_api = ['count', [13, 17]]    # array of values of the specified type
    arr_name_a1_api = ['rattr', {'length': 4, 'weight': 5.6}]
    arr_names_a1_api = ['rattrs', [{'length': 4, 'weight': 5.6}, {'length': 7, 'weight': 8.9}]]
    arr_names_a2_api = ['rattr', [{'length': 4, 'weight': 5.6}, {'length': 7, 'weight': 8.9}]]
    arr_name_p1_api = ['pair', [1, 'rug']]
    arr_names_p1_api = ['pairs', [[3, 'rug'], [2, 'clock']]]
    arr_names_p2_api = ['pair', [[3, 'rug'], [2, 'clock']]]

    arr_tag1_api = [7, 17]                  # enumerated tag values are integers
    arr_tag2_api = [6, 'green']
    arr_tag3_api = [5, {'cat': 'Fluffy'}]
    arr_tag4_bad_api = [9, 17]              # name is type String, not Integer
    arr_tag5_bad_api = [2, 17]              # 2 is not a defined type
    arr_tags1_api = [7, [13, 17]]           # array of values of the specified type

    arr_name1_min = [7, 17]                 # Enumerated type with 'id' option always uses min encoding (tag)
    arr_name2_min = [6, 3]
    arr_name3_min = [5, {3: 'Fluffy'}]      # min encoding of map (serialized keys are strings)
    arr_name4_bad_min = [9, 17]
    arr_name5_bad_min = [2, 17]

    arr_tag1_min = arr_name1_min
    arr_tag2_min = arr_name2_min
    arr_tag3_min = arr_name3_min
    arr_tag4_bad_min = arr_name4_bad_min
    arr_tag5_bad_min = arr_name5_bad_min

    def test_attr_arr_name_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_name1_api), self.arr_name1_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_name1_api), self.arr_name1_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_name2_api), self.arr_name2_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_name2_api), self.arr_name2_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_name3_api), self.arr_name3_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_name3_api), self.arr_name3_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_name_a1_api), self.arr_name_a1_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_name_a1_api), self.arr_name_a1_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_names_a1_api), self.arr_names_a1_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_names_a1_api), self.arr_names_a1_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_name_p1_api), self.arr_name_p1_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_name_p1_api), self.arr_name_p1_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_names_p1_api), self.arr_names_p1_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_names_p1_api), self.arr_names_p1_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-arr-name', self.arr_name4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-arr-name', self.arr_name4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-arr-name', self.arr_name5_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-arr-name', self.arr_name5_bad_api)

    def test_attr_arr_tag_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertListEqual(self.tc.encode('T-attr-arr-tag', self.arr_tag1_api), self.arr_tag1_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-tag', self.arr_tag1_api), self.arr_tag1_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-tag', self.arr_tag2_api), self.arr_tag2_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-tag', self.arr_tag2_api), self.arr_tag2_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-tag', self.arr_tag3_api), self.arr_tag3_api)
        self.assertListEqual(self.tc.decode('T-attr-arr-tag', self.arr_tag3_api), self.arr_tag3_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-arr-tag', self.arr_tag4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-arr-tag', self.arr_tag4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-arr-tag', self.arr_tag5_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-arr-tag', self.arr_tag5_bad_api)

    def test_attr_arr_name_min(self):
        self.tc.set_mode(verbose_rec=False, verbose_str=False)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_name1_api), self.arr_name1_min)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_name1_min), self.arr_name1_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_name2_api), self.arr_name2_min)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_name2_min), self.arr_name2_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-name', self.arr_name3_api), self.arr_name3_min)
        self.assertListEqual(self.tc.decode('T-attr-arr-name', self.arr_name3_min), self.arr_name3_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-arr-name', self.arr_name4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-arr-name', self.arr_name4_bad_min)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-arr-name', self.arr_name5_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-arr-name', self.arr_name5_bad_min)

    def test_attr_arr_tag_min(self):
        self.tc.set_mode(verbose_rec=False, verbose_str=False)
        self.assertListEqual(self.tc.encode('T-attr-arr-tag', self.arr_tag1_api), self.arr_tag1_min)
        self.assertListEqual(self.tc.decode('T-attr-arr-tag', self.arr_tag1_min), self.arr_tag1_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-tag', self.arr_tag2_api), self.arr_tag2_min)
        self.assertListEqual(self.tc.decode('T-attr-arr-tag', self.arr_tag2_min), self.arr_tag2_api)
        self.assertListEqual(self.tc.encode('T-attr-arr-tag', self.arr_tag3_api), self.arr_tag3_min)
        self.assertListEqual(self.tc.decode('T-attr-arr-tag', self.arr_tag3_min), self.arr_tag3_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-arr-tag', self.arr_tag4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-arr-tag', self.arr_tag4_bad_min)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-arr-tag', self.arr_tag5_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-arr-tag', self.arr_tag5_bad_min)

    rec_name1_api = {'type': 'count', 'value': 17}
    rec_name2_api = {'type': 'color', 'value': 'green'}
    rec_name3_api = {'type': 'animal', 'value': {'cat': 'Fluffy'}}
    rec_name4_bad_api = {'type': 'name', 'value': 17}
    rec_name5_bad_api = {'type': 'universe', 'value': 'Fred'}

    rec_name1_min = arr_name1_min
    rec_name2_min = arr_name2_min
    rec_name3_min = arr_name3_min
    rec_name4_bad_min = arr_name4_bad_min
    rec_name5_bad_min = arr_name5_bad_min

    """
    rec_name1_min = ['Integer', 17]
    rec_name2_min = ['Primitive', {'7': 17}]
    rec_name3_min = ['Category', {'2': {'5': [21, 0.342]}}]
    rec_name4_bad_min = ['Vegetable', {'7': 17}]
    rec_name5_bad_min = ['Category', {'2': {'9': 10}}]
    """

    def test_attr_rec_name_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('T-attr-rec-name', self.rec_name1_api), self.rec_name1_api)
        self.assertDictEqual(self.tc.decode('T-attr-rec-name', self.rec_name1_api), self.rec_name1_api)
        self.assertDictEqual(self.tc.encode('T-attr-rec-name', self.rec_name2_api), self.rec_name2_api)
        self.assertDictEqual(self.tc.decode('T-attr-rec-name', self.rec_name2_api), self.rec_name2_api)
        self.assertDictEqual(self.tc.encode('T-attr-rec-name', self.rec_name3_api), self.rec_name3_api)
        self.assertDictEqual(self.tc.decode('T-attr-rec-name', self.rec_name3_api), self.rec_name3_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-rec-name', self.rec_name4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-rec-name', self.rec_name4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-rec-name', self.rec_name5_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-rec-name', self.rec_name5_bad_api)

    def test_attr_rec_name_min(self):
        self.tc.set_mode(verbose_rec=False, verbose_str=False)
        self.assertListEqual(self.tc.encode('T-attr-rec-name', self.rec_name1_api), self.rec_name1_min)
        self.assertDictEqual(self.tc.decode('T-attr-rec-name', self.rec_name1_min), self.rec_name1_api)
        self.assertListEqual(self.tc.encode('T-attr-rec-name', self.rec_name2_api), self.rec_name2_min)
        self.assertDictEqual(self.tc.decode('T-attr-rec-name', self.rec_name2_min), self.rec_name2_api)
        self.assertListEqual(self.tc.encode('T-attr-rec-name', self.rec_name3_api), self.rec_name3_min)
        self.assertDictEqual(self.tc.decode('T-attr-rec-name', self.rec_name3_min), self.rec_name3_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-rec-name', self.rec_name4_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-rec-name', self.rec_name4_bad_min)
        with self.assertRaises(ValueError):
            self.tc.encode('T-attr-rec-name', self.rec_name5_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-attr-rec-name', self.rec_name5_bad_min)

    pep_api = {'foo': 'bar', 'data': {'count': 17}}
    pec_api = {'foo': 'bar', 'data': {'animal': {'rat': {'length': 21, 'weight': .342}}}}
    pep_bad_api = {'foo': 'bar', 'data': {'turnip': ''}}

    def test_property_explicit_verbose(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('T-property-explicit-primitive', self.pep_api), self.pep_api)
        self.assertDictEqual(self.tc.decode('T-property-explicit-primitive', self.pep_api), self.pep_api)
        self.assertDictEqual(self.tc.encode('T-property-explicit-category', self.pec_api), self.pec_api)
        self.assertDictEqual(self.tc.decode('T-property-explicit-category', self.pec_api), self.pec_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-property-explicit-primitive', self.pep_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-property-explicit-primitive', self.pep_bad_api)

    pep_min = ['bar', {7: 17}]
    pec_min = ['bar', {2: {5: [21, 0.342]}}]
    pep_bad_min = ['bar', {'6': 17}]

    def test_property_explicit_min(self):
        self.tc.set_mode(verbose_rec=False, verbose_str=False)
        self.assertListEqual(self.tc.encode('T-property-explicit-primitive', self.pep_api), self.pep_min)
        self.assertDictEqual(self.tc.decode('T-property-explicit-primitive', self.pep_min), self.pep_api)
        self.assertListEqual(self.tc.encode('T-property-explicit-category', self.pec_api), self.pec_min)
        self.assertDictEqual(self.tc.decode('T-property-explicit-category', self.pec_min), self.pec_api)
        with self.assertRaises(ValueError):
            self.tc.encode('T-property-explicit-primitive', self.pep_bad_api)
        with self.assertRaises(ValueError):
            self.tc.decode('T-property-explicit-primitive', self.pep_bad_min)


class ListCardinality(unittest.TestCase):      # TODO: arrayOf(rec,map,array,arrayof,choice), array(), map(), rec()
    schema = {  # JADN schema for fields with cardinality > 1 (e.g., list of x)
        'types': [
            ['T-array0', 'ArrayOf', ['*String', '}2'], ''],         # Min array length = 0 (default), Max = 2
            ['T-array1', 'ArrayOf', ['*String', '{1', '}2'], ''],   # Min array length = 1, Max = 2
            ['T-opt-list0', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'T-array0', ['[0'], '']  # Min = 0, Max default = 1 (Array is optional)
            ]],
            ['T-opt-list1', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'T-array1', ['[0'], '']  # Min = 0, Max default = 1 (Array is optional)
            ]],
            ['T-list-1-2', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'String', [']2'], '']  # Min default = 1, Max = 2
            ]],
            ['T-list-0-2', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'String', ['[0', ']2'], '']  # Min = 0, Max = 2 (Array is optional, empty is invalid)
            ]],
            ['T-list-2-3', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'String', ['[2', ']3'], '']  # Min = 2, Max = 3
            ]],
            ['T-list-1-n', 'Record', [], '', [
                [1, 'string', 'String', [], ''],
                [2, 'list', 'String', [']0'], '']  # Min default = 1, Max = 0 -> n
            ]]
        ]}

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.codec.Codec(self.schema)

    Lna = {'string': 'cat'}                     # Cardinality 0..n field omits empty list.  Use ArrayOf type to send empty list.
    Lsa = {'string': 'cat', 'list': 'red'}      # Always invalid, value is a string, not a list of one string.
    L0a = {'string': 'cat', 'list': []}         # Arrays SHOULD have minimum cardinality 1 to prevent ambiguity.
    L1a = {'string': 'cat', 'list': ['red']}
    L2a = {'string': 'cat', 'list': ['red', 'green']}
    L3a = {'string': 'cat', 'list': ['red', 'green', 'blue']}

    def test_opt_list0_verbose(self):        # n-P, s-F, 0-P, 1-P, 2-P, 3-F
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('T-opt-list0', self.Lna), self.Lna)
        self.assertDictEqual(self.tc.decode('T-opt-list0', self.Lna), self.Lna)
        with self.assertRaises(ValueError):
            self.tc.encode('T-opt-list0', self.Lsa)
        with self.assertRaises(ValueError):
            self.tc.decode('T-opt-list0', self.Lsa)
        self.assertDictEqual(self.tc.encode('T-opt-list0', self.L0a), self.L0a)
        self.assertDictEqual(self.tc.decode('T-opt-list0', self.L0a), self.L0a)
        self.assertDictEqual(self.tc.encode('T-opt-list0', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.decode('T-opt-list0', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.encode('T-opt-list0', self.L2a), self.L2a)
        self.assertDictEqual(self.tc.decode('T-opt-list0', self.L2a), self.L2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-opt-list0', self.L3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-opt-list0', self.L3a)

    def test_opt_list1_verbose(self):        # n-P, s-F, 0-F, 1-P, 2-P, 3-F
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('T-opt-list1', self.Lna), self.Lna)
        self.assertDictEqual(self.tc.decode('T-opt-list1', self.Lna), self.Lna)
        with self.assertRaises(ValueError):
            self.tc.encode('T-opt-list1', self.Lsa)
        with self.assertRaises(ValueError):
            self.tc.decode('T-opt-list1', self.Lsa)
        with self.assertRaises(ValueError):
            self.tc.encode('T-opt-list1', self.L0a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-opt-list1', self.L0a)
        self.assertDictEqual(self.tc.encode('T-opt-list1', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.decode('T-opt-list1', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.encode('T-opt-list1', self.L2a), self.L2a)
        self.assertDictEqual(self.tc.decode('T-opt-list1', self.L2a), self.L2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-opt-list1', self.L3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-opt-list1', self.L3a)

    def test_list_1_2_verbose(self):        # n-F, s-F, 0-F, 1-P, 2-P, 3-F
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-1-2', self.Lna)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-1-2', self.Lna)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-1-2', self.Lsa)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-1-2', self.Lsa)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-1-2', self.L0a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-1-2', self.L0a)
        self.assertDictEqual(self.tc.encode('T-list-1-2', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.decode('T-list-1-2', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.encode('T-list-1-2', self.L2a), self.L2a)
        self.assertDictEqual(self.tc.decode('T-list-1-2', self.L2a), self.L2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-1-2', self.L3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-1-2', self.L3a)

    def test_list_0_2_verbose(self):        # n-P, s-F, 0-F, 1-P, 2-P, 3-F
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('T-list-0-2', self.Lna), self.Lna)
        self.assertDictEqual(self.tc.decode('T-list-0-2', self.Lna), self.Lna)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-0-2', self.Lsa)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-0-2', self.Lsa)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-0-2', self.L0a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-0-2', self.L0a)
        self.assertDictEqual(self.tc.encode('T-list-0-2', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.decode('T-list-0-2', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.encode('T-list-0-2', self.L2a), self.L2a)
        self.assertDictEqual(self.tc.decode('T-list-0-2', self.L2a), self.L2a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-0-2', self.L3a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-0-2', self.L3a)

    def test_list_2_3_verbose(self):        # n-F, 0-F, 1-F, 2-P, 3-P
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-2-3', self.Lna)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-2-3', self.Lna)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-2-3', self.L0a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-2-3', self.L0a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-2-3', self.L1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-2-3', self.L1a)
        self.assertDictEqual(self.tc.encode('T-list-2-3', self.L2a), self.L2a)
        self.assertDictEqual(self.tc.decode('T-list-2-3', self.L2a), self.L2a)
        self.assertDictEqual(self.tc.encode('T-list-2-3', self.L3a), self.L3a)
        self.assertDictEqual(self.tc.decode('T-list-2-3', self.L3a), self.L3a)

    def test_list_1_n_verbose(self):        # n-F, 0-F, 1-P, 2-P, 3-P
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-1-n', self.Lna)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-1-n', self.Lna)
        with self.assertRaises(ValueError):
            self.tc.encode('T-list-1-n', self.L0a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-list-1-n', self.L0a)
        self.assertDictEqual(self.tc.encode('T-list-1-n', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.decode('T-list-1-n', self.L1a), self.L1a)
        self.assertDictEqual(self.tc.encode('T-list-1-n', self.L2a), self.L2a)
        self.assertDictEqual(self.tc.decode('T-list-1-n', self.L2a), self.L2a)
        self.assertDictEqual(self.tc.encode('T-list-1-n', self.L3a), self.L3a)
        self.assertDictEqual(self.tc.decode('T-list-1-n', self.L3a), self.L3a)


class ListTypes(unittest.TestCase):
    schema = {
        'types': [
            ['T-list', 'ArrayOf', ['*T-list-types'], ''],
            ['T-list-types', 'Record', [], '', [
                [1, 'bins', 'Binary', ['[0', ']2'], ''],
                [2, 'bools', 'Boolean', ['[0', ']2'], ''],
                [3, 'ints', 'Integer', ['[0', ']2'], ''],
                [4, 'strs', 'String', ['[0', ']2'], ''],
                [5, 'arrs', 'T-arr', ['[0', ']2'], ''],
                [6, 'aro_s', 'T-aro-s', ['[0', ']2'], ''],
                [7, 'aro_ch', 'T-aro-ch', ['[0', ']2'], ''],
                [8, 'choices', 'T-ch', ['[0', ']2'], ''],
                [9, 'enums', 'T-enum', ['[0', ']2'], ''],
                [10, 'maps', 'T-map', ['[0', ']2'], ''],
                [11, 'recs', 'T-rec', ['[0', ']2'], '']
            ]],
            ['T-arr', 'Array', [], '', [
                [1, 'x', 'Integer', [], ''],
                [2, 'y', 'Number', [], '']
            ]],
            ['T-aro-s', 'ArrayOf', ['*String'], ''],
            ['T-aro-ch', 'ArrayOf', ['*t_ch'], ''],
            ['T-ch', 'Choice', [], '', [
                [1, 'red', 'Integer', [], ''],
                [2, 'blue', 'Integer', [], '']
            ]],
            ['T-enum', 'Enumerated', [], '', [
                [1, 'heads', ''],
                [2, 'tails', '']
            ]],
            ['T-map', 'Map', [], '', [
                [1, 'red', 'Integer', [], ''],
                [2, 'blue', 'Integer', [], '']
            ]],
            ['T-rec', 'Record', [], '', [
                [1, 'red', 'Integer', [], ''],
                [2, 'blue', 'Integer', [], '']
            ]]
        ]}

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.codec.Codec(self.schema)

    prims = [{
            'bools': [True],
            'ints': [1, 2]
        },
        {'strs': ['cat', 'dog']}
    ]
    enums = [
        {'enums': ['heads', 'tails']},
        {'enums': ['heads']},
        {'enums': ['heads']},
        {'enums': ['tails']},
        {'enums': ['heads']},
        {'enums': ['tails']}
    ]

    def test_list_primitives(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertListEqual(self.tc.encode('T-list', self.prims), self.prims)
        self.assertListEqual(self.tc.decode('T-list', self.prims), self.prims)
        self.assertListEqual(self.tc.encode('T-list', self.enums), self.enums)
        self.assertListEqual(self.tc.decode('T-list', self.enums), self.enums)


class Bounds(unittest.TestCase):        # TODO: check max and min string length, integer and number values, array sizes
                                        # TODO: Schema default and options
                                        # TODO: Array count for concise Records
    schema = {
        'types': [
            ['Int', 'Integer', [], ''],
            ['Num', 'Number', [], ''],
            ['Int-3-6', 'Integer', ['{3', '}6'], ''],
            ['Num-3-6', 'Number', ['y3.0', 'z6.0'], ''],
            ['T-Map23', 'Map', ['{2', '}3'], '', [
                [2, 'red', 'Integer', ['[0'], ''],
                [4, 'green', 'Integer', ['[0'], ''],
                [6, 'blue', 'Integer', ['[0'], ''],
                [9, 'alpha', 'Integer', [], '']
            ]],
            ['T-Arr23', 'Array', ['{2', '}3'], '', [
                [1, 'red', 'Integer', ['[0'], ''],
                [2, 'green', 'Integer', ['[0'], ''],
                [3, 'blue', 'Integer', ['[0'], ''],
                [4, 'alpha', 'Integer', [], '']
            ]],
            ['T-Rec23', 'Record', ['{2', '}3'], '', [
                [1, 'red', 'Integer', ['[0'], ''],
                [2, 'green', 'Integer', ['[0'], ''],
                [3, 'blue', 'Integer', ['[0'], ''],
                [4, 'alpha', 'Integer', [], '']
            ]]
        ]
    }

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.codec.Codec(self.schema, verbose_rec=True, verbose_str=True)

    i1 = 1
    i5 = 5
    i9 = 9
    f1 = 1.0
    f5 = 5.5
    f9 = 9.8

    def test_int(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertEqual(self.tc.encode('Int', self.i1), self.i1)
        self.assertEqual(self.tc.decode('Int', self.i1), self.i1)
        self.assertEqual(self.tc.encode('Int', self.i5), self.i5)
        self.assertEqual(self.tc.decode('Int', self.i5), self.i5)
        self.assertEqual(self.tc.encode('Int', self.i9), self.i9)
        self.assertEqual(self.tc.decode('Int', self.i9), self.i9)
        self.assertEqual(self.tc.encode('Int-3-6', self.i5), self.i5)
        self.assertEqual(self.tc.decode('Int-3-6', self.i5), self.i5)
        with self.assertRaises(ValueError):
            self.tc.encode('Int-3-6', self.i1)
        with self.assertRaises(ValueError):
            self.tc.encode('Int-3-6', self.i9)

    def test_num(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertEqual(self.tc.encode('Num', self.f1), self.f1)
        self.assertEqual(self.tc.decode('Num', self.f1), self.f1)
        self.assertEqual(self.tc.encode('Num', self.f5), self.f5)
        self.assertEqual(self.tc.decode('Num', self.f5), self.f5)
        self.assertEqual(self.tc.encode('Num', self.f9), self.f9)
        self.assertEqual(self.tc.decode('Num', self.f9), self.f9)
        self.assertEqual(self.tc.encode('Num-3-6', self.f5), self.f5)
        self.assertEqual(self.tc.decode('Num-3-6', self.f5), self.f5)
        with self.assertRaises(ValueError):
            self.tc.encode('Num-3-6', self.f1)
        with self.assertRaises(ValueError):
            self.tc.encode('Num-3-6', self.f9)

    a0 = []
    a1 = [30]
    a1a = [None, None, None, 24]
    a2a = [6, None, None, 16]
    a3a = [None, 5, 8, 15]
    a4a = [9, 12, 14, 20]

    d0 = {}
    d1 = {'red': 30}
    d1a = {'alpha': 24}
    d2a = {'red': 6, 'alpha': 16}
    d3a = {'green': 5, 'blue': 8, 'alpha': 15}
    d4a = {'red': 9, 'green': 12, 'blue': 14, 'alpha': 20}

    def test_array23(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Arr23', self.a0)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Arr23', self.a0)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Arr23', self.a1)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Arr23', self.a1)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Arr23', self.a1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Arr23', self.a1a)
        self.assertEqual(self.tc.encode('T-Arr23', self.a2a), self.a2a)
        self.assertEqual(self.tc.decode('T-Arr23', self.a2a), self.a2a)
        self.assertEqual(self.tc.encode('T-Arr23', self.a3a), self.a3a)
        self.assertEqual(self.tc.decode('T-Arr23', self.a3a), self.a3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Arr23', self.a4a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Arr23', self.a4a)

    def test_map23(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Map23', self.d0)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Map23', self.d0)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Map23', self.d1)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Map23', self.d1)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Map23', self.d1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Map23', self.d1a)
        self.assertEqual(self.tc.encode('T-Map23', self.d2a), self.d2a)
        self.assertEqual(self.tc.decode('T-Map23', self.d2a), self.d2a)
        self.assertEqual(self.tc.encode('T-Map23', self.d3a), self.d3a)
        self.assertEqual(self.tc.decode('T-Map23', self.d3a), self.d3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Map23', self.d4a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Map23', self.d4a)

    def test_rec23(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Rec23', self.d0)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Rec23', self.d0)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Rec23', self.d1)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Rec23', self.d1)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Rec23', self.d1a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Rec23', self.d1a)
        self.assertEqual(self.tc.encode('T-Rec23', self.d2a), self.d2a)
        self.assertEqual(self.tc.decode('T-Rec23', self.d2a), self.d2a)
        self.assertEqual(self.tc.encode('T-Rec23', self.d3a), self.d3a)
        self.assertEqual(self.tc.decode('T-Rec23', self.d3a), self.d3a)
        with self.assertRaises(ValueError):
            self.tc.encode('T-Rec23', self.d4a)
        with self.assertRaises(ValueError):
            self.tc.decode('T-Rec23', self.d4a)


class Format(unittest.TestCase):
    schema = {                          # JADN schema for value constraint tests
        'types': [
            ['IPv4-Bin', 'Binary', ['{4', '}4'], ''],  # Check length = 32 bits with format function
            ['IPv4-Hex', 'Binary', ['{4', '}4', '/X'], ''],  # Check length = 32 bits with min/max size
            ['IPv4-String', 'Binary', ['{4', '}4', '/ipv4-addr'], ''],
            ['IPv6-Base64url', 'Binary', ['{16', '}16'], ''],
            ['IPv6-Hex', 'Binary', ['{16', '}16', '/X'], ''],
            ['IPv6-String', 'Binary', ['{16', '}16', '/ipv6-addr'], ''],
            ['IPv4-Net', 'Array', ['/ipv4-net'], '', [
                [1, 'addr', 'Binary', [], ''],
                [2, 'prefix', 'Integer', [], '']
            ]],
            ['IPv6-Net', 'Array', ['/ipv6-net'], '', [
                [1, 'addr', 'Binary', [], ''],
                [2, 'prefix', 'Integer', [], '']
            ]],
            ['T-ipaddrs', 'ArrayOf', ['*IPv4-Bin'], ''],
            ['MAC-Addr', 'Binary', ['/eui'], ''],
            ['Email-Addr', 'String', ['/email'], ''],
            ['Hostname', 'String', ['/hostname'], ''],
            ['URI', 'String', ['/uri'], ''],
            ['DateTime', 'Integer', ['/datetime-ms'], ''],
            ['Int8', 'Integer', ['/i8'], ''],
            ['Int16', 'Integer', ['/i16'], ''],
            ['Int32', 'Integer', ['/i32'], ''],
            ['Int64', 'Integer', ['/i64'], '']
        ]
    }

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.codec.Codec(self.schema)

    ipv4_b = binascii.a2b_hex('c6020304')           # IPv4 address
    ipv4_s64 = 'xgIDBA'                             # Base64url encoded
    ipv4_sx = 'C6020304'                            # Hex encoded
    ipv4_str = '198.2.3.4'                          # IPv4-string encoded
    ipv4_b1_bad = binascii.a2b_hex('c60203')        # Too short
    ipv4_b2_bad = binascii.a2b_hex('c602030456')    # Too long
    ipv4_s64_bad = 'xgIDBFY'                        # Too long
    ipv4_sx_bad = 'C602030456'                      # Too long
    ipv4_str_bad = '198.2.3.4.56'                   # Too long

    def test_ipv4_addr(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertEqual(self.tc.encode('IPv4-Bin', self.ipv4_b), self.ipv4_s64)
        self.assertEqual(self.tc.decode('IPv4-Bin', self.ipv4_s64), self.ipv4_b)
        self.assertEqual(self.tc.encode('IPv4-Hex', self.ipv4_b), self.ipv4_sx)
        self.assertEqual(self.tc.decode('IPv4-Hex', self.ipv4_sx), self.ipv4_b)
        self.assertEqual(self.tc.encode('IPv4-String', self.ipv4_b), self.ipv4_str)
        self.assertEqual(self.tc.decode('IPv4-String', self.ipv4_str), self.ipv4_b)
        with self.assertRaises(ValueError):
            self.tc.encode('IPv4-Hex', self.ipv4_b1_bad)
        with self.assertRaises(ValueError):
            self.tc.encode('IPv4-Hex', self.ipv4_b1_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('IPv4-Bin', self.ipv4_s64_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('IPv4-Hex', self.ipv4_sx_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('IPv4-String', self.ipv4_str_bad)
        with self.assertRaises(ValueError):
            self.tc.encode('IPv4-Bin', b'')
        with self.assertRaises(ValueError):
            self.tc.decode('IPv4-Bin', '')
        with self.assertRaises(ValueError):
            self.tc.encode('IPv4-Hex', b'')
        with self.assertRaises(ValueError):
            self.tc.decode('IPv4-Hex', '')
        with self.assertRaises(ValueError):
            self.tc.encode('IPv4-String', b'')
        with self.assertRaises(ValueError):
            self.tc.decode('IPv4-String', '')

    ipv4_net_str = '192.168.0.0/20'                     # IPv4 CIDR network address (not class C /24)
    ipv4_net_a = [binascii.a2b_hex('c0a80000'), 20]

    def test_ipv4_net(self):
        self.assertEqual(self.tc.encode('IPv4-Net', self.ipv4_net_a), self.ipv4_net_str)
        self.assertEqual(self.tc.decode('IPv4-Net', self.ipv4_net_str), self.ipv4_net_a)
        # with self.assertRaises(ValueError):
        #    self.tc.encode('IPv4-Net', self.ipv4_net_bad1)

    ipv6_b = binascii.a2b_hex('20010db885a3000000008a2e03707334')   # IPv6 address
    ipv6_s64 = 'IAENuIWjAAAAAIouA3BzNA'                             # Base64 encoded
    ipv6_sx = '20010DB885A3000000008A2E03707334'                    # Hex encoded
    ipv6_str1 = '2001:db8:85a3::8a2e:370:7334'                      # IPv6-string encoded
    ipv6_str2 = '2001:db8:85a3::8a2e:0370:7334'                     # IPv6-string encoded - leading 0
    ipv6_str3 = '2001:db8:85A3::8a2e:370:7334'                      # IPv6-string encoded - uppercase
    ipv6_str4 = '2001:db8:85a3:0::8a2e:370:7334'                    # IPv6-string encoded - zero not compressed

    def test_ipv6_addr(self):
        self.assertEqual(self.tc.encode('IPv6-Base64url', self.ipv6_b), self.ipv6_s64)
        self.assertEqual(self.tc.decode('IPv6-Base64url', self.ipv6_s64), self.ipv6_b)
        self.assertEqual(self.tc.encode('IPv6-Hex', self.ipv6_b), self.ipv6_sx)
        self.assertEqual(self.tc.decode('IPv6-Hex', self.ipv6_sx), self.ipv6_b)
        self.assertEqual(self.tc.encode('IPv6-String', self.ipv6_b), self.ipv6_str1)
        self.assertEqual(self.tc.decode('IPv6-String', self.ipv6_str1), self.ipv6_b)

    ipv6_net_str = '2001:db8:85a3::8a2e:370:7334/64'                # IPv6 network address
    ipv6_net_a = [binascii.a2b_hex('20010db885a3000000008a2e03707334'), 64]

    def test_ipv6_net(self):
        self.assertEqual(self.tc.encode('IPv6-Net', self.ipv6_net_a), self.ipv6_net_str)
        self.assertEqual(self.tc.decode('IPv6-Net', self.ipv6_net_str), self.ipv6_net_a)

    eui48b = binascii.a2b_hex('002186b56e10')
    eui48s = '002186b56e10'.upper()
    eui64b = binascii.a2b_hex('022186fffeb56e10')
    eui64s = '022186fffeb56e10'.upper()
    eui48b_bad = binascii.a2b_hex('0226fffeb56e10')
    eui48s_bad = '0226fffeb56e10'.upper()

    def test_mac_addr(self):
        self.assertEqual(self.tc.encode('MAC-Addr', self.eui48b), self.eui48s)
        self.assertEqual(self.tc.decode('MAC-Addr', self.eui48s), self.eui48b)
        self.assertEqual(self.tc.encode('MAC-Addr', self.eui64b), self.eui64s)
        self.assertEqual(self.tc.decode('MAC-Addr', self.eui64s), self.eui64b)
        with self.assertRaises(ValueError):
            self.tc.encode('MAC-Base64url', self.eui48b_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('MAC-Base64url', self.eui48s_bad)

    email1s = 'fred@foo.com'
    email2s_bad = 'https://www.foo.com/index.html'
    email3s_bad = 'Nancy'
    email4s_bad = 'John@'

    def test_email(self):
        self.assertEqual(self.tc.encode('Email-Addr', self.email1s), self.email1s)
        self.assertEqual(self.tc.decode('Email-Addr', self.email1s), self.email1s)
        with self.assertRaises(ValueError):
            self.tc.encode('Email-Addr', self.email2s_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('Email-Addr', self.email2s_bad)
        with self.assertRaises(ValueError):
            self.tc.encode('Email-Addr', self.email3s_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('Email-Addr', self.email3s_bad)
        with self.assertRaises(ValueError):
            self.tc.encode('Email-Addr', self.email4s_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('Email-Addr', self.email4s_bad)

    hostname1s = 'eewww.example.com'
    hostname2s = 'top-gun.2600.xyz'                     # No TLD registry, no requirement to be FQDN
    hostname3s = 'dynamo'                               # No requirement to have more than one label
    hostname1s_bad = '_http._sctp.www.example.com'      # Underscores are allowed in DNS service names but not hostnames
    hostname2s_bad = 'tag-.example.com'                 # Label cannot begin or end with hyphen

    def test_hostname(self):
        self.assertEqual(self.tc.encode('Hostname', self.hostname1s), self.hostname1s)
        self.assertEqual(self.tc.decode('Hostname', self.hostname1s), self.hostname1s)
        self.assertEqual(self.tc.encode('Hostname', self.hostname2s), self.hostname2s)
        self.assertEqual(self.tc.decode('Hostname', self.hostname2s), self.hostname2s)
        self.assertEqual(self.tc.encode('Hostname', self.hostname3s), self.hostname3s)
        self.assertEqual(self.tc.decode('Hostname', self.hostname3s), self.hostname3s)
        with self.assertRaises(ValueError):
            self.tc.encode('Hostname', self.hostname1s_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('Hostname', self.hostname1s_bad)
        with self.assertRaises(ValueError):
            self.tc.encode('Hostname', self.hostname2s_bad)
        with self.assertRaises(ValueError):
            self.tc.decode('Hostname', self.hostname2s_bad)
        with self.assertRaises(ValueError):
            self.tc.encode('Hostname', self.email1s)
        with self.assertRaises(ValueError):
            self.tc.decode('Hostname', self.email1s)

    good_urls = [       # Some examples from WHATWG spec (which uses URL as a synonym for URI, so URNs are valid URLs)
        'http://example.com/resource?foo=bar#fragment',
        'urn:isbn:0451450523',
        'urn:uuid:6e8bc430-9c3a-11d9-9669-0800200c9a66',
        'https://example.com/././foo',
        'file://loc%61lhost/',
        'https://EXAMPLE.com/../x',
        'https://example.org//',
    ]
    bad_urls = [
        'www.example.com/index.html',       # Missing scheme
        # 'https:example.org',                  # // is required
        # 'https://////example.com///',
        # 'http://www.example.com',             # Missing resource
        'file:///C|/demo',
        # 'https://user:password@example.org/',
        'https://example.org/foo bar',      # Extra whitespace
        'https://example.com:demo',         #
        'http://[www.example.com]/',        #
    ]

    def test_uri(self):
        for uri in self.good_urls:
            self.assertEqual(self.tc.encode('URI', uri), uri)
            self.assertEqual(self.tc.decode('URI', uri), uri)
        for uri in self.bad_urls:
            with self.assertRaises(ValueError):
                self.tc.encode('URI', uri)
            with self.assertRaises(ValueError):
                self.tc.decode('URI', uri)

    dt1 = 1626634165000
    dt4 = 1626634165394
    dts1 = '2021-07-18T18:49:25+00:00'
    dtsf = '2021-07-18T18:49:25.394+00:00'  # millisecond resolution
    dts2 = '2021-07-18t18:49:25z'           # RFC 3339 allows lower-case t and z
    dts3 = '2021-07-18 18:49:25Z'           # RFC 3339 allows space instead of T
    dts4 = '2021-07-18 18:49:25.394Z'

    def test_datetime(self):
        self.assertEqual(self.tc.encode('DateTime', self.dt1), self.dts1)
        self.assertEqual(self.tc.encode('DateTime', self.dt4), self.dtsf)
        self.assertEqual(self.tc.decode('DateTime', self.dts1), self.dt1)
        self.assertEqual(self.tc.decode('DateTime', self.dts2), self.dt1)
        self.assertEqual(self.tc.decode('DateTime', self.dts3), self.dt1)
        self.assertEqual(self.tc.decode('DateTime', self.dts4), self.dt4)

    int8v0 = 0
    int8v1 = -128
    int8v2 =  127
    int8v3 = -129
    int8v4 =  128

    int16v1 = -32768
    int16v2 =  32767
    int16v3 = -32769
    int16v4 =  32768

    int32v1 = -2147483648
    int32v2 =  2147483647
    int32v3 = -2147483649
    int32v4 =  2147483648

    int64v1 = -9223372036854775808
    int64v2 =  9223372036854775807
    int64v3 = -9223372036854775809
    int64v4 =  9223372036854775808

    def test_sized_ints(self):
        self.assertEqual(self.tc.encode('Int8', self.int8v0), self.int8v0)
        self.assertEqual(self.tc.decode('Int8', self.int8v0), self.int8v0)
        self.assertEqual(self.tc.encode('Int8', self.int8v1), self.int8v1)
        self.assertEqual(self.tc.decode('Int8', self.int8v1), self.int8v1)
        self.assertEqual(self.tc.encode('Int8', self.int8v2), self.int8v2)
        self.assertEqual(self.tc.decode('Int8', self.int8v2), self.int8v2)
        with self.assertRaises(ValueError):
            self.tc.encode('Int8', self.int8v3)
        with self.assertRaises(ValueError):
            self.tc.decode('Int8', self.int8v3)
        with self.assertRaises(ValueError):
            self.tc.encode('Int8', self.int8v4)
        with self.assertRaises(ValueError):
            self.tc.decode('Int8', self.int8v4)

        self.assertEqual(self.tc.encode('Int16', self.int8v0), self.int8v0)
        self.assertEqual(self.tc.decode('Int16', self.int8v0), self.int8v0)
        self.assertEqual(self.tc.encode('Int16', self.int16v1), self.int16v1)
        self.assertEqual(self.tc.decode('Int16', self.int16v1), self.int16v1)
        self.assertEqual(self.tc.encode('Int16', self.int16v2), self.int16v2)
        self.assertEqual(self.tc.decode('Int16', self.int16v2), self.int16v2)
        with self.assertRaises(ValueError):
            self.tc.encode('Int16', self.int16v3)
        with self.assertRaises(ValueError):
            self.tc.decode('Int16', self.int16v3)
        with self.assertRaises(ValueError):
            self.tc.encode('Int16', self.int16v4)
        with self.assertRaises(ValueError):
            self.tc.decode('Int16', self.int16v4)

        self.assertEqual(self.tc.encode('Int32', self.int8v0), self.int8v0)
        self.assertEqual(self.tc.decode('Int32', self.int8v0), self.int8v0)
        self.assertEqual(self.tc.encode('Int32', self.int32v1), self.int32v1)
        self.assertEqual(self.tc.decode('Int32', self.int32v1), self.int32v1)
        self.assertEqual(self.tc.encode('Int32', self.int32v2), self.int32v2)
        self.assertEqual(self.tc.decode('Int32', self.int32v2), self.int32v2)
        with self.assertRaises(ValueError):
            self.tc.encode('Int32', self.int32v3)
        with self.assertRaises(ValueError):
            self.tc.decode('Int32', self.int32v3)
        with self.assertRaises(ValueError):
            self.tc.encode('Int32', self.int32v4)
        with self.assertRaises(ValueError):
            self.tc.decode('Int32', self.int32v4)

        self.assertEqual(self.tc.encode('Int64', self.int8v0), self.int8v0)
        self.assertEqual(self.tc.decode('Int64', self.int8v0), self.int8v0)
        self.assertEqual(self.tc.encode('Int64', self.int64v1), self.int64v1)
        self.assertEqual(self.tc.decode('Int64', self.int64v1), self.int64v1)
        self.assertEqual(self.tc.encode('Int64', self.int64v2), self.int64v2)
        self.assertEqual(self.tc.decode('Int64', self.int64v2), self.int64v2)
        with self.assertRaises(ValueError):
            self.tc.encode('Int64', self.int64v3)
        with self.assertRaises(ValueError):
            self.tc.decode('Int64', self.int64v3)
        with self.assertRaises(ValueError):
            self.tc.encode('Int64', self.int64v4)
        with self.assertRaises(ValueError):
            self.tc.decode('Int64', self.int64v4)


class Union(unittest.TestCase):
    schema = {
        'types': [
            ['PhoneAny', 'Choice', ['CO'], '', [
                [1, 'f1', 'PhoneType', [], ''],
                [2, 'f2', 'String', [], '']
            ]],
            ['PhoneAll', 'Choice', ['CA'], '', [
                [1, 'f1', 'PhoneType', [], ''],
                [2, 'f2', 'String', [], '']
            ]],
            ['PhoneOne', 'Choice', ['CX'], '', [
                [1, 'f1', 'PhoneType', [], ''],
                [2, 'f2', 'String', [], '']
            ]],
            ['PhoneType', 'Enumerated', [], '', [
                [1, 'home', ''],
                [2, 'work', ''],
                [3, 'cell', '']
            ]],
            ['Namespaces', 'Choice', ['CO'], 'anyOf v1.1 or v1.0, in priority order', [
                [1, 'ns_arr', 'NsArr', [], '[prefix, namespace] syntax - v1.1'],
                [2, 'ns_obj', 'NsObj', [], '{prefix: Namespace} syntax - v1.0']
            ]],
            ['NsArr', 'ArrayOf', ['*PrefixNS', '{1'], 'Type references to other packages - v1.1', []],
            ['PrefixNS', 'Array', [], 'Prefix corresponding to a namespace IRI', [
                [1, 'prefix', 'NSID', [], ''],
                [2, 'namespace', 'URI', [], '']
            ]],
            ['NsObj', 'MapOf', ['*URI', '+NSID', '{1'], 'Type references to other packages - v1.0', []],
            ['NSID', 'String', ['}8'], '', []],
            ['URI', 'String', ['/uri'], '', []],
        ]
    }

    def setUp(self):
        jadn.check(self.schema)
        self.tc = jadn.codec.Codec(self.schema, verbose_rec=True, verbose_str=True)

    phone1 = 'home'
    phone2 = 'office'

    def test_union_phone(self):
        self.assertEqual(self.tc.encode('PhoneAny', self.phone1), self.phone1)
        self.assertEqual(self.tc.decode('PhoneAny', self.phone1), self.phone1)
        self.assertEqual(self.tc.encode('PhoneAny', self.phone2), self.phone2)
        self.assertEqual(self.tc.decode('PhoneAny', self.phone2), self.phone2)
        self.assertEqual(self.tc.encode('PhoneAll', self.phone1), self.phone1)
        self.assertEqual(self.tc.decode('PhoneAll', self.phone1), self.phone1)
        with self.assertRaises(ValueError):
            self.tc.encode('PhoneAll', self.phone2)
        with self.assertRaises(ValueError):
            self.tc.decode('PhoneAll', self.phone2)
        with self.assertRaises(ValueError):
            self.tc.encode('PhoneOne', self.phone1)
        with self.assertRaises(ValueError):
            self.tc.decode('PhoneOne', self.phone1)
        self.assertEqual(self.tc.encode('PhoneOne', self.phone2), self.phone2)
        self.assertEqual(self.tc.decode('PhoneOne', self.phone2), self.phone2)

    ns_map = {    # Map syntax - duplicate keys are invalid
        '': 'https://shop.bookstore.com/books/metadata/',
        'bm': 'https://shop.bookstore.com/books/back_matter/',
        'cat': 'https://shop.bookstore.com/books/catalog/',
        'prof': 'https://shop.bookstore.com/books/profile/',
        'comp': 'https://shop.bookstore.com/books/component/'
    }
    ns_array = [    # Array syntax - duplicates are valid
        ['', 'https://shop.bookstore.com/books/metadata/'],
        ['', 'https://shop.bookstore.com/books/back_matter/'],
        ['cat', 'https://shop.bookstore.com/books/catalog/'],
        ['prof', 'https://shop.bookstore.com/books/profile/'],
        ['cat', 'https://shop.bookstore.com/books/component/']
    ]

    def test_union_namespaces(self):
        self.assertEqual(self.tc.encode('Namespaces', self.ns_map), self.ns_map)
        self.assertEqual(self.tc.decode('Namespaces', self.ns_map), self.ns_map)
        self.assertEqual(self.tc.encode('Namespaces', self.ns_array), self.ns_array)
        self.assertEqual(self.tc.decode('Namespaces', self.ns_array), self.ns_array)


if __name__ == '__main__':
    unittest.main()
