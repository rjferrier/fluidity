import sys
sys.path.append('..')

import unittest
from options_dict import OptionsDict, OptionsDictException
from node_info import OrphanNodeInfo
        

class TestOptionsDictOrphanNodeCreation(unittest.TestCase):

    def test_create_node_from_non_string(self):
        """
        When I create a node using something other than a string, an error
        should be raised.
        """
        create_od = lambda: OptionsDict.node({'foo': 'bar'})
        self.assertRaises(OptionsDictException, create_od)

        
class TestOptionsDictOrphanNodeBasics(unittest.TestCase):

    def setUp(self):
        """I create an OptionsDict node."""
        self.od = OptionsDict.node('foo', {'bar': 1})

    def test_equal_names_and_dicts(self):
        self.assertEqual(self.od,
                         OptionsDict.node('foo', {'bar': 1}))

    def test_equal_names_but_unequal_dicts(self):
        self.assertNotEqual(self.od,
                            OptionsDict.node('foo', {'bar': 2}))

    def test_unequal_names_but_equal_dicts(self):
        self.assertNotEqual(self.od,
                            OptionsDict.node('baz', {'bar': 1}))

    def test_copy(self):
        other = self.od.copy()
        # test for equivalence and non-identity
        self.assertEqual(other, self.od)
        self.assertFalse(other is self.od)
        # test that name components have been copied and not simply
        # linked
        other.update(OptionsDict.node('baz'))
        self.assertNotEqual(other, self.od)

    def test_default_str(self):
        """
        Calling the __str__ idiom and the str() method with no arguments
        should just return the name.
        """
        self.assertEqual(str(self.od), 'foo')
        self.assertEqual(self.od.str(), 'foo')


class TestOptionsDictOrphanNodeInfo(unittest.TestCase):

    def setUp(self):
        """
        I create an OptionsDict node and get its node info object.
        """
        self.od = OptionsDict.node('foo', {'bar': 1})
        self.node_info = self.od.get_node_info()

    def test_node_info_type(self):
        """
        The stored node info should be an instance of OrphanNodeInfo.
        """
        self.assertIsInstance(self.node_info, OrphanNodeInfo)

    def test_str(self):
        """
        The string representation of the node info should be the same as
        that of the OptionsDict.
        """
        self.assertEqual(str(self.node_info), str(self.od))

    def test_copy(self):
        other = self.od.copy()
        # test for equivalence and non-identity
        self.assertEqual(other, self.od)
        self.assertFalse(other is self.od)

        
class TestUpdateFromOrphanNode(unittest.TestCase):
        
    def setUp(self):
        """
        I create and store an OptionsDict node.  I create another
        OptionsDict node, with one entry duplicating a key from the
        stored dict but having a different corresponding value.  I
        update the stored dict with the other dict.
        """
        self.od = OptionsDict.node('A', {'foo': 1, 'bar': 2})
        other = OptionsDict.node('B', {'foo': 3, 'baz': 4})
        self.od.update(other)
        
    def test_name(self):
        self.assertEqual(str(self.od), 'A_B')

    def test_right_overrides_left(self):
        """
        Looking up the shared key should return the other dict's value.
        """
        self.assertEqual(self.od['foo'], 3)

        
class TestUpdateFromDict(unittest.TestCase):
    
    def setUp(self):
        """
        I create and store an OptionsDict node.  I create a standard dict,
        with one entry duplicating a key from the stored dict but
        having a different corresponding value.  I update the stored
        dict with the other dict.
        """
        self.od = OptionsDict.node('A', {'foo': 1, 'bar': 2})
        other = {'foo': 3, 'baz': 4}
        self.od.update(other)
        
    def test_name(self):
        self.assertEqual(str(self.od), 'A')

        
    
if __name__ == '__main__':
    unittest.main()
        
