import unittest
from unit_tree_elements import UnitOptionsNode
from tree_elements import OptionsNodeException


class TestOptionsNodeCreation(unittest.TestCase):

    def test_create_node_from_non_string(self):
        """
        When I create a node using something other than a string, an
        error should be raised.
        """
        create_node = lambda: UnitOptionsNode({'foo': 'bar'})
        self.assertRaises(OptionsNodeException, create_node)

    def test_create_node_with_bad_child(self):
        """
        When I create a node with a child that is not another
        OptionsTreeElement, an error should be raised.
        """
        create_node = lambda: UnitOptionsNode('foo', child='bar')
        self.assertRaises(OptionsNodeException, create_node)

    def test_create_node_from_non_class(self):
        """
        When I create a node using class method from_node and passing in
        something other than a class, an error should be raised.
        """
        class some_node:
            foo = 'bar'
        # some_node() instantiates an object from the class - this
        # should fail as such object won't have a name.
        create_node = lambda: UnitOptionsNode(some_node())
        self.assertRaises(OptionsNodeException, create_node)
        
        
class TestOptionsNodeBasics(unittest.TestCase):

    @staticmethod
    def make_node(name='foo', entries={'bar': 1},
                  child=UnitOptionsNode('qux')):
        return UnitOptionsNode(name, entries, child)
    
    def setUp(self):
        self.node = self.make_node()

    def test_equal(self):
        self.assertEqual(self.node, self.make_node())

    def test_unequal_names(self):
        self.assertNotEqual(self.node,
                            self.make_node(name='baz'))

    def test_unequal_dicts(self):
        self.assertNotEqual(self.node, 
                            self.make_node(entries={'bar': 2}))

    def test_unequal_dicts(self):
        self.assertNotEqual(self.node, 
                            self.make_node(child=UnitOptionsNode('baz')))

    def test_copy(self):
        other = self.node.copy()
        # test for equivalence and non-identity
        self.assertEqual(other, self.node)
        self.assertFalse(other is self.node)

    def test_str(self):
        self.assertEqual(str(self.node), 'foo')

    def test_donate_copy(self):
        node_init = self.node.copy()
        acceptor = UnitOptionsNode('baz')
        acceptor, remainder = self.node.donate_copy(acceptor)
        self.assertEqual(acceptor.child, node_init)
        self.assertEqual(len(remainder), 0)        

    def test_count_leaves(self):
        self.assertEqual(self.node.count_leaves(), 1)        

    def test_compare_with_node_from_class(self):
        """
        This can be done as long as there aren't any dynamic entries.
        Dynamic entries are created from functions, and functions
        created in different contexts aren't equal.
        """
        class foo:
            bar = 1
        class qux: 
            pass
        node_from_class = UnitOptionsNode(foo, child=UnitOptionsNode(qux))
        self.assertEqual(node_from_class, self.node)

        
if __name__ == '__main__':
    unittest.main()
        
