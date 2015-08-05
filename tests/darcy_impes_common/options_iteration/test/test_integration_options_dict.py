import unittest
from options_dict import OptionsDict, CallableEntry, OptionsDictException
from node_info import SimpleFormatter, TreeFormatter
from tree_elements import OptionsNode, OptionsArray


class TestOptionsDictBasics(unittest.TestCase):

    def setUp(self):
        self.od = OptionsDict({})
        
    def test_str(self):
        """
        Because there is no node information, str() should return an empty
        string.
        """
        self.assertEqual(str(self.od), '')
    
    def test_create_node_info_formatter_simple(self):
        self.assertIsInstance(
            self.od.create_node_info_formatter('simple'), SimpleFormatter)

    def test_create_node_info_formatter_tree(self):
        self.assertIsInstance(
            self.od.create_node_info_formatter('tree'), TreeFormatter)

    def test_create_node_info_formatter_error(self):
        self.assertRaises(
            OptionsDictException, 
            lambda: self.od.create_node_info_formatter('madethisup'))
        


class TestOptionsDictInteractionsWithNode(unittest.TestCase):

    def setUp(self):
        self.node = OptionsNode('foo')
        self.od = OptionsDict(entries={'bar': 1})

    def test_donate_copy(self):
        """
        Passing a node to OptionsDict's donate_copy method should furnish
        the node with dictionary information.
        """
        od_init = self.od.copy()
        self.node, remainder = self.od.donate_copy(self.node)
        node_od = self.node.collapse()[0]
        self.assertEqual(node_od['bar'], 1)
        self.assertEqual(len(remainder), 0)


class TestOptionsDictAfterTreeCollapse(unittest.TestCase):

    def setUp(self):
        """
        Run tests on this tree:
        0: a
            1: a
                2: a
                2: b
                2: c
            1: b
                2: a
                2: b
                2: c
        """
        self.tree = OptionsArray('0', ['a']) * \
                    OptionsArray('1', ['a', 'b']) * \
                    OptionsArray('2', ['a', 'b', 'c'])
        
    def test_str_tree(self):
        ods = self.tree.collapse()
        expected = """
0: a
    1: a
        2: a
        2: b
        2: c
    1: b
        2: a
        2: b
        2: c"""
        result = ''.join(['\n' + od.str(formatter='tree') for od in ods])
        self.assertEqual(result, expected)

        
    def test_indent(self):
        ods = self.tree.collapse()
        expected = ('\n' + ' '*12)*6
        result = ''.join(['\n' + od.indent() for od in ods])
        self.assertEqual(result, expected)

        
        
class TestCallableEntry(unittest.TestCase):
    
    def test_callable_entry(self):
        """
        I create an OptionsDict with a callable entry stored under
        'my_func'.  This should not evaluate like a dynamic entry but
        instead remain intact and work as intended.
        """
        od = OptionsDict({
            'my_func': CallableEntry(lambda a, b=1: a + b)})
        self.assertIsInstance(od['my_func'], CallableEntry)
        self.assertEqual(od['my_func'](1), 2)
        self.assertEqual(od['my_func'](1, 2), 3)

        
if __name__ == '__main__':
    unittest.main()
