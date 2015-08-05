import unittest
from unit_tree_elements import UnitOptionsArray, UnitOptionsNode
from tree_elements import OptionsArrayException


class TestOptionsArrayCreation(unittest.TestCase):

    def test_create_from_assorted(self):
        """
        I should be able to create an array from assorted objects.
        """
        some_node = UnitOptionsNode('some_node', {'foo': 'bar'})
        class another_node_basis:
            qux = 1
        UnitOptionsArray('random', ['A', 3.14, some_node, another_node_basis])

        
    def test_create_with_unwrapped_dictionary(self):
        """
        I should not be able to create an array when one of the input
        elements is a dictionary.  This is because it is not obvious
        how to name the resulting nodes or what to store under the
        array key ('random').
        """
        create_array = lambda: UnitOptionsArray('random',
                                                ['A', 2, {'pi': 3.14}])
        self.assertRaises(OptionsArrayException, create_array)

        
    def test_format_names_with_string(self):
        """
        I create an OptionsArray 'A' using integers 2, 5, 10.
        Format the element names as A02, A05, A10.
        """
        array = UnitOptionsArray('A', [2, 5, 10], name_format='A{:02g}')
        expected_names = ['A02', 'A05', 'A10']
        for el, expected in zip(array, expected_names):
            self.assertEqual(str(el), expected)

    def test_format_names_with_function(self):
        """
        I create an OptionsArray 'A' using floats 1, 2.5,
        6.25.  Format the element names as 1p00, 2p50, 6p25.
        """
        fmt = lambda x: '{:.2f}'.format(x).replace('.', 'p')
        array = UnitOptionsArray('A', [1., 2.5, 6.25], name_format=fmt)
        expected_names = ['1p00', '2p50', '6p25']
        for el, expected in zip(array, expected_names):
            self.assertEqual(str(el), expected)

    def test_format_names_with_bad_formatter(self):
        """
        I create an OptionsArray with an inappropriate object
        as name_format.  An error should be raised.
        """
        create_array = lambda: UnitOptionsArray('A', [1., 2.5, 6.25],
                                                name_format=None)
        self.assertRaises(OptionsArrayException, create_array)


class TestOptionsDictArrayBasics(unittest.TestCase):

    def setUp(self):
        """
        I create an OptionsArray from a list of differently-typed values,
        one of which is an OptionsNode and another is a class which
        can be used to form the basis of an OptionsNode.
        """
        node = UnitOptionsNode('some_node', {'foo': 'bar'})
        class another_node:
            qux = 1
        self.values = ['A', 3.14, node, another_node]
        self.array = UnitOptionsArray('random', self.values)

    def test_equal(self):
        self.assertEqual(self.array, UnitOptionsArray('random', self.values))

    def test_unequal_names(self):
        self.assertNotEqual(self.array, UnitOptionsArray('things', self.values))

    def test_unequal_nodes(self):
        values = self.values
        values[0] = 'B'
        self.assertNotEqual(self.array, UnitOptionsArray('random', values))

    def test_len(self):
        self.assertEqual(len(self.array), 4)

    def test_iteration(self):
        for el, v in zip(self.array, self.values):
            try:
                v_str = v.__name__
            except AttributeError:
                v_str = str(v)
            self.assertEqual(str(el), v_str)

    def test_getitem_from_index_and_check_value(self):
        node = self.array[1]
        self.assertEqual(str(node), '3.14')

    def test_getitem_from_name_and_check_value(self):
        node = self.array['3.14']
        self.assertEqual(str(node), '3.14')

    def test_getitem_from_slice_and_check_values(self):
        subarray = self.array[1:4:2]
        self.assertEqual(str(subarray[0]), '3.14')
        self.assertEqual(str(subarray[1]), 'another_node')
        self.assertEqual(len(subarray), 2)

    def test_setitem_from_index_and_check_value(self):
        self.array[2] = UnitOptionsNode('baz')
        self.assertEqual(str(self.array[2]), 'baz')

    def test_setitem_from_slice_and_check_values(self):
        self.array[1:4:2] = [UnitOptionsNode('baz'), UnitOptionsNode('qux')]
        self.assertEqual(str(self.array[1]), 'baz')
        self.assertEqual(str(self.array[3]), 'qux')

    def test_append(self):
        self.array.append(UnitOptionsNode('5'))
        self.assertEqual(len(self.array), 5)
        self.assertEqual(str(self.array[-1]), '5')

    def test_append_with_bad_value_raises_error(self):
        self.assertRaises(OptionsArrayException, lambda: self.array.append(5))

    def test_pop_and_check_values(self):
        node = self.array.pop()
        self.assertEqual(str(node), 'another_node')
        self.assertEqual(str(self.array[-1]), 'some_node')
        self.assertEqual(len(self.array), 3)

    def test_collapse(self):
        for el, v in zip(self.array, self.values):
            try:
                v_str = v.__name__
            except AttributeError:
                v_str = str(v)
            self.assertEqual(str(el), v_str)

    def test_donate_copy(self):
        array_init = self.array.copy()
        acceptor = UnitOptionsNode('baz')
        acceptor, remainder = self.array.donate_copy(acceptor)
        self.assertEqual(acceptor.child, array_init[0:1])
        self.assertEqual(len(remainder), 3)

    def test_count_leaves(self):
        self.assertEqual(self.array.count_leaves(), 4)        

    
if __name__ == '__main__':
    unittest.main()
        
