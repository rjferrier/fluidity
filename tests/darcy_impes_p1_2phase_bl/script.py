import darcy_impes_options as base
from options_iteration import OptionsArray, OptionsNode
from options_iteration.utilities import smap, pmap, ExpandTemplate, RunBinary,\
    SimpleRendering, get_nprocs
from darcy_impes_functors import WriteXml, StudyConvergence, \
    get_error_from_field, get_error_with_1d_solution
import diml_snippets as diml
import os
import errno
import sys


## SETTINGS

case_name = 'darcy_impes_p1_2phase_bl'
simulation_naming_keys = ['subcase', 'submodel', 'dim', 'mesh_res']
nprocs_max = 6

mesh_dir = 'meshes'
simulation_dir = 'simulations'
simulator_path = '../../../bin/darcy_impes'


        
## OPTIONS TREES

# initialise top level of tree for meshing
mesh_options_tree = base.dims

# only the second and third dimensions have a mesh type, and we will
# use only the regular mesh type here
class reg:
    is_regular = 1
class irreg:
    is_regular = 0
mesh_options_tree[1:] *= OptionsArray('mesh_type', [reg])

# for MMS tests we usually assign mesh resolutions [10, 20, 40, 80] to
# 1D, [10, 20, 40] to 2D, etc.  But in the BL case the solution
# discontinuity makes the convergence very noisy, especially when
# there are fewer grid points.  So calculate the convergence rate over
# three resolution doublings in 1D and two doublings in 2D.
mesh_options_tree[0] *= OptionsArray('mesh_res', [10, 80])
mesh_options_tree[1] *= OptionsArray('mesh_res', [10, 40])
mesh_options_tree[2] *= OptionsArray('mesh_res', [10, 20])


def get_reference_solution_filename(options, field):
    return 'reference_solution/{0}_{1}.txt'.format(options.subcase, field)

def get_error_snippet(options, field, variable_name):
    return diml.error_variable.format(
        options.subcase, get_reference_solution_filename(options, field),
        variable_name)


class p1satdiag:
    gravity_snippet = ""
    relative_permeability_relation = diml.quadratic_relperm_correlation
    residual_saturation_snippet = ""
    initial_saturation2 = 0.
    density2 = 1.
    def saturation2_error_snippet(self):
        return get_error_snippet(self, 'saturation2', 'Saturation')
    def pressure2_error_snippet(self):
        return get_error_snippet(self, 'pressure2', 'Pressure')
    # TO BE FIXED in options_iteration: should automatically get
    # an {OptionsArray.name: OptionsNode.name} entry
    subcase = 'p1satdiag'
   
class withgrav_updip:
    gravity_snippet = diml.gravity
    relative_permeability_relation = diml.quadratic_relperm_correlation
    residual_saturation_snippet = diml.residual_saturations
    residual_saturation1 = 0.1
    residual_saturation2 = 0.1
    initial_saturation2 = 0.1
    density2 = 2.
    def saturation2_error_snippet(self):
        return get_error_snippet(self, 'saturation2', 'Saturation')
    pressure2_error_snippet = ""
    # TO BE FIXED in options_iteration: should automatically get
    # an {OptionsArray.name: OptionsNode.name} entry
    subcase = 'withgrav_updip'
    
subcases = OptionsArray('subcase', [p1satdiag, withgrav_updip])


class relpermupwind:
    rel_perm_face_value = "FirstOrderUpwind"
    sat_face_value_snippet = ""

class modrelpermupwind:
    rel_perm_face_value = "RelPermOverSatUpwind"
    sat_face_value_snippet = diml.sat_face_value_fe_sweby

submodels = OptionsArray('submodel', [relpermupwind, modrelpermupwind])


# build simulation options tree on top of mesh_options_tree
sim_options_tree = subcases * submodels * mesh_options_tree

# do the same for a testing tree, where additionally we're interested
# in certain fields
test_options_tree = sim_options_tree * OptionsArray('field', ['saturation2'])

nprocs = get_nprocs(sim_options_tree.count_leaves(),
                    nprocs_max=nprocs_max)


## GLOBAL OPTIONS

# update classes in darcy_impes_common/options.py to suit this test
# case, and populate the trees accordingly.

class global_spatial_options(base.global_spatial_options):
    domain_extents = (1.0, 1.2, 0.8)
    reference_element_nums = (10, 12, 8)
    el_num_y = 2
    el_num_z = 2
    def wall_flow_bc_snippet(self):
        if self.dim_number == 1:
            return ''
        else:
            return diml.wall_no_normal_flow_bc

class global_simulation_options(base.global_simulation_options):
    case = case_name
    simulator_path = simulator_path
    def simulation_name(self):
        return self.str(simulation_naming_keys)
    def mesh_prefix_relative_to_simulation(self):
        return '../{}/'.format(mesh_dir)


class global_testing_options(base.global_testing_options):
    case = case_name
    user_id = 'rferrier'
    nprocs = nprocs
    xml_target_filename = 'darcy_impes_p1_2phase_bl.xml'
    simulation_options_test_length = 'short'
    min_convergence_rate = 0.7
    error_calculation = 'integral'
    timestep_index = -1
    def report_filename(self): 
        self.case + '_report.txt'
    def error_variable_name(self): 
        return self.variable_name + 'AbsError'
    def max_error_norm(self):
        """
        Since we're already testing convergence rates, let's only test the
        absolute error norm for the first mesh.
        """
        if self['mesh_res'] == 10:
            if 'saturation' in self.field:
                return 0.1
        return None
    
    def reference_solution_filename(self):
        return get_reference_solution_filename(self, self.field)
    

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
    smap('Expanding XML file',
         WriteXml('mesh_res', mesh_dir=mesh_dir, 
                  simulation_dir=simulation_dir,
                  with_respect_to_resolution=True),
         test_options_tree)
    
    
if 'pre' in commands:
    smap("Expanding geometry files",
         ExpandTemplate(
             'geo_template_filename', 'geo_filename', target_dir=mesh_dir),
         mesh_options_tree)
    
    smap("Expanding options files",
         ExpandTemplate(
             'simulation_options_template_filename',
             'simulation_options_filename', target_dir=simulation_dir,
             rendering_strategy=SimpleRendering(nloops=5)),
         sim_options_tree)

    
if 'mesh' in commands:
    pmap("Meshing",
         RunBinary('meshing_args', 'geo_filename', 'mesh_name',
                   working_dir=mesh_dir),
         mesh_options_tree, nprocs_max=nprocs_max, in_reverse=True)

    
if 'run' in commands:
    pmap("Running simulations",
         RunBinary('simulation_args',
                   'simulation_prerequisite_filenames',
                   'simulation_name', working_dir=simulation_dir),
         sim_options_tree, nprocs_max=nprocs_max, in_reverse=True)
    
if 'post' in commands:
    smap('Postprocessing',
         StudyConvergence('mesh_res', case_name + '.txt', 
                          results_dir=simulation_dir,
                          with_respect_to_resolution=True),
         test_options_tree)
    
