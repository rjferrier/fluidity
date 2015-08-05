import sys
sys.path.append('..')

import unittest
from tools import flatten, attach, product, merge, merges_dicts, Lookup


class TestIterationTools(unittest.TestCase):

    def help_flatten(self, persistent):
        tree = [1, ["a string", [{'a': 'dict'}, 4], 5]]
        expected = (1, "a string", {'a': 'dict'}, 4, 5)
        result = flatten(tree, persistent)
        return result, expected
    
    def test_flatten_persistent(self):
        result, expected = self.help_flatten(True)
        self.assertEqual(tuple(result), expected)
        self.assertEqual(tuple(result), expected)
        
    def test_flatten_nonpersistent(self):
        result, expected = self.help_flatten(False)
        self.assertEqual(tuple(result), expected)
        # the implicit iteration in the previous statement should have
        # depleted the result
        self.assertNotEqual(tuple(result), expected)
        self.assertEqual(len(tuple(result)), 0)
        
    def help_attach(self, persistent):
        parents = ('A', ('B', 'C'))
        children = ((1, 2, 3), (4, 5))
        expected = (('A', 1), ('A', 2), ('A', 3),
                    ('B', 4), ('B', 5),
                    ('C', 4), ('C', 5))
        result = attach(parents, children, persistent)
        return result, expected
        
    def test_attach_persistent(self):
        result, expected = self.help_attach(True)
        self.assertEqual(tuple(result), expected)
        self.assertEqual(tuple(result), expected)
        
    def test_attach_nonpersistent(self):
        result, expected = self.help_attach(False)
        self.assertEqual(tuple(result), expected)
        # the implicit iteration in the previous statement should have
        # depleted the result
        self.assertNotEqual(tuple(result), expected)
        self.assertEqual(len(tuple(result)), 0)

    def test_attach_with_strings_and_dicts(self):
        parents = ('A', 'bee', {'C': 'see'})
        children = ((1, 'two'), ({3: 'three'}, 4, 5), (6,))
        expected = (('A', 1), ('A', 'two'),
                    ('bee', {3: 'three'}), ('bee', 4), ('bee', 5),
                    ({'C': 'see'}, 6))
        result = attach(parents, children)
        self.assertEqual(tuple(result), expected)

    def help_product(self, persistent):
        iterables = (('A', 'B'), (1, 2, 3))
        expected = (('A', 1), ('A', 2), ('A', 3),
                    ('B', 1), ('B', 2), ('B', 3))
        result = product(*iterables, persistent=persistent)
        return result, expected

    def test_product_persistent(self):
        result, expected = self.help_product(True)
        self.assertEqual(tuple(result), expected)
        self.assertEqual(tuple(result), expected)
        
    def test_product_nonpersistent(self):
        result, expected = self.help_product(False)
        self.assertEqual(tuple(result), expected)
        # the implicit iteration in the previous statement should have
        # depleted the result
        self.assertNotEqual(tuple(result), expected)
        self.assertEqual(len(tuple(result)), 0)

            
class TestDictTools(unittest.TestCase):

    def setUp(self):
        self.d1 = {'a': 1, 'b': 1, 'c': 1}
        self.d2 = {'a': 2, 'b': 2}
        self.d3 = {'a': 3}
        self.dicts = [self.d1, self.d2, self.d3]
    
    def test_merge(self):
        d = merge(self.dicts)
        self.assertEqual(d['c'], 1)
        self.assertEqual(d['a'], 3)
    
    def test_merge_single_dict(self):
        d = merge(self.d1)
        self.assertEqual(d['c'], 1)
        self.assertEqual(d['a'], 1)
    
    def test_merges_dicts(self):
        @merges_dicts
        def myfunc(d):
            return d['a'] + d['b'] + d['c']
        self.assertEqual(myfunc(self.dicts), 6)
    
    def test_create_lookup(self):
        lookup = Lookup('c')
        self.assertEqual(lookup(self.dicts), 1)
        lookup = Lookup('a')
        self.assertEqual(lookup(self.dicts), 3)

        
if __name__ == '__main__':
    unittest.main()
