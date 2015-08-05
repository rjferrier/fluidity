"""
Base module for test_functional_serial_iteration and
test_functional_parallel_iteration.
"""

import unittest
from tree_elements import OptionsNode, OptionsArray
from options_dict import OptionsDict, Lookup, Str, freeze

    
class TestOptionsDictCartesianProductIteration(unittest.TestCase):
    
    def setUp(self):
        """
        I create two OptionsDict arrays, one for 'speed' and one
        for 'travel time'.
        """
        speed = OptionsArray('speed', [30, 40, 60])
        time  = OptionsArray('travel_time', [0.5, 1])
        self.tree = speed * time
        self.expected_distances = [15, 30, 20, 40, 30, 60]

        
class TestOptionsDictTreeIteration(unittest.TestCase):

    def setUp(self):
        """
        Suppose I want to run a simulator on a set of 1D, 2D and 3D
        grids at different resolutions, but it is expensive to do this
        on multi-dimensional grids at higher resolutions.  I decide to
        iterate over the following combinations:

            dim.   res.
             1     10, 20, 40, 80
             2     10, 20, 40
             3     10, 20

        This should be possible using the attach and product
        functions.  I will implement a dynamic entry at the root of
        the tree to calculate the computational cost.
        """
        dims = OptionsArray('dim', [1, 2, 3], name_format='{}d')
        res1d = OptionsArray('res', [10, 20, 40, 80])
        res2d = OptionsArray('res', [10, 20, 40])
        res3d = OptionsArray('res', [10, 20])
        root = OptionsNode('sim', {
            'cost': lambda opt: opt['res']**opt['dim']})
        self.tree = root + dims + (res1d, res2d, res3d)
        self.options_dicts = self.tree.collapse()

    def check_names(self, resulting_names):
        "Helper for name_check tests."
        expected_names = [
            'sim_1d_10', 'sim_1d_20', 'sim_1d_40', 'sim_1d_80', 
            'sim_2d_10', 'sim_2d_20', 'sim_2d_40',
            'sim_3d_10', 'sim_3d_20']
        for result, expected in zip(resulting_names, expected_names):
            self.assertEqual(result, expected)

    def check_times(self, resulting_times):
        "Helper for lookup tests."
        expected_times = [
            10., 20., 40., 80.,
            100., 400., 1600.,
            1000., 8000.]
        for result, expected in zip(resulting_times, expected_times):
            self.assertAlmostEqual(result, expected)
    
