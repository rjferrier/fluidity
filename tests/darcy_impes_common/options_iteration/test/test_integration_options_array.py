import unittest
from tree_elements import OptionsArray, OptionsNode, OptionsArrayException
from options_dict import OptionsDict, OptionsDictException
from node_info import OrphanNodeInfo, ArrayNodeInfo
    

class TestOptionsArrayCreation(unittest.TestCase):

    def test_create_with_common_entries(self):
        """
        I create an OptionsArray 'A' using three integers and a valid
        common_entries argument.  I should be able to use the latter
        after collapsing the array to get options dictionaries.
        """
        array = OptionsArray('A', range(3), {'foo': 'bar'})
        ods = array.collapse()
        for od in ods:
            self.assertEqual(od['foo'], 'bar') 

    def test_create_with_bad_common_entries(self):
        """
        I create an OptionsArray 'A' using three integers and
        something that is not a dictionary for the common_entries
        argument.  An error should be raised.
        """
        create_array = lambda: OptionsArray('A', range(3), 'foo')
        self.assertRaises(OptionsDictException, create_array)

    def test_format_names_with_string(self):
        """
        I create an OptionsDict array 'A' using integers 2, 5, 10.
        Format the element names as A02, A05, A10.
        """
        seq = OptionsArray('A', [2, 5, 10], name_format='A{:02g}')
        expected_names = ['A02', 'A05', 'A10']
        for el, expected in zip(seq, expected_names):
            self.assertEqual(str(el), expected)

    def test_format_names_with_function(self):
        """
        I create an OptionsDict array 'A' using floats 1, 2.5, 6.25.
        Format the element names as 1p00, 2p50, 6p25.
        """
        formatter = lambda x: '{:.2f}'.format(x).replace('.', 'p')
        seq = OptionsArray('A', [1., 2.5, 6.25], name_format=formatter)
        expected_names = ['1p00', '2p50', '6p25']
        for el, expected in zip(seq, expected_names):
            self.assertEqual(str(el), expected)

    def test_format_names_with_bad_formatter(self):
        """
        I create an OptionsDict array with an inappropriate object
        as name_format.  An error should be raised.
        """
        create_seq = lambda: OptionsArray('A', [1., 2.5, 6.25],
                                          name_format=None)
        self.assertRaises(OptionsArrayException, create_seq)


class TestOptionsArrayBasics(unittest.TestCase):

    def setUp(self):
        """
        I create an OptionsArray from a list of assorted objects, two of
        which are OptionsNodes - one created from a string and dict,
        the other from a class.
        """
        node = OptionsNode('some_dict', {'foo': 'bar'})
        class another_dict:
            qux = 2
        another_node = OptionsNode(another_dict)
        self.values = ['A', 3.14, node, another_node]
        self.array = OptionsArray('random', self.values)
        self.expected_names = ['A', '3.14', 'some_dict', 'another_dict']

    def test_create_options_dict(self):
        node = self.array.create_options_node('baz')
        self.assertIsInstance(node, OptionsNode)
        self.assertEqual(str(node), 'baz')

    def test_create_node_info(self):
        ni = self.array.create_node_info(1)
        self.assertIsInstance(ni, ArrayNodeInfo)
        self.assertEqual(ni.str(collection_separator=':'), 'random:3.14')

    def test_copy(self):
        other = self.array.copy()
        # test for equivalence and non-identity
        self.assertEqual(other, self.array)
        self.assertFalse(other is self.array)

    def test_element_types(self):
        for el in self.array:
            self.assertIsInstance(el, OptionsNode)

    def test_element_types_after_collapse(self):
        for el in self.array.collapse():
            self.assertIsInstance(el, OptionsDict)

    def test_element_names_after_collapse(self):
        for el, expected in zip(self.array.collapse(), self.expected_names):
            self.assertEqual(str(el), expected)

    def test_element_contents_after_collapse(self):
        """
        Getting the options dictionaries and querying 'random' should
        return the various values; alternatively, the OptionsNode
        dictionaries we started with should now be queryable.
        """
        for i, el in enumerate(self.array.collapse()):
            if i==2:
                self.assertEqual(el['foo'], 'bar')
            elif i==3:
                self.assertEqual(el['qux'], 2)
            else:
                self.assertEqual(el['random'], self.values[i])

    def test_element_node_name_after_collapse(self):
        """
        Each options dictionary should return a node info object that has
        the correct name, indicating that it is a NodeInfo object.
        """
        for i, el in enumerate(self.array.collapse()):
            ni = el.get_node_info()
            self.assertEqual(ni.str(), self.expected_names[i])

    def test_element_node_position_after_collapse(self):
        """
        Each options dictionary should return a node info object that has
        the correct position, indicating that it is an ArrayNodeInfo
        object.
        """
        for i, el in enumerate(self.array.collapse()):
            ni = el.get_node_info()
            self.assertTrue(ni.at(i))

    def test_getitem_from_index_and_check_type_and_node_info(self):
        node = self.array[2]
        self.assertIsInstance(node, OptionsNode)
        # check node info is up to date
        od = node.collapse()[0]
        ni = od.get_node_info()
        self.assertTrue(ni.at(2))

    def test_getitem_from_slice_and_check_type_and_node_info(self):
        subarray = self.array[1:4:2]
        self.assertIsInstance(subarray, OptionsArray)
        # check that all items are nodes
        for node in self.array:
            self.assertIsInstance(node, OptionsNode)
        # check that node info is up to date in this subarray
        for i, od in enumerate(subarray.collapse()):
            ni = od.get_node_info()
            self.assertTrue(ni.at(i))

    def test_setitem_from_slice_and_check_type_and_node_info(self):
        node = OptionsNode('some_other_dict', {'foo': 'baz'})
        self.array[1:4:2] = [3, node]
        self.assertIsInstance(self.array[1:4:2], OptionsArray)
        # check that all set items have been converted to nodes
        for node in self.array:
            self.assertIsInstance(node, OptionsNode)
        # check that node info is up to date
        for i, od in enumerate(self.array.collapse()):
            ni = od.get_node_info()
            self.assertTrue(ni.at(i))

    def check_array_node_info(self, index, expected_node_names):
        """
        Helper function.  Checks that node info is up to date in the
        OptionsArray under test.
        """
        od = self.array.collapse()[index]
        ni = od.get_node_info()
        self.assertIsInstance(ni, ArrayNodeInfo)
        self.assertTrue(ni.at(index))
        self.assertEqual(ni.node_names, expected_node_names)

    def test_append_and_check_node_info(self):
        # append with primitive
        self.array.append(OptionsNode('5'))
        self.check_array_node_info(-1, self.expected_names + ['5'])
        # append with node
        self.array.append(OptionsNode('another_dict'))
        self.check_array_node_info(
            -1, self.expected_names + ['5', 'another_dict'])

    def test_pop_and_check_node_info(self):
        node = self.array.pop()
        # check that this node is now an orphan node
        od = node.collapse()[0]
        ni = od.get_node_info()
        self.assertIsInstance(ni, OrphanNodeInfo)
        # check remaining array
        self.check_array_node_info(-1, self.expected_names[:-1])
        
            

class TestOptionsArraySlice(unittest.TestCase):

    def setUp(self):
        """
        I create an OptionsArray and take a slice which should leave me
        the second, fifth and eighth nodes.  This test fixture is
        important for checking that node information is being injected
        correctly into the options dictionaries.
        """
        node_names = [c for c in 'ABCDEFGHIJKL']
        self.array = OptionsArray('alphabet', node_names)
        self.array = self.array[1:10:3]
        self.expected_names = 'BEH'

    def test_element_names_after_collapse(self):
        for el, expected in zip(self.array.collapse(), self.expected_names):
            self.assertEqual(str(el), expected)

    def test_element_node_position_after_collapse(self):
        for i, el in enumerate(self.array.collapse()):
            ni = el.get_node_info()
            self.assertTrue(ni.at(i))

            
if __name__ == '__main__':
    unittest.main()
