
import os
from unittest import main, TestCase

import jadn
from jadn.codec import Codec


class JADN(TestCase):

    def setUp(self):
        fn = os.path.join(jadn.data_dir(), 'jadn_v1.0_schema.jadn')
        schema = jadn.load(fn)
        self.schema = schema
        sa = jadn.analyze(schema)
        if sa['undefined']:
            print('Warning - undefined:', sa['undefined'])
        self.tc = Codec(schema)

    def test_jadn_self(self):
        self.tc.set_mode(verbose_rec=True, verbose_str=True)
        self.assertDictEqual(self.tc.encode('Schema', self.schema), self.schema)
        self.assertDictEqual(self.tc.decode('Schema', self.schema), self.schema)


class BadSchema(TestCase):
    schema_bad_item_fields = {
        'meta': {'module': 'http://jadn.org/unittests-BadSchema'},
        'types': [
            ['Color', 'Map', [], '', [          # Enumerated items not applicable to Container types
                [1, 'red', ''],
                [2, 'green', ''],
                [3, 'blue', '']
            ]]
        ]
    }

    def test_bad_item_fields(self):
        with self.assertRaises(ValueError):
            jadn.check(self.schema_bad_item_fields)


if __name__ == '__main__':
    main()
