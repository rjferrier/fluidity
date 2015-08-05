import unittest
from tree_elements import OptionsNode
from options_dict import OptionsDict, OptionsDictException
from node_info import OrphanNodeInfo
    

class TestOptionsNodeCreation(unittest.TestCase):

    def test_create_with_bad_common_entries(self):
        """
        I create an OptionsNode using something that is not a dictionary
        for the entries argument.  An error should be raised.
        """
        create_node = lambda: OptionsNode('A', 'foo')
        self.assertRaises(OptionsDictException, create_node)


class TestOptionsNodeBasics(unittest.TestCase):

    def setUp(self):
        self.node = OptionsNode('B', {'foo': 1})

    def test_create_options_dict(self):
        od = self.node.create_options_dict({'bar': 2})
        self.assertIsInstance(od, OptionsDict)
        self.assertEqual(od['bar'], 2)

    def test_create_info(self):
        ni = self.node.create_info()
        self.assertIsInstance(ni, OrphanNodeInfo)
        self.assertEqual(str(ni), 'B')

    def test_collapse(self):
        ods = self.node.collapse()
        self.assertEqual(len(ods), 1)
        od = ods[0]
        self.assertIsInstance(od, OptionsDict)
        self.assertEqual(od['foo'], 1)


class TestOrphanNodeAfterCollapse(unittest.TestCase):

    def setUp(self):
        """
        I create a node and collapse it, which should leave an OptionsDict
        with OrphanNodeInfo.
        """
        node = OptionsNode('A', {'foo': 'bar'})
        self.od = node.collapse()[0]

    def test_type(self):
        self.assertIsInstance(self.od, OptionsDict)

    def test_name(self):
        self.assertEqual(str(self.od), 'A')

    def test_contents(self):
        self.assertEqual(self.od['foo'], 'bar')

    def test_node_info_name(self):
        ni = self.od.get_node_info()
        self.assertEqual(ni.str(), 'A')


class TestOrphanNodeFromClassAfterCollapse(unittest.TestCase):
    """
    Repeat the setup and key tests from TestOrphanNodeAfterCollapse,
    this time creating the node from a class.
    """

    def setUp(self):
        class A:
            foo = 'bar'
        node = OptionsNode(A)
        self.od = node.collapse()[0]

    def test_contents(self):
        self.assertEqual(self.od['foo'], 'bar')

    def test_node_info_name(self):
        ni = self.od.get_node_info()
        self.assertEqual(ni.str(), 'A')


if __name__ == '__main__':
    unittest.main()
