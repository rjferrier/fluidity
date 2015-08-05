"""
These unit tests involves file creation and destruction and are
segregated from the default tests for safety.
"""

import os
import unittest
from unit_options_dict import UnitOptionsDict


class TestOptionsDictTemplateExpansion(unittest.TestCase):

    def setUp(self):
        self.od = UnitOptionsDict({'fluid'         : 'water',
                                   'melting_point' :       0,
                                   'boiling_point' :     100})
        
    def test_expand_file(self):
        src_filename = 'sample_template.txt'
        tgt_filename = 'sample_result.txt'
        
        # expand template, read the resulting file, clean up
        self.od.expand_template_file(src_filename, tgt_filename)
        with open(tgt_filename, 'r') as f:
            result = f.readline()
        os.remove(tgt_filename)

        # check result (note the newline)
        expected = "water has a melting point of 0 degrees C.\n"
        self.assertEqual(result, expected)

        
    
if __name__ == '__main__':
    unittest.main()
        
