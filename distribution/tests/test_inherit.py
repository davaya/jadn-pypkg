"""
Test JADN Codec
"""
import copy
import os
import random
import unittest
import jadn


class Inherit(unittest.TestCase):
    schema = {
        'types': [
            []
        ]
    }

    def setUp(self):
        jadn.check(self.schema)

    def test_extend(self):
        """

        """
        self.assertEqual('a', 'a')

    def test_restrict(self):
        """

        """
        self.assertEqual('a', 'a')

    def test_abstract(self):
        self.assertEqual('a', 'a')

    def test_final(self):
        self.assertEqual('a', 'a')


if __name__ == '__main__':
    unittest.main()
