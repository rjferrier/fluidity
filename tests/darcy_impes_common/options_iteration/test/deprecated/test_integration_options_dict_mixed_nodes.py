import sys
sys.path.append('..')

import unittest
from options_dict import OptionsDict, OptionsDictException, NodeInfoException


class TestOptionsDictsWithMixedNodeInfo(unittest.TestCase):
    
    def setUp(self):
        """
        I create three OptionsDict arrays, 'A', 'B' and 'C', and an orphan
        (non-array-initialised) OptionsDict.  I store the second element
        of B and update it with the first element of C, an orphan node,
        and the third element of A.  To make sure the framework is
        really robust, I'm going to do the updating in a funny order.
        """
        A = OptionsDict.array('A', [1, 2, 3])
        B = OptionsDict.array('B', ['i', 'ii', 'iii'])
        C = OptionsDict.array('C', [0.25, 0.5, 1.0])
        d = OptionsDict.node('d', {})
        d.update(A[2])
        C[0].update(d)
        self.od = B[1]
        self.od.update(C[0])
        
    def test_get_default_node_info(self):
        """
        When I call get_node_info with no arguments, the result should
        be the same as that of get_node_info('B'), i.e. it should not
        have changed since B was updated.
        """
        self.assertEqual(self.od.get_node_info(),
                         self.od.get_node_info('B'))

    def test_get_other_node_info(self):
        """
        get_node_info('A') should return a NodeInfo object from which we
        can recover the name of the third element in A.
        """
        self.assertEqual(self.od.get_node_info('A').str(), '3')

    def test_copy(self):
        other = self.od.copy()
        # test for equivalence and non-identity
        self.assertEqual(other, self.od)
        self.assertFalse(other is self.od)
        # test that node_info objects have been copied and not simply
        # linked
        E = OptionsDict.array('E', ['foo', 'bar'])
        other.update(E[0])
        self.assertRaises(NodeInfoException, \
                          lambda: self.od.get_node_info('E'))

    def test_default_str(self):
        """
        Calling the str() method without any arguments should return a
        name for the OptionsDict based on its constituent OptionsDict.
        """
        self.assertEqual(self.od.str(), 'ii_0.25_d_3')

    def test_str_from_array_names(self):
        """
        I should be able to get a subset of the name of the merged
        OptionsDict by passing array names to its str() method.  The
        ordering of the resulting substrings should be insensitive to
        the order in which I give the array names.
        """
        self.assertEqual(self.od.str('A'), '3')
        self.assertEqual(self.od.str(['C', 'A']), '0.25_3')
        self.assertEqual(self.od.str(['A', 'C']), '0.25_3')

    def test_str_with_exclusions(self):
        """
        I should be able to exclude substrings from the name of the
        merged OptionsDict by passing array names via the 'exclude'
        argument of its str() method.  The ordering of the resulting
        substrings should be insensitive to the order in which I give
        the array names.
        """
        self.assertEqual(self.od.str(exclude='C'), 'ii_d_3')
        self.assertEqual(self.od.str(exclude=['C', 'B']), 'd_3')

    def test_str_from_array_names_with_exclusions(self):
        """
        I should be able to use the 'only' and 'exclude' arguments
        together, although the latter will override the former.
        Having an array name that features in the latter but not the
        former should do nothing.
        """
        self.assertEqual(self.od.str(['A', 'C'], exclude='A'), '0.25')
        self.assertEqual(self.od.str('C', exclude='A'), '0.25')
        self.assertEqual(self.od.str('A', exclude=['A', 'C']), '')

    def test_str_from_absolute_indices(self):
        """
        I should be able to infer the name of another merged OptionsDict
        by passing array names and absolute indices to its str()
        method.
        """
        self.assertEqual(
            self.od.str(absolute={'B': -1, 'A': 0}), 'iii_0.25_d_1')
        self.assertRaises(IndexError, lambda: self.od.str(relative={'A': 3}))

    def test_str_from_relative_indices(self):
        """
        I should be able to infer the name of another merged OptionsDict
        by passing array names and relative indices to its str()
        method.
        """
        self.assertEqual(
            self.od.str(relative={'A': -1, 'C': 1}), 'ii_0.5_d_2')
        self.assertRaises(IndexError, lambda: self.od.str(relative={'C': -1}))

    def test_str_with_absolute_and_relative_indices(self):
        """
        I should be able to mix the 'absolute' and 'relative' arguments.
        """
        self.assertEqual(
            self.od.str(absolute={'B': -1, 'C': 2},
                        relative={'A': -1, 'C': -1}),
            'iii_0.5_d_2')

    def test_str_with_all_four_arguments(self):
        """
        I should be able to use all four arguments in forming the string.
        """
        self.assertEqual(
            self.od.str(only=['A', 'C', 'B'], exclude='C',
                        absolute={'B': -1, 'C': 2},
                        relative={'A': -1, 'C': -1}),
            'iii_2')
        
if __name__ == '__main__':
    unittest.main()
        
