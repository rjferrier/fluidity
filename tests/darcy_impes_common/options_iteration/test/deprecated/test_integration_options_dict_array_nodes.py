import sys
sys.path.append('..')

import unittest
from options_dict import OptionsDict, OptionsDictException, NodeInfoException
from node_info import ArrayNodeInfo

class TestOptionsDictArrayCreationOptions(unittest.TestCase):

    def test_create_with_common_entries(self):
        """
        I create an OptionsDict array 'A' using three integers and
        common entry {'foo': 'bar'}.  All elements should have this
        entry.
        """
        seq = OptionsDict.array('A', range(3), {'foo': 'bar'})
        for el in seq:
            self.assertEqual(el['foo'], 'bar')

    def test_create_with_bad_common_entries(self):
        """
        I create an OptionsDict array 'A' using three integers and
        something that is not a dictionary for the common_entries
        argument.  An error should be raised.
        """
        create_seq = lambda: \
            OptionsDict.array('A', range(3), 'foo')
        self.assertRaises(OptionsDictException, create_seq)

    def test_format_names_with_string(self):
        """
        I create an OptionsDict array 'A' using integers 2, 5, 10.
        Format the element names as A02, A05, A10.
        """
        seq = OptionsDict.array('A', [2, 5, 10],
                                   name_format='A{:02g}')
        expected_names = ['A02', 'A05', 'A10']
        for el, expected in zip(seq, expected_names):
            self.assertEqual(str(el), expected)

    def test_format_names_with_function(self):
        """
        I create an OptionsDict array 'A' using floats 1, 2.5,
        6.25.  Format the element names as 1p00, 2p50, 6p25.
        """
        formatter = lambda x: '{:.2f}'.format(x).replace('.', 'p')
        seq = OptionsDict.array('A', [1., 2.5, 6.25],
                              name_format=formatter)
        expected_names = ['1p00', '2p50', '6p25']
        for el, expected in zip(seq, expected_names):
            self.assertEqual(str(el), expected)

    def test_format_names_with_bad_formatter(self):
        """
        I create an OptionsDict array with an inappropriate object
        as name_format.  An error should be raised.
        """
        create_seq = lambda: \
            OptionsDict.array('A', [1., 2.5, 6.25],
                                 name_format=None)
        self.assertRaises(OptionsDictException, create_seq)


class TestOptionsDictArrayBasics(unittest.TestCase):

    def setUp(self):
        """
        I create an OptionsDict array from a list of different-typed
        values, one of which is already an OptionsDict.
        """
        od = OptionsDict.node('some_dict', {'foo': 'bar'})
        self.values = ['A', od, 2, 3.14]
        self.seq = OptionsDict.array('random_thing', self.values)
        
    def test_element_types(self):
        """
        Each element in the array should be an OptionsDict.
        """
        for el in self.seq:
            self.assertIsInstance(el, OptionsDict)

    def test_element_names(self):
        """
        The name of each element, given by its string representation,
        should be identical to the string representation of the
        corresponding initial value.
        """
        for el, v in zip(self.seq, self.values):
            self.assertEqual(str(el), str(v))

    def test_element_dicts(self):
        """
        While all the elements should be dictionaries, only the
        preexisting OptionsDict should have the {'foo': 'bar'} entry.
        """
        for i, el in enumerate(self.seq):
            if i==1:
                self.assertEqual(el['foo'], 'bar')
            else:
                self.assertRaises(KeyError, lambda: el['foo'])

    def test_lookup_array_name(self):
        """
        When the array name is looked up in each element, the
        element should return the corresponding initial value.  The
        initial value representation of the preexisting OptionsDict is
        simply its name.
        """
        for i, el in enumerate(self.seq):
            result = el['random_thing']
            if i==1:
                self.assertEqual(result, 'some_dict')
            elif i==3:
                # careful with floats
                self.assertAlmostEqual(result, 3.14)
            else:
                self.assertEqual(result, self.values[i])
        
        
class TestOptionsDictArrayNodeInfo(unittest.TestCase):

    def setUp(self):
        """
        I create an OptionsDict array 'A' using three integers.  I store
        the second node and its node info object.
        """
        seq = OptionsDict.array('A', [1, 2, 3])
        self.od = seq[1]
        self.node_info = self.od.get_node_info()

    def test_node_info_type(self):
        """
        The stored node info should be an instance of ArrayNodeInfo.
        """
        self.assertIsInstance(self.node_info, ArrayNodeInfo)

    def test_str(self):
        """
        The string representation of the node info should be the same as
        that of the OptionsDict.
        """
        self.assertEqual(str(self.node_info), str(self.od))

    def test_get_node_info_by_array_name(self):
        """
        I should get the same node info by passing the array key to the
        OptionDict's get_node_info method.
        """
        self.assertEqual(self.node_info, self.od.get_node_info('A'))

    def test_nonexistent_node_info(self):
        """
        Conversely, passing anything else should return None.
        """
        self.assertRaises(NodeInfoException, \
                          lambda: self.od.get_node_info('B'))

    def test_copy(self):
        other = self.od.copy()
        # test for equivalence and non-identity
        self.assertEqual(other, self.od)
        self.assertFalse(other is self.od)

        
class TestOptionsDictArrayNodeUpdatedWithSibling(unittest.TestCase):

    def setUp(self):
        """
        This is not an intended use case, but suppose I create an array
        and update one of the OptionsDicts with another from the same
        sequence.
        """
        seq = OptionsDict.array('A', [1, 2, 3])
        self.od = seq[1]
        self.od.update(seq[2])
        self.node_info = self.od.get_node_info()
        
    def test_default_str(self):
        self.assertEqual(self.od.str(), '2_3')

    def test_get_node_info(self):
        """
        Whether I call get_node_info with no arguments or with the array
        name, the result should be the original node info.
        """
        self.assertEqual(self.od.get_node_info().str(), '2')
        self.assertEqual(self.od.get_node_info('A').str(), '2')

    def test_set_default_node_info(self):
        """
        When I call set_node_info with no arguments, I should end up
        setting the original node info.
        """
        self.od.set_node_info(
            self.od.create_orphan_node_info('i'))
        self.assertEqual(self.od.str(), 'i_3')

    def test_set_node_info_with_array_name(self):
        """
        When I call set_node_info with the array name, I should end up
        setting the original node info.  However, if I do this again
        having replaced the original node info with orphan node info,
        I should end up setting the second node info.
        """
        self.od.set_node_info(
            self.od.create_orphan_node_info('i'), collection_name='A')
        self.assertEqual(self.od.str(), 'i_3')

        self.od.set_node_info(
            self.od.create_orphan_node_info('ii'), collection_name='A')
        self.assertEqual(self.od.str(), 'i_ii')

    
         
if __name__ == '__main__':
    unittest.main()
        
