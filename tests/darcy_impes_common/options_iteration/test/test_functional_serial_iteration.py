from test_functional_common import *
import unittest


class TestOptionsDictCartesianProductSerialIteration(
        TestOptionsDictCartesianProductIteration):
    """
    The base test fixture is defined in test_functional_common.
    """

    def test_manual_iteration(self):
        """
        I want to iterate over all combinations of speed and time and
        calculate distance for each combination.
        """
        options_dicts = self.tree.collapse()
        for od, expected in zip(self.tree.collapse(),
                                self.expected_distances):
            result = od['speed'] * od['travel_time']
            self.assertAlmostEqual(result, expected)
            
    def test_manual_iteration_with_extra_dict_and_dynamic_entry(self):
        """
        I define distance as a dynamic entry and pass a corresponding
        Lookup functor to a serial map.
        """
        self.tree.update({'distance': lambda opt: \
                          opt['speed'] * opt['travel_time']})
        for od, expected in zip(self.tree.collapse(),
                                 self.expected_distances):
            self.assertAlmostEqual(od['distance'], expected)

    def test_mapping(self):
        """
        I want to create combinations of speed and travel time and
        calculate the correct distances using a map.
        """
        def distance_func(opt):
            return opt['speed'] * opt['travel_time']
        results = map(distance_func, self.tree.collapse())
        self.assertAlmostEqual(results, self.expected_distances)


class TestOptionsDictTreeSerialIteration(TestOptionsDictTreeIteration):
        
    def test_manual_iteration_and_name_check(self):
        resulting_names = []
        for od in self.tree.collapse():
            resulting_names.append(str(od))
        self.check_names(resulting_names)

    def test_manual_iteration_and_lookup(self):
        resulting_times = []
        for od in self.tree.collapse():
            resulting_times.append(od['cost'])
        self.check_times(resulting_times)

    def test_mapping_and_name_check(self):
        resulting_names = map(Str(), self.tree.collapse())
        self.check_names(resulting_names)
            
    def test_mapping_and_lookup(self):
        resulting_times = map(Lookup('cost'), self.tree.collapse())
        self.check_times(resulting_times)
            
            
if __name__ == '__main__':
    unittest.main()
        
