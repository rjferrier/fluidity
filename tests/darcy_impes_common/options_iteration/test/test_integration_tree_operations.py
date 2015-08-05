import unittest
from copy import deepcopy

from tree_elements import OptionsArray, OptionsNode, product
from options_dict import OptionsDict, Lookup, freeze
from multiprocessing import Pool


# ---------------------------------------------------------------------
# helper functions

def pool():
    return Pool(2)

def add_dynamic_entry(tree_element):
    """
    Implements a dynamic entry which returns the product of 'letter'
    and 'number' entries, treating A, B, C as 1, 2, 3.
    """
    tree_element.update({'product': lambda opt: \
                         (1 + 'ABC'.index(opt['letter'])) * opt['number']})

# ---------------------------------------------------------------------
# helper classes

class Operation:
    def check(self, test_case, expected_names, expected_tree_string):
        # perform operation (delegate to subclass) 
        self()

        # flatten and inspect the result
        ods = self.result.collapse()
        test_case.assertEqual([str(od) for od in ods], expected_names)
        if expected_tree_string:
            test_case.assertEqual(self.make_tree_str(ods),
                                       expected_tree_string)

        # check the states of the operands (delegate to middle class)
        self.check_operand_states(test_case)
        
        
    @staticmethod
    def make_tree_str(options_dicts):
        result_str = ''
        for od in options_dicts:
            branch = od.str(formatter='tree')
            if branch:
                result_str += '\n' + branch
        return result_str
    

# ---------------------------------------------------------------------

class BinaryOp(Operation):
    def __init__(self, left_operand, right_operand,
                 left_subscript=None, right_subscript=None):
        self.left_operand = left_operand
        self.right_operand = right_operand
        self.left_operand_init = deepcopy(left_operand)
        self.right_operand_init = deepcopy(right_operand)

    def check_operand_states(self, test_case):
        test_case.assertEqual(self.left_operand, self.left_operand_init)
        test_case.assertEqual(self.right_operand, self.right_operand_init)
    
class Plus(BinaryOp):
    def __call__(self):
        self.result = self.left_operand + self.right_operand
        
class Times(BinaryOp):
    def __call__(self):
        self.result = self.left_operand * self.right_operand

# ---------------------------------------------------------------------
        
class IncrementalOp(Operation):
    def __init__(self, left_operand, right_operand, subscript=None):
        self.result = left_operand
        self.right_operand = right_operand
        self.result_init = deepcopy(left_operand)
        self.right_operand_init = deepcopy(right_operand)
        self.subscript = subscript

    def check_operand_states(self, test_case):
        test_case.assertNotEqual(self.result, self.result_init)
        test_case.assertEqual(self.right_operand, self.right_operand_init)
        
class PlusEquals(IncrementalOp):
    def __call__(self):
        if self.subscript:
            self.result[self.subscript] += self.right_operand
        else:
            self.result += self.right_operand
            
class TimesEquals(IncrementalOp):
    def __call__(self):
        if self.subscript:
            self.result[self.subscript] *= self.right_operand
        else:
            self.result *= self.right_operand

# ---------------------------------------------------------------------
        
class Reduction(Operation):
    def __init__(self, operands):
        self.operands = operands
        self.operands_init = deepcopy(operands)

    def check_operand_states(self, test_case):
        for op, op_init in zip(self.operands, self.operands_init):
            test_case.assertEqual(op, op_init)

class Sum(Reduction):
    def __call__(self):
        self.result = sum(self.operands)
        
class Product(Reduction):
    def __call__(self):
        self.result = product(self.operands)

        
# ---------------------------------------------------------------------
# test cases

class TestNodeOperations(unittest.TestCase):

    def setUp(self):
        self.node = OptionsNode('A')
        self.other_node = OptionsNode('B')
        self.array = OptionsArray('number', range(3))
        self.node_list = [OptionsNode(str(i)) for i in range(3)]
        self.od = OptionsDict({'foo': 'bar'})

        
    def help_test_addition_with_node(self, operation):
        expected_names = ['A_B']
        expected_tree_str = """
A
    B"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_addition_with_node(self):
        self.help_test_addition_with_node(
            Plus(self.node, self.other_node))
        
    def test_incremental_addition_with_node(self):
        self.help_test_addition_with_node(
            PlusEquals(self.node, self.other_node))
        
    def test_sum_with_node(self):
        self.help_test_addition_with_node(
            Sum((self.node, self.other_node)))

        
    def help_test_multiplication_with_node(self, operation):
        expected_names = ['A_B']
        expected_tree_str = """
A
    B"""
        operation.check(self, expected_names, expected_tree_str)

    def test_multiplication_with_node(self):
        self.help_test_multiplication_with_node(
            TimesEquals(self.node, self.other_node))
        
    def test_incremental_multiplication_with_node(self):
        self.help_test_multiplication_with_node(
            TimesEquals(self.node, self.other_node))
        
    def test_product_with_node(self):
        self.help_test_multiplication_with_node(
            Product((self.node, self.other_node)))


    def help_test_addition_with_array(self, operation):
        """
        Adding many nodes on the right (R) to a single node on the left
        (L) should work, but the surplus right hand nodes will get
        discarded (to leave L_R).  Array information (for R) should be
        preserved.
        """
        expected_names = ['A_0']
        expected_tree_str = """
A
    number: 0"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_addition_with_array(self):
        self.help_test_addition_with_array(
            Plus(self.node, self.array))
        
    def test_incremental_addition_with_array(self):
        self.help_test_addition_with_array(
            PlusEquals(self.node, self.array))
        
    def test_sum_with_array(self):
        self.help_test_addition_with_array(
            Sum((self.node, self.array)))

        
    def help_test_multiplication_with_array(self, operation):
        expected_names = ['A_0', 'A_1', 'A_2']
        expected_tree_str = """
A
    number: 0
    number: 1
    number: 2"""
        operation.check(self, expected_names, expected_tree_str)

        
    def test_multiplication_with_array(self):
        self.help_test_multiplication_with_array(
            TimesEquals(self.node, self.array))
        
    def test_incremental_multiplication_with_array(self):
        self.help_test_multiplication_with_array(
            TimesEquals(self.node, self.array))
        
    def test_product_with_array(self):
        self.help_test_multiplication_with_array(
            Product((self.node, self.array)))
        
        
    def help_test_addition_with_list(self, operation):
        """
        As with TestNodeOperationsWithArray.test_addition, but here the
        first array in the list gets added to the node on the left
        hand side, and the other arrays get discarded.  There is no
        array information this time.
        """
        expected_names = ['A_0']
        expected_tree_str = """
A
    0"""
        operation.check(self, expected_names, expected_tree_str)

    def test_addition_with_list(self):
        self.help_test_addition_with_list(
            Plus(self.node, self.node_list))

    def test_incremental_addition_with_list(self):
        self.help_test_addition_with_list(
            PlusEquals(self.node, self.node_list))
        
    def test_sum_with_list(self):
        self.help_test_addition_with_list(
            Sum([self.node, self.node_list]))

        
    def test_update_with_options_dict(self):
        self.node.update(self.od)
        node_od = self.node.collapse()[0]
        self.assertEqual(node_od['foo'], 'bar')

    def test_update_with_options_dict_from_other_node(self):
        other_od = self.other_node.collapse()[0]
        self.node.update(other_od)
        node_od = self.node.collapse()[0]
        self.assertEqual(node_od.str(), 'A_B')

    def test_update_with_options_dict_from_array(self):
        other_od = self.array.collapse()[0]
        self.node.update(other_od)
        node_od = self.node.collapse()[0]
        self.assertEqual(node_od.str(), 'A_0')

    def test_collapse_mp_safe(self):
        self.node.update({'letter': 'A', 'number': 2})
        add_dynamic_entry(self.node)
        ods = freeze(self.node.collapse())
        results = pool().map(Lookup('product'), ods)
        self.assertEqual(results, [2])

        
class TestArrayOperations(unittest.TestCase):

    def setUp(self):
        self.array = OptionsArray('letter', ['A', 'B', 'C'])
        self.other_array = OptionsArray('number', range(3))
        self.node = OptionsNode('0')
        self.node_list = [OptionsNode(str(i)) for i in range(3)]
        self.od = OptionsDict({'foo': 'bar'})

        
    def help_test_addition_with_node(self, operation):
        expected_names = ['A_0', 'B', 'C']
        expected_tree_str = """
letter: A
    0
letter: B
letter: C"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_addition_with_node(self):
        self.help_test_addition_with_node(
            Plus(self.array, self.node))
        
    def test_incremental_addition_with_node(self):
        self.help_test_addition_with_node(
            PlusEquals(self.array, self.node))
        
    def test_sum_with_node(self):
        self.help_test_addition_with_node(
            Sum([self.array, self.node]))

        
    def help_test_multiplication_with_node(self, operation):
        expected_names = ['A_0', 'B_0', 'C_0']
        expected_tree_str = """
letter: A
    0
letter: B
    0
letter: C
    0"""
        operation.check(self, expected_names, expected_tree_str)

    def test_multiplication_with_node(self):
        self.help_test_multiplication_with_node(
            Times(self.array, self.node))

    def test_incremental_multiplication_with_node(self):
        self.help_test_multiplication_with_node(
            TimesEquals(self.array, self.node))
        
    def test_product_with_node(self):
        self.help_test_multiplication_with_node(
            Product([self.array, self.node]))

        
    def help_test_addition_with_array(self, operation):
        expected_names = ['A_0', 'B_1', 'C_2']
        expected_tree_str = """
letter: A
    number: 0
letter: B
    number: 1
letter: C
    number: 2"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_addition_with_array(self):
        self.help_test_addition_with_array(
            Plus(self.array, self.other_array))
        
    def test_incremental_addition_with_array(self):
        self.help_test_addition_with_array(
            PlusEquals(self.array, self.other_array))
        
    def test_sum_with_array(self):
        self.help_test_addition_with_array(
            Sum([self.array, self.other_array]))

        
    def help_test_multiplication_with_array(self, operation):
        expected_names = ['A_0', 'A_1', 'A_2',
                          'B_0', 'B_1', 'B_2',
                          'C_0', 'C_1', 'C_2']
        expected_tree_str = """
letter: A
    number: 0
    number: 1
    number: 2
letter: B
    number: 0
    number: 1
    number: 2
letter: C
    number: 0
    number: 1
    number: 2"""
        operation.check(self, expected_names, expected_tree_str)

    def test_multiplication_with_array(self):
        self.help_test_multiplication_with_array(
            Times(self.array, self.other_array))

    def test_incremental_multiplication_with_array(self):
        self.help_test_multiplication_with_array(
            TimesEquals(self.array, self.other_array))
        
    def test_product_with_array(self):
        self.help_test_multiplication_with_array(
            Product([self.array, self.other_array]))

        
    def help_test_addition_with_list(self, operation):
        expected_names = ['A_0', 'B_1', 'C_2']
        expected_tree_str = """
letter: A
    0
letter: B
    1
letter: C
    2"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_addition_with_list(self):
        self.help_test_addition_with_list(
            Plus(self.array, self.node_list))
        
    def test_incremental_addition_with_list(self):
        self.help_test_addition_with_list(
            PlusEquals(self.array, self.node_list))
        
    def test_sum_with_list(self):
        self.help_test_addition_with_list(
            Sum([self.array, self.node_list]))

        
    def test_update_with_options_dict(self):
        self.array.update(self.od)
        array_ods = self.array.collapse()
        for od in array_ods:
            self.assertEqual(od['foo'], 'bar')

    def test_update_with_options_dict_from_node(self):
        node_od = self.node.collapse()[0]
        self.array.update(node_od)
        array_ods = self.array.collapse()
        self.assertEqual([od.str() for od in array_ods],
                         ['A_0', 'B_0', 'C_0'])

    def test_update_with_options_dict_from_other_array(self):
        other_od = self.other_array.collapse()[1]
        self.array.update(other_od)
        array_ods = self.array.collapse()
        self.assertEqual([od.str() for od in array_ods],
                         ['A_1', 'B_1', 'C_1'])

    def test_collapse_and_freeze(self):
        self.array.update({'number': 2})
        add_dynamic_entry(self.array)
        ods = freeze(self.array.collapse())
        results = pool().map(Lookup('product'), ods)
        expected = [2, 4, 6]
        self.assertEqual(results, expected)

        
    # now test set-item operations.  Let's not linger on these.  If we
    # get what we expect for one or two operators, for both single
    # item and slice accessors, then OptionsArray.__setitem__ is doing
    # its job.

    def test_item_incremental_addition_with_node(self):
        expected_names = ['A', 'B_0', 'C']
        expected_tree_str = """
letter: A
letter: B
    0
letter: C"""
        op = PlusEquals(self.array, self.node, subscript=1)
        op.check(self, expected_names, expected_tree_str)
        
    def test_slice_incremental_addition_with_node(self):
        expected_names = ['A', 'B_0', 'C']
        expected_tree_str = """
letter: A
letter: B
    0
letter: C"""
        op = PlusEquals(self.array, self.node, subscript=slice(1, 3))
        op.check(self, expected_names, expected_tree_str)

        
    def test_item_incremental_multiplication_with_node(self):
        expected_names = ['A', 'B_0', 'C']
        expected_tree_str = """
letter: A
letter: B
    0
letter: C"""
        op = TimesEquals(self.array, self.node, subscript=1)
        op.check(self, expected_names, expected_tree_str)

        
    def test_slice_incremental_multiplication_with_node(self):
        expected_names = ['A', 'B_0', 'C_0']
        expected_tree_str = """
letter: A
letter: B
    0
letter: C
    0"""
        op = TimesEquals(self.array, self.node, subscript=slice(1, 3))
        op.check(self, expected_names, expected_tree_str)


        
class TestTreeOperations(unittest.TestCase):

    def setUp(self):
        letters = OptionsArray('letter', ['A', 'B'])
        numbers = OptionsArray('number', range(2))
        # putting dynamic entries on the leaves is the most rigorous
        # way of testing them after a tree collapse
        add_dynamic_entry(numbers)
        self.tree = letters * numbers
        self.node = OptionsNode('i')
        self.array = OptionsArray('subnumber', ['i', 'ii', 'iii'])
        self.node_list = [OptionsNode(name) for name in ['i', 'ii', 'iii']]
        self.od = OptionsDict({'foo': 'bar'})

        
    def help_test_addition_with_node(self, operation):
        expected_names = ['A_0_i', 'A_1', 'B_0', 'B_1']
        expected_tree_str = """
letter: A
    number: 0
        i
    number: 1
letter: B
    number: 0
    number: 1"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_addition_with_node(self):
        self.help_test_addition_with_node(
            Plus(self.tree, self.node))
        
    def test_incremental_addition_with_node(self):
        self.help_test_addition_with_node(
            PlusEquals(self.tree, self.node))
        
    def test_sum_with_node(self):
        self.help_test_addition_with_node(
            Sum([self.tree, self.node]))

        
    def help_test_multiplication_with_node(self, operation):
        expected_names = ['A_0_i', 'A_1_i', 'B_0_i', 'B_1_i']
        expected_tree_str = """
letter: A
    number: 0
        i
    number: 1
        i
letter: B
    number: 0
        i
    number: 1
        i"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_multiplication_with_node(self):
        self.help_test_multiplication_with_node(
            Times(self.tree, self.node))
        
    def test_incremental_multiplication_with_node(self):
        self.help_test_multiplication_with_node(
            TimesEquals(self.tree, self.node))
        
    def test_product_with_node(self):
        self.help_test_multiplication_with_node(
            Product([self.tree, self.node]))

        
    def help_test_addition_with_array(self, operation):
        expected_names = ['A_0_i', 'A_1_ii', 'B_0_iii', 'B_1']
        expected_tree_str = """
letter: A
    number: 0
        subnumber: i
    number: 1
        subnumber: ii
letter: B
    number: 0
        subnumber: iii
    number: 1"""
        operation.check(self, expected_names, expected_tree_str)

    def test_addition_with_array(self):
        self.help_test_addition_with_array(
            Plus(self.tree, self.array))

    def test_incremental_addition_with_array(self):
        self.help_test_addition_with_array(
            PlusEquals(self.tree, self.array))
        
    def test_sum_with_array(self):
        self.help_test_addition_with_array(
            Sum([self.tree, self.array]))

        
    def help_test_multiplication_with_array(self, operation):
        expected_names = ['A_0_i', 'A_0_ii', 'A_0_iii',
                          'A_1_i', 'A_1_ii', 'A_1_iii',
                          'B_0_i', 'B_0_ii', 'B_0_iii',
                          'B_1_i', 'B_1_ii', 'B_1_iii']
        expected_tree_str = """
letter: A
    number: 0
        subnumber: i
        subnumber: ii
        subnumber: iii
    number: 1
        subnumber: i
        subnumber: ii
        subnumber: iii
letter: B
    number: 0
        subnumber: i
        subnumber: ii
        subnumber: iii
    number: 1
        subnumber: i
        subnumber: ii
        subnumber: iii"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_multiplication_with_array(self):
        self.help_test_multiplication_with_array(
            Times(self.tree, self.array))

    def test_incremental_multiplication_with_array(self):
        self.help_test_multiplication_with_array(
            TimesEquals(self.tree, self.array))
        
    def test_product_with_array(self):
        self.help_test_multiplication_with_array(
            Product([self.tree, self.array]))

        
    def help_test_addition_with_list(self, operation):
        expected_names = ['A_0_i', 'A_1_ii', 'B_0_iii', 'B_1']
        expected_tree_str = """
letter: A
    number: 0
        i
    number: 1
        ii
letter: B
    number: 0
        iii
    number: 1"""
        operation.check(self, expected_names, expected_tree_str)
        
    def test_addition_with_list(self):
        self.help_test_addition_with_list(
            Plus(self.tree, self.node_list))

    def test_incremental_addition_with_list(self):
        self.help_test_addition_with_list(
            PlusEquals(self.tree, self.node_list))
        
    def test_sum_with_list(self):
        self.help_test_addition_with_list(
            Sum([self.tree, self.node_list]))

        
    def test_update_with_options_dict(self):
        self.tree.update(self.od)
        tree_ods = self.tree.collapse()
        for od in tree_ods:
            self.assertEqual(od['foo'], 'bar')

    def test_update_with_options_dict_from_node(self):
        node_od = self.node.collapse()[0]
        self.tree.update(node_od)
        tree_ods = self.tree.collapse()
        self.assertEqual([od.str() for od in tree_ods],
                         ['A_0_i', 'A_1_i', 'B_0_i', 'B_1_i'])

    def test_update_with_options_dict_from_array(self):
        array_od = self.array.collapse()[1]
        self.tree.update(array_od)
        tree_ods = self.tree.collapse()
        self.assertEqual([od.str() for od in tree_ods],
                         ['A_0_ii', 'A_1_ii', 'B_0_ii', 'B_1_ii'])

    def test_collapse_and_freeze(self):
        ods = freeze(self.tree.collapse())
        results = pool().map(Lookup('product'), ods)
        expected = [0, 1, 0, 2]
        self.assertEqual(results, expected)

    def test_count_leaves(self):
        self.assertEqual(self.tree.count_leaves(), 4)


    # now test set-item operations
            
    def test_item_incremental_addition_with_node(self):
        expected_names = ['A_0', 'A_1', 'B_0_i', 'B_1']
        expected_tree_str = """
letter: A
    number: 0
    number: 1
letter: B
    number: 0
        i
    number: 1"""
        op = PlusEquals(self.tree, self.node, subscript=1)
        op.check(self, expected_names, expected_tree_str)

        
    def test_slice_incremental_addition_with_node(self):
        expected_names = ['A_0', 'A_1', 'B_0_i', 'B_1']
        expected_tree_str = """
letter: A
    number: 0
    number: 1
letter: B
    number: 0
        i
    number: 1"""
        op = PlusEquals(self.tree, self.node, subscript=slice(1, 2))
        op.check(self, expected_names, expected_tree_str)

        
    def test_item_incremental_multiplication_with_node(self):
        expected_names = ['A_0', 'A_1', 'B_0_i', 'B_1_i']
        expected_tree_str = """
letter: A
    number: 0
    number: 1
letter: B
    number: 0
        i
    number: 1
        i"""
        op = TimesEquals(self.tree, self.node, subscript=1)
        op.check(self, expected_names, expected_tree_str)

        
    def test_slice_incremental_multiplication_with_node(self):
        expected_names = ['A_0', 'A_1', 'B_0_i', 'B_1_i']
        expected_tree_str = """
letter: A
    number: 0
    number: 1
letter: B
    number: 0
        i
    number: 1
        i"""
        op = TimesEquals(self.tree, self.node, subscript=slice(1, 2))
        op.check(self, expected_names, expected_tree_str)


            
if __name__ == '__main__':
    unittest.main()
