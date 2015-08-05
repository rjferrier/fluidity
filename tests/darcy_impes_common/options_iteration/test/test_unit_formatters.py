import unittest
from node_info import SimpleFormatter, TreeFormatter
from itertools import product


class FakeNodeInfo:
    """
    For representing a node on this tree:
    0: a
        1: a
            2: a ...
    """
    ref_nodes = list('abcd')

    def __init__(self, level, node_name, node_index):
        self.level = level
        self.node_name = node_name
        self.node_index = node_index

    @classmethod
    def combo(Self, node_names, anon=[]):
        result = []
        for i, node_name in enumerate(node_names):
            node_index = Self.ref_nodes.index(node_name)
            if i in anon:
                node_name = None
            result.append(Self(i, node_name, node_index))
        return result

    def str(self, absolute=None, relative=None, collection_separator=None):
        if not self.node_name:
            return ''
        result = ''
        if collection_separator:
            result += str(self.level) + collection_separator
        return result + self.node_name

    def is_first(self):
        return self.node_index == 0

        
class TestSimpleFormatter(unittest.TestCase):

    def setUp(self):
        self.formatter = SimpleFormatter()

    def test_simple_formatter(self):
        self.node_info = FakeNodeInfo.combo('abc')
        self.assertEqual(self.formatter(self.node_info), 'a_b_c')

    def test_simple_formatter_with_anonymous_middle_node(self):
        self.node_info = FakeNodeInfo.combo('abc', anon=[1])
        self.assertEqual(self.formatter(self.node_info), 'a_c')

    def test_simple_formatter_with_anonymous_first_two_nodes(self):
        self.node_info = FakeNodeInfo.combo('abc', anon=[0, 1])
        self.assertEqual(self.formatter(self.node_info), 'c')

    def test_simple_formatter_with_custom_separator(self):
        self.node_info = FakeNodeInfo.combo('abc')
        self.formatter = SimpleFormatter(',')
        self.assertEqual(self.formatter(self.node_info), 'a,b,c')


class TestTreeFormatter(unittest.TestCase):

    def make_tree(self, node_combos, anon=[], formatter=TreeFormatter()):
        result = ''
        for c in node_combos:
            branch = formatter(FakeNodeInfo.combo(c, anon))
            if branch:
                result += '\n' + branch
        return result

    def make_indents(self, node_combos, anon=[], formatter=TreeFormatter()):
        result = ''
        for c in node_combos:
            indent = formatter(FakeNodeInfo.combo(c, anon), only_indent=True)
            if indent:
                result += '\n' + indent
        return result
        

        
class TestTreeFormatterWithThreeLevels(TestTreeFormatter):

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
        self.node_combos = product('a', 'ab', 'abc')


    def test_tree_formatter_first_combo(self):
        """
        I want to print part of the tree associated with the very first
        node combination, [a,a,a].
        """
        expected = """
0: a
    1: a
        2: a"""
        self.assertEqual(self.make_tree(['aaa']), expected)


    def test_tree_formatter_intermediate_combo(self):
        """
        I want to print part of the tree associated with an intermediate
        combination, [a,b,a].
        """
        expected = """
    1: b
        2: a"""
        self.assertEqual(self.make_tree(['aba']), expected)


    def test_tree_formatter_leaf_combo(self):
        """
        I want to print e.g. [a,a,b] which does not have any preamble when
        it is printed.
        """
        expected = """
        2: b"""
        self.assertEqual(self.make_tree(['aab']), expected)


    def test_tree_formatter_intermediate_combo_with_custom_separator(self):
        formatter = TreeFormatter(collection_separator='-')
        expected = """
    1-b
        2-a"""
        self.assertEqual(self.make_tree(['aba'], formatter=formatter),
                         expected)


    def test_tree_formatter_intermediate_combo_omitting_collection_names(self):
        """
        I want to omit the collection names altogether, so I'll specify
        the collection separator as None.
        """
        formatter = TreeFormatter(collection_separator=None)
        expected = """
    b
        a"""
        self.assertEqual(self.make_tree(['aba'], formatter=formatter),
                         expected)


    def test_tree_formatter_intermediate_combo_with_custom_indent(self):
        formatter = TreeFormatter(indent_string='...')
        expected = """
...1: b
......2: a"""
        self.assertEqual(self.make_tree(['aba'], formatter=formatter),
                         expected)
        
        
    def test_tree_formatter_all(self):
        """
        I want to print the entire tree.
        """
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
        self.assertEqual(self.make_tree(self.node_combos), expected)


    def test_tree_formatter_all_with_anonymous_first_node(self):
        expected = """
1: a
    2: a
    2: b
    2: c
1: b
    2: a
    2: b
    2: c"""
        self.assertEqual(self.make_tree(self.node_combos, anon=[0]), expected)


    def test_tree_formatter_all_with_anonymous_intermediate_node(self):
        expected = """
0: a
    2: a
    2: b
    2: c
    2: a
    2: b
    2: c"""
        self.assertEqual(self.make_tree(self.node_combos, anon=[1]),
                         expected)

        
    def test_tree_formatter_all_with_anonymous_end_node(self):
        expected = """
0: a
    1: a
    1: b"""
        self.assertEqual(self.make_tree(self.node_combos, anon=[2]),
                         expected)
        
        
    def test_tree_formatter_indent(self):
        """
        Indent so I can print stuff between the leaves.
        """
        expected = ('\n' + ' '*12) * 6
        self.assertEqual(self.make_indents(self.node_combos), expected)

        
        
class TestTreeFormatterWithFourLevels(TestTreeFormatter):

    def setUp(self):
        """
        Run tests on this tree:
        0: a
            1: a
                2: a
                    3: a
                2: b
                    3: a
            1: b
                2: a
                    3: a
                2: b
                    3: a
        """
        self.node_combos = product('a', 'ab', 'ab', 'a')
        

    def test_tree_formatter_four_levels_with_anonymous_second_node(self):
        expected = """
0: a
    2: a
        3: a
    2: b
        3: a
    2: a
        3: a
    2: b
        3: a"""
        results = self.make_tree(self.node_combos, anon=[1])
        self.assertEqual(results, expected)
        
        
    def test_tree_formatter_four_levels_with_anonymous_third_node(self):
        expected = """
0: a
    1: a
        3: a
        3: a
    1: b
        3: a
        3: a"""
        results = self.make_tree(self.node_combos, anon=[2])
        self.assertEqual(results, expected)
        
        
    def test_tree_formatter_indent(self):
        """
        Indent so I can print stuff between the leaves.
        """
        expected = ('\n' + ' '*16) * 4
        self.assertEqual(self.make_indents(self.node_combos), expected)

        
class TestEmptyNodeInfo(unittest.TestCase):

    def test_simple_formatter(self):
        self.assertEqual(SimpleFormatter()([]), '')

    def test_tree_formatter(self):
        self.assertEqual(TreeFormatter()([]), '')


if __name__ == '__main__':
    unittest.main()
        
