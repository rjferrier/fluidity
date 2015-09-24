import darcy_impes_options as base
from options_iteration import OptionsArray, OptionsNode
from options_iteration.utilities import smap, pmap, ExpandTemplate, RunProgram,\
    Jinja2Rendering, get_nprocs
from darcy_impes_functors import WriteXml, StudyConvergence
import os
import errno
import sys


## SETTINGS

problem_name = 'darcy_impes_p1_2phase_bl'
simulation_naming_keys = ['case', 'submodel', 'dim', 'mesh_res']
nprocs_max = 6

mesh_dir = 'meshes'
simulation_dir = 'simulations'
reference_solution_dir = 'reference_solution'

        
## OPTIONS TREES

# initialise top level of tree for meshing
mesh_options_tree = OptionsArray('dim', [base.dim1, base.dim2, base.dim3], 
                                 name_format=lambda s: s[-1]+'d')

# for MMS tests we usually assign mesh resolutions [10, 20, 40, 80] to
# 1D, [10, 20, 40] to 2D, etc.  But in the BL case the solution
# discontinuity makes the convergence very noisy, especially when
# there are fewer grid points.  So calculate the convergence rate over
# three resolution doublings in 1D and two doublings in 2D.
mesh_options_tree[0] *= OptionsArray('mesh_res', [10, 80])
mesh_options_tree[1] *= OptionsArray('mesh_res', [10, 40])
mesh_options_tree[2] *= OptionsArray('mesh_res', [10, 20])


class ExaminedField:
    """
    Helper structure recording a field's phase number, variable name
    and details of its reference solution.  The field will be examined
    for convergence.
    """
    def __init__(self, case, variable_name, phase_number):
        self.field = variable_name.lower() + str(phase_number)
        self.variable_name = variable_name
        self.reference_solution_filename = '{}/{}_{}.txt'.format(
            reference_solution_dir, case, self.field)

class p1satdiag:
    gravity_magnitude = None
    initial_saturation2 = 0.
    density2 = 1.
    examined_fields = [
        ExaminedField('p1satdiag', 'Saturation', 2),
        ExaminedField('p1satdiag', 'Pressure',   2)]
    
class withgrav_updip:
    gravity_magnitude = 1.5e6
    residual_saturations = (0.1, 0.1)
    initial_saturation2 = 0.1
    density2 = 2.
    examined_fields = [
        ExaminedField('withgrav_updip', 'Saturation', 2)]
    
cases = OptionsArray('case', [p1satdiag, withgrav_updip])


class relpermupwind:
    saturation_face_value = None
    rel_perm_face_value = "FirstOrderUpwind"

class modrelpermupwind:
    saturation_face_value = "FiniteElement"
    saturation_face_value_limiter = "Sweby"
    rel_perm_face_value = "RelPermOverSatUpwind"

submodels = OptionsArray('submodel', [relpermupwind, modrelpermupwind])


# build simulation options tree on top of mesh_options_tree
sim_options_tree = cases * submodels * mesh_options_tree

# do the same for a testing tree, where additionally we're interested
# in certain fields
test_options_tree = OptionsNode()
test_options_tree *= sim_options_tree
test_options_tree[0] *= OptionsArray('field', ['pressure2', 'saturation2'])
test_options_tree[1] *= OptionsArray('field', ['saturation2'])

nprocs = get_nprocs(sim_options_tree.count_leaves(),
                    nprocs_max=nprocs_max)


## GLOBAL OPTIONS

# update classes in darcy_impes_common/options.py to suit this test
# case, and populate the trees accordingly.

class global_spatial_options(base.global_spatial_options):
    mesh_dir = mesh_dir
    def element_numbers(self):
        # don't really care about element numbers in y and z
        return [self.mesh_res, 2, 2]
    def mesh_name(self):
        return self.geometry + '_' + self.str(['mesh_res'])

    
class global_simulation_options(base.global_simulation_options):
    simulation_dir = simulation_dir
    problem_name = problem_name
    def simulation_name(self):
        return self.str(simulation_naming_keys)
    def mesh_prefix_relative_to_simulation(self):
        return '../{}/'.format(mesh_dir)
    def gravity_direction(self):
        result = [0] * self.dim_number
        result[0] = -1
        return result
    relperm_relation = 'PowerLaw'
    relperm_relation_exponents = (2, 2)

    
class global_testing_options(base.global_testing_options):
    user_id = 'rferrier'
    nprocs = nprocs
    xml_target_filename = 'darcy_impes_p1_2phase_bl.xml'
    simulation_options_test_length = 'short'
    min_convergence_rate = 0.7
    error_calculation = 'integral'
    timestep_index = -1
    def report_filename(self): 
        self.problem_name + '_report.txt'
    def error_variable_name(self): 
        return self.variable_name + 'AbsError'
    def max_error_norm(self):
        """
        Since we're already testing convergence rates, let's only test the
        absolute error norm for the first mesh.
        """
        scale = None
        # TODO replace get_node_info in options_iteration
        if self.get_node_info.is_first('mesh'):
            if 'saturation' in self.field:
                scale = 1.
            elif 'pressure' in self.field:
                scale = 1.e6
        if scale:
            return 0.1 * scale
        else:
            return None
    

mesh_options_tree.update(global_spatial_options)

sim_options_tree.update(global_spatial_options)
sim_options_tree.update(global_simulation_options)

test_options_tree.update(global_spatial_options)
test_options_tree.update(global_simulation_options)
test_options_tree.update(global_testing_options)



## PROCESSING

# get any args from the command line
if len(sys.argv) > 1:
    commands = sys.argv[1:]
else:
    commands = ['pre', 'mesh', 'run', 'post']

    
# make directories if necessary
if 'pre' in commands:
    for d in [mesh_dir, simulation_dir]:
        try:
            os.makedirs(d)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    
if 'xml' in commands:
    smap(WriteXml('mesh_res', mesh_dir=mesh_dir, 
                  simulation_dir=simulation_dir,
                  with_respect_to_resolution=True),
         test_options_tree,
         message='Expanding XML file')
    
    
if 'pre' in commands:
    smap(ExpandTemplate('geo_template_filename', 'geo_filename',
                        target_dir_key='mesh_dir',
                        rendering_strategy=Jinja2Rendering({
                            'extensions': [base.RaiseExtension]})),
         mesh_options_tree,
         message="Expanding geometry files")
    
    smap(ExpandTemplate('simulation_options_template_filename',
                        'simulation_options_filename',
                        target_dir_key='simulation_dir',
                        rendering_strategy=Jinja2Rendering()),
         sim_options_tree,
         message="Expanding options files")

    
if 'mesh' in commands:
    pmap(RunProgram('meshing_args', 'geo_filename', 'mesh_name',
                    working_dir_key='mesh_dir'),
         mesh_options_tree,
         nprocs_max=nprocs_max, in_reverse=True, message="Meshing")

    
if 'run' in commands:
    pmap(RunProgram('simulation_args',
                    'simulation_prerequisite_filenames',
                    'simulation_name',
                    working_dir_key='simulation_dir'),
         sim_options_tree,
         nprocs_max=nprocs_max, in_reverse=True,
         message="Running simulations")
    
if 'post' in commands:
    smap(StudyConvergence('mesh_res', case_name + '.txt', 
                          results_dir=simulation_dir,
                          with_respect_to_resolution=True),
         test_options_tree,
         message="Postprocessing")
    
