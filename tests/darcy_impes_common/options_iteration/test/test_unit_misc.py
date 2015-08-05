import unittest
from options_dict import Lookup, Str, freeze


class TestOptionsDictHelpers(unittest.TestCase):
    
    def test_lookup_functor(self):
        objs = [{'foo': 'bar'}] * 3
        results = map(Lookup('foo'), objs)
        self.assertEqual(results, ['bar'] * 3)

    def test_str_functor(self):
        class Stringifiable:
            def str(self, only=[], exclude=[], absolute={}, relative={}, 
                    formatter=None):
                return only + exclude + absolute + relative + formatter
        objs = [Stringifiable()] * 3
        functor = Str(only='a', exclude='b', absolute='c', relative='d',
                          formatter='e')
        results = map(functor, objs)
        self.assertEqual(results, ['abcde'] * 3)

    def setUp_freeze_test(self):
        class Freezable:
            def __init__(self):
                self.frozen = False
            def freeze(self):
                self.frozen = True
        self.objs = [Freezable()] * 3
        before = [obj.frozen for obj in self.objs]
        self.assertEqual(before, [False] * 3)
        
    def test_freeze(self):
        self.setUp_freeze_test()
        frozen_objs = freeze(self.objs)
        after = [obj.frozen for obj in frozen_objs]
        self.assertEqual(after, [True] * 3)

    def test_freeze_does_not_mutate_argument(self):
        self.setUp_freeze_test()
        freeze(self.objs)
        after = [obj.frozen for obj in self.objs]
        self.assertEqual(after, [False] * 3)

        
if __name__ == '__main__':
    unittest.main()
