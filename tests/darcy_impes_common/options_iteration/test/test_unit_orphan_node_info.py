import unittest
from node_info import OrphanNodeInfo


class TestOrphanNodeInfoString(unittest.TestCase):

    def setUp(self):
        """
        I create an OrphanNodeInfo object.
        """
        self.node_info = OrphanNodeInfo('A')

    def test_belongs_to(self):
        """
        The node should test negative for belonging to anything.
        """
        self.assertFalse(self.node_info.belongs_to('A'))

    def test_belongs_to_any(self):
        """
        Similar to belongs_to test.
        """
        self.assertFalse(self.node_info.belongs_to_any(['A', 'B']))

    def test_node_name(self):
        """
        I should be able to recover the name of the node from both the
        __str__ and str() methods.
        """
        self.assertEqual(self.node_info.str(), 'A')
        self.assertEqual(str(self.node_info), 'A')

    def test_other_node_name_from_absolute_index(self):
        """
        There is only one node.  Asking str() for the first or last node
        name should get the same result; anything else should trigger an
        error.
        """
        self.assertEqual(self.node_info.str(0), 'A')
        self.assertEqual(self.node_info.str(-1), 'A')
        self.assertRaises(IndexError, lambda: self.node_info.str(1))

    def test_other_node_name_from_relative_index(self):
        """
        Only a relative index of 0 should be valid.
        """
        self.assertEqual(self.node_info.str(relative=0), 'A')
        self.assertRaises(IndexError,
                          lambda: self.node_info.str(relative=-1))

    def test_other_node_name_from_relative_and_absolute_index(self):
        """
        Strictly speaking, using both a relative and absolute index
        should work, but a resulting negative index will raise an
        IndexError.
        """
        self.assertEqual(self.node_info.str(relative=-1, absolute=1), 'A')
        self.assertRaises(
            IndexError, lambda: self.node_info.str(relative=-2, absolute=1))

    def test_other_node_name_from_absolute_index_in_dict(self):
        """
        The absolute index might be supplied via a dictionary of entries
        in the form {collection_name: index}.  Here the node name will
        default.
        """
        self.assertEqual(self.node_info.str({'foo': -1}), 'A')

    def test_other_node_name_from_relative_index_in_dict(self):
        """
        The relative index might be supplied via a dictionary of entries
        in the form {collection_name: index}.  Here the node name will
        default.
        """
        self.assertEqual(self.node_info.str(relative={'foo': 1}), 'A')
        

class TestOrphanNodeInfoIndex(unittest.TestCase):
    
    def setUp(self):
        """
        I create an OrphanNodeInfo object.
        """
        self.node_info = OrphanNodeInfo('A')
    
    def test_at(self):
        # check positions from start 
        self.assertTrue(self.node_info.at(0))
        self.assertFalse(self.node_info.at(1))
        # check position from end
        self.assertFalse(self.node_info.at(-2))
        self.assertTrue(self.node_info.at(-1))
    
    def test_is_first(self):
        self.assertTrue(self.node_info.is_first())
    
    def test_is_last(self):
        self.assertTrue(self.node_info.is_last())


        
if __name__ == '__main__':
    unittest.main()
        
