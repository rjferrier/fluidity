import darcy_impes_base as base
import darcy_impes_runner as runner
from opiter import OptionsArray, OptionsNode, Remove, missing_dependencies
from copy import deepcopy


#------------------------------------------------------------------------------
# fields to be iterated over in postprocessing

class pressure2:
    phase_name = 'Phase2'
    variable_name = 'Pressure'
    error_tolerance = 0.1 * 1.e6

class saturation2:
    phase_name = 'Phase2'
    variable_name = 'Saturation'
    error_tolerance = 0.1

examined_fields = OptionsArray('field', [pressure2, saturation2])


#------------------------------------------------------------------------------
# cases

class p1satdiag:
    gravity_magnitude = None
    residual_saturations = None
    initial_saturation2 = 0.
    density2 = 1.
    # see note 1
    examined_fields = examined_fields.collapse()

class withgrav_updip:
    gravity_magnitude = 1.5e6
    residual_saturations = (0.1, 0.1)
    initial_saturation2 = 0.1
    density2 = 2.
    # cut out the pressure field for this case as we do not have the
    # reference solution
    examined_fields = examined_fields[1:2].collapse()
    
cases = OptionsArray('case', [p1satdiag, withgrav_updip])



#---------------------------------------------------------------------
# common to all

# extend the class of the same name in darcy_impes_options
class common(base.common):
    
    # don't really care about element numbers in y and z
    def element_numbers(self):
        return [self.mesh_res, 2, 2]
    
    def gravity_direction(self):
        result = [0] * self.dim_number
        result[0] = -1
        return result
    
    relperm_relation_name = 'PowerLaw'
    relperm_relation_exponents = (2, 2)

    user_id = 'rferrier'
    test_length = 'short'          # TODO: change to medium?

    # prefer the l1-norm or integral to the l2 norm because the
    # discontinuity causes error spikes which are accentuated by the
    # latter
    error_aggregation = 'integral'

    
# make an anonymous root node to store the above options
root = OptionsNode(item_hooks=[Remove(missing_dependencies)])
root.update(common)


#------------------------------------------------------------------------------
# TREE ASSEMBLY

# for MMS tests we usually assign mesh resolutions [10, 20, 40, 80] to
# 1D, [10, 20, 40] to 2D, etc.  But in the BL case the solution
# discontinuity makes the convergence very noisy, especially when
# there are fewer grid points.  So calculate the convergence rate over
# three resolution doublings in 1D and two doublings in 2D.
base.dims['1d'] *= OptionsArray('mesh_res', [10, 80])
base.dims['2d'] *= OptionsArray('mesh_res', [10, 40])
base.dims['3d'] *= OptionsArray('mesh_res', [10, 20])

# create meshing tree from the array of problem dimensions
mesh_options_tree = root * base.dims

# the simulation tree adds cases and face controls
sim_options_tree = root * cases * base.face_controls * base.dims

# with the testing tree, we're additionally interested in certain
# fields for certain cases.
test_options_tree = deepcopy(sim_options_tree)
test_options_tree['p1satdiag'] *= examined_fields[0:2]
test_options_tree['withgrav_updip'] *= examined_fields[1:2]


#------------------------------------------------------------------------------
# DISPATCH

if __name__ == '__main__':
    runner.main(mesh_options_tree,
                sim_options_tree,
                test_options_tree)

    
# Notes:
# 
# [1] Each simulation needs to compute all of the fields in
# examined_fields before we iterate over them at the postprocessing
# stage.  One way of storing this information is to convert
# examined_fields to a list of dictionaries.
