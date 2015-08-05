from test_functional_common import *
from multiprocessing import Pool


def pool():
    return Pool(2)

def distance_func(opt):
    return opt['speed'] * opt['travel_time']

    
class TestOptionsDictCartesianProductParallelIteration(
        TestOptionsDictCartesianProductIteration):

    def test_mapping(self):
        """
        I pass distance_func to a multiprocessing map.  Note that
        distance_func must be a global, named function to avoid
        pickling errors (which is why it resides outside the present
        test class)
        """
        options_dicts = self.tree.collapse()
        results = pool().map(distance_func, freeze(options_dicts))
        self.assertAlmostEqual(results, self.expected_distances)
            
    def test_mapping_with_extra_dict_and_dynamic_entry(self):
        """
        I define distance as a dynamic entry and pass a corresponding
        Lookup functor to a multiprocessing map.
        """
        self.tree.update({'distance': lambda opt: \
                          opt['speed'] * opt['travel_time']})
        options_dicts = self.tree.collapse()
        results = pool().map(Lookup('distance'), freeze(options_dicts))
        self.assertAlmostEqual(results, self.expected_distances)


class TestOptionsDictTreeParallelIteration(
        TestOptionsDictTreeIteration):
            
    def test_mapping_and_name_check(self):
        resulting_names = pool().map(Str(), freeze(self.options_dicts))
        self.check_names(resulting_names)
            
    def test_mapping_and_lookup(self):
        resulting_times = pool().map(Lookup('cost'), freeze(self.options_dicts))
        self.check_times(resulting_times)

            
if __name__ == '__main__':
    unittest.main()
