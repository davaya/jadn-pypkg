"""
Test JADN Schema Validation
"""
import os
from binascii import a2b_hex
from unittest import main, TestCase

import jadn
from jadn.codec import Codec

dir_path = os.path.abspath(os.path.dirname(__file__))


class JADN(TestCase):
    def setUp(self):
        with open(os.path.join(jadn.data_dir(), 'jadn_v1.0_schema.jadn')) as fp:
            self.schema = jadn.load(fp)
        sa = jadn.analyze(self.schema)
        if sa['undefined']:
            print('Warning - undefined:', sa['undefined'])
        self.tc = Codec(self.schema)

    def test_jadn_self(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('Schema', self.schema), self.schema)
        self.assertDictEqual(self.tc.decode('Schema', self.schema), self.schema)


class BadSchema(TestCase):
    schema_bad_item_fields = {
        'types': [
            ['Color', 'Map', [], '', [          # Enumerated items not applicable to Container types
                [1, 'red', ''],
                [2, 'green', ''],
                [3, 'blue', '']
            ]]
        ]
    }

    schema_bad_ordinal_fields = {
        'types': [
            ['Color', 'Record', [], '', [  # Invalid item ID for blue
                [1, 'red', 'Integer', ['{0', '}255'], ''],
                [2, 'green', 'Integer', ['{0', '}255'], ''],
                [4, 'blue', 'Integer', ['{0', '}255'], '']
            ]]
        ]
    }

    def test_bad_item_fields(self):
        with self.assertRaises(ValueError):
            jadn.check(self.schema_bad_item_fields)

    def test_bad_ordinal_fields(self):
        with self.assertRaises(ValueError):
            jadn.check(self.schema_bad_ordinal_fields)


class SpecExamples(TestCase):
    """
    Test Example messages contained in JADN spec
    """

    def setUp(self):
        with open(os.path.join(dir_path, 'jadn-v1.0-examples.jadn')) as fp:
            self.schema = jadn.load(fp)
        self.tc = Codec(self.schema, verbose_rec=True, verbose_str=True)

    def test_choice_explicit(self):
        msg_intrinsic = {"quantity": 395, "product": {"software": "https://www.example.com/B902D1P0W37"}}
        msg_explicit = {"dept": "software", "quantity": 395, "product": "https://www.example.com/B902D1P0W37"}

        self.assertEqual(self.tc.encode('Stock1', msg_intrinsic), msg_intrinsic)
        self.assertEqual(self.tc.encode('Stock2', msg_explicit), msg_explicit)

    def test_pointer(self):
        msg_pointer = {
          "a": {"x": 57.9, "y": 4.841},
          "b": {
            "foo": "Elephant",
            "bar": 762}}
        self.assertEqual(self.tc.encode('Catalog', msg_pointer), msg_pointer)

    def test_discriminated_union(self):
        md5 = "B64CF5EAF07E86D1697D4EEE96A670B6"
        md5b = a2b_hex(md5)
        sha256 = "C9004978CF5ADA526622ACD4EFED005A980058B7B9972B12F9B3A5D0DA46B7D9"
        sha256b = a2b_hex(sha256)
        msg_intrinsic = {"sha256": sha256, "md5": md5}
        api_intrinsic = {"sha256": sha256b, "md5": md5b}
        msg_explicit = [{"algorithm": "md5", "value": md5}, {"algorithm": "sha256", "value": sha256}]
        api_explicit = [{"algorithm": "md5", "value": md5b}, {"algorithm": "sha256", "value": sha256b}]
        msg_explicit_bad_alg = [{"algorithm": "foo", "value": md5}, {"algorithm": "sha256", "value": sha256}]
        msg_explicit_bad_val = [{"algorithm": "md5", "value": sha256}, {"algorithm": "sha256", "value": sha256}]
        self.assertEqual(self.tc.decode('Hashes', msg_intrinsic), api_intrinsic)
        self.assertEqual(self.tc.decode('Hashes2', msg_explicit), api_explicit)
        with self.assertRaises(ValueError):
            self.tc.decode('Hashes2', msg_explicit_bad_alg)
        with self.assertRaises(ValueError):
            self.tc.decode('Hashes2', msg_explicit_bad_val)


class SpecExamplesUniversity(TestCase):
    uni_verbose = {
      "name": "Faber College",
      "classes": [
        {
          "name": "ECE1010",
          "room": "DRGN 105",
          "teachers": ["U-004932"],
          "students": ["U-194325", "U-029437"]
        }, {
          "name": "ECE1750",
          "room": "FLRS 102",
          "teachers": ["U-004932"],
          "students": ["U-127439", "U-194325", "U-029437"]
        }
      ],
      "people": [
        {
          "name": "Damien Braun",
          "univ_id": "U-004932",
          "email": "d.braun@faber.edu"
        }, {
          "name": "Ellie Osborne",
          "univ_id": "U-194325",
          "email": "ellie.osborne@faber.edu"
        }, {
          "name": "Pierre Cox",
          "univ_id": "U-029437",
          "email": "pc9000@outlook.com"
        }, {
          "name": "Alden Cantrel",
          "univ_id": "U-127439",
          "email": "alden.cantrel@faber.edu"
        }
      ]
    }

    uni_compact = [
      "Faber College",
      [
        ["ECE1010", "DRGN 105", ["U-004932"], ["U-194325", "U-029437"]],
        ["ECE1750", "FLRS 102", ["U-004932"], ["U-127439", "U-194325", "U-029437"]]
      ],
      [
        ["Damien Braun", "U-004932", "d.braun@faber.edu"],
        ["Ellie Osborne", "U-194325", "ellie.osborne@faber.edu"],
        ["Pierre Cox", "U-029437", "pc9000@outlook.com"],
        ["Alden Cantrel", "U-127439", "alden.cantrel@faber.edu"]
      ]
    ]

    def test_university(self):
        with open(os.path.join(dir_path, 'jadn-v1.0-examples-uni.jadn')) as fp:
            self.schema = jadn.load(fp)
        self.tcv = Codec(self.schema, verbose_rec=True, verbose_str=True)
        self.tcc = Codec(self.schema, verbose_rec=False, verbose_str=True)
        uni_1 = self.tcv.decode("University", self.uni_verbose)
        uni_2 = self.tcc.decode("University", self.uni_compact)
        self.assertEqual(uni_1, uni_2)


if __name__ == '__main__':
    main()
