import sys
sys.path.append('../darcy_impes_common')
from options import spatial_dict, dims, simulation_dict, testing_dict
from options_iteration import OptionsArray, OptionsNode
from functors import *
from buckley_leverett_tools import *
from diml_snippets import *
import os
import errno


## SETTINGS

case_name = 'darcy_impes_p1_2phase_bl'
simulation_naming_keys = ['subcase', 'submodel', 'dim', 'mesh_res']
nprocs = 6

mesh_dir = 'meshes'
simulation_dir = 'results'


        
## OPTIONS TREES

# initialise top level of tree for meshing
mesh_options_tree = dims

# only the second and third dimensions have a mesh type, and we will
# use only the regular mesh type here
mesh_options_tree[1:] *= OptionsArray('mesh_type', ['reg'])

# for MMS tests we usually assign mesh resolutions [10, 20, 40, 80] to
# 1D, [10, 20, 40] to 2D, etc.  But in the BL case the solution
# discontinuity makes the convergence very noisy, especially when
# there are fewer grid points.  So calculate the convergence rate over
# three resolution doublings in 1D and two doublings in 2D.
mesh_options_tree[0] *= OptionsArray('mesh_res', [10, 80])
mesh_options_tree[1] *= OptionsArray('mesh_res', [10, 40])
mesh_options_tree[2] *= OptionsArray('mesh_res', [10, 20])


# define different groups of options that we're going to test.  Refer
# to xml_snippets.py.
subcases = OptionsArray('subcase', [
    OptionsNode('p1satdiag', {
        'GRAVITY_SNIPPET': "",
        'RELATIVE_PERMEABILITY_RELATION': quadratic_relperm_correlation,
        'RESIDUAL_SATURATION_SNIPPET': "",
        'INITIAL_SATURATION2': 0.,
        'DENSITY2': 1.,
        'SATURATION2_ERROR_SNIPPET': error_variable.format(
            'p1satdiag', 'saturation2', 'Saturation'),
        'PRESSURE2_ERROR_SNIPPET': error_variable.format(
            'p1satdiag', 'pressure2', 'Pressure'),
    }),
    
    OptionsNode('withgrav_updip', {
        'GRAVITY_SNIPPET': gravity,
        'RELATIVE_PERMEABILITY_RELATION': quadratic_relperm_correlation,
        'RESIDUAL_SATURATION_SNIPPET': residual_saturations,
        'RESIDUAL_SATURATION1': 0.1,
        'RESIDUAL_SATURATION2': 0.1,
        'INITIAL_SATURATION2': 0.1,
        'DENSITY2': 2.,
        'SATURATION2_ERROR_SNIPPET': error_variable.format(
            'withgrav_updip', 'saturation2', 'Saturation'),
        'PRESSURE2_ERROR_SNIPPET': "",
    }),
])

# and, orthogonally, some sub-models
submodels = OptionsArray('submodel', [
    OptionsNode('relpermupwind', {
        'REL_PERM_FACE_VALUE': "FirstOrderUpwind",
        'SAT_FACE_VALUE_SNIPPET': "",
    }),
    OptionsNode('modrelpermupwind', {
        'REL_PERM_FACE_VALUE': "RelPermOverSatUpwind",
        'SAT_FACE_VALUE_SNIPPET': sat_face_value_fe_sweby,
    }),
])

# build simulation options tree on top of mesh_options_tree
sim_options_tree = subcases * submodels * mesh_options_tree

# do the same for a testing tree, where additionally we're interested
# in certain fields
test_options_tree = sim_options_tree * OptionsArray('field', ['saturation2'])


## DICTIONARIES

# update entries in darcy_impes_common/options.py to suit this test
# case, and populate the trees accordingly.

spatial_dict.update({
    'domain_extents': (1., 1., 1.), 
    'reference_element_nums': (10, 10, 10), 
    'EL_NUM_Y': lambda opt: 2,
    'EL_NUM_Z': lambda opt: 2,
    'MESH_NAME': lambda opt: '{}/{}'.format(mesh_dir, opt['mesh_name']),
    'WALL_FLOW_BC_SNIPPET': lambda opt:
        wall_no_normal_flow_bc if opt['dim_number'] > 1 else '',
})
mesh_options_tree.update(spatial_dict)


simulation_dict.update({
    'case': case_name,
    'naming_keys': None,        # DELETE?
    # we're only using the 'reg' mesh type, so leave this out of the
    # simulation IDs.
    'excluded_naming_keys': ['mesh_type'], # DELETE?
    'simulation_name': lambda opt: opt.str(simulation_naming_keys),
})
sim_options_tree.update(spatial_dict)
sim_options_tree.update(simulation_dict)


def max_error_norm(options):
    """
    Since we're already testing convergence rates, let's only test the
    absolute error norm for the first mesh.
    """
    if options['mesh_res'] == 10:
        if 'saturation' in options['field']:
            return 0.1
    return None
    
testing_dict.update({
    'case': case_name,
    'user_id': 'rferrier',
    'nprocs': nprocs,
    'xml_target_filename': 'darcy_impes_p1_2phase_bl.xml',
    'simulation_options_test_length': 'short',
    'reference_solution_filename': 'reference_solution/'+
        'analytic_BL_QuadraticPerm_withgravity_updip_saturation2.txt',
    'report_filename': lambda opt: opt['case'] + '_report.txt',
    'min_convergence_rate': 0.7,
    'max_error_norm': max_error_norm,
    'error_variable_name': lambda opt: opt['variable_name'] + 'AbsError',
    'test_harness_command_line': 'python script.py pre run post',
})

test_options_tree.update(spatial_dict)
test_options_tree.update(simulation_dict)
test_options_tree.update(testing_dict)



## PROCESSING

# get any args from the command line
if len(sys.argv) > 1:
    commands = sys.argv[1:]
else:
    commands = ['pre', 'run', 'post']

    
# make directories if necessary
if 'pre' in commands:
    for d in [mesh_dir, simulation_dir]:
        try:
            os.makedirs(d)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    
if 'xml' in commands:
    smap('Expanding XML file', WriteXml(), test_options_tree)
    
if 'pre' in commands:
    smap("Expanding geometry files",
         ExpandTemplate(
             'geo_template_filename', 'geo_filename', target_dir=mesh_dir),
         mesh_options_tree)
    
    pmap("Meshing", Mesh(working_dir=mesh_dir),
         mesh_options_tree, default_nprocs=nprocs)
    
    smap("Expanding options files",
         ExpandTemplate(
             'simulation_options_template_filename',
             'simulation_options_filename', target_dir=simulation_dir),
         sim_options_tree)

    
if 'run' in commands:
    pmap('Running simulations',
         Simulate('../../bin/darcy_impes', working_dir=simulation_dir),
         sim_options_tree, default_nprocs=nprocs)
    
if 'post' in commands:
    smap('Postprocessing',
         Postprocess(GetErrorFromField, results_dir=simulation_dir),
         test_options_tree)
    
