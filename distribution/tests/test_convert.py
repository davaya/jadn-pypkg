
from unittest import main, TestCase

from jadn.core import jadn_check, Codec


# TODO: Read and Write JIDL, Write Markdown, HTML, JSON Schema, XSD, CDDL

class Basic(TestCase):

    schema = {
    }

    def setUp(self):
        jadn_check(self.schema)
        self.tc = Codec(self.schema, verbose_rec=False, verbose_str=False)


if __name__ == '__main__':
    main()
