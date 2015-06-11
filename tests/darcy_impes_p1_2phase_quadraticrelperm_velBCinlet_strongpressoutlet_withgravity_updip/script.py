import sys
sys.path.append('../darcy_impes_common')
from mesh_options import *
from simulation_and_testing_options import *
from functors import *
from buckley_leverett_tools import *
from xml_snippets import *

## SETTINGS

case_name = 'darcy_impes_p1_2phase_bl'
simulation_naming_keys = ['subcase', 'submodel', 'dim', 'mesh_res']
nprocs = 6



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
        'SUBCASE': "withgrav_updip",
        'GRAVITY_SNIPPET': gravity,
        'RELATIVE_PERMEABILITY_RELATION': quadratic_relperm_correlation,
        'RESIDUAL_SATURATION_SNIPPET': residual_saturations,
        'RESIDUAL_SATURATION1': 0.1,
        'RESIDUAL_SATURATION2': 0.2,
        'INITIAL_SATURATION2': 0.1,
        'DENSITY2': 2.,
        'SATURATION2_ERROR_SNIPPET': error_variable.format(
            'withgrav_updip', 'saturation2', 'Saturation'),
        'PRESSURE2_ERROR_SNIPPET': "",
    }),
])


## UPDATE DICTIONARIES 

# extend/override entries in the predefined dictionaries to suit this
# test case

spatial_dict.update({
    'domain_extents': (1., 1., 1.), 
    'EL_NUM_Y': lambda opt: opt['EL_NUM_X']/2,
    'EL_NUM_Z': lambda opt: opt['EL_NUM_X']/2,
})

simulation_dict.update({
    'case': case_name,
    'naming_keys': None,
    'excluded_naming_keys': ['mesh_type'],
    'simulation_name': lambda opt: opt.str(simulation_naming_keys),
    })

def max_error_norm(options):
    # let's only test the error norm for the first mesh
    if options['mesh_res'] == 10:
        if 'saturation' in options['field']:
            return 0.1
    return None
        
testing_dict.update({
    'case': case_name,
    'user_id': 'rferrier',
    'nprocs': nprocs,
    'xml_template_filename': 'darcy_impes_p1_2phase_bl.xml.template',
    'xml_target_filename': 'darcy_impes_p1_2phase_bl.xml',
    'simulation_options_test_length': 'short',
    'reference_solution_filename': 'reference_solution/'+
        'analytic_BL_QuadraticPerm_withgravity_updip_saturation2.txt',
    'min_convergence_rate': 0.7,
    'max_error_norm': max_error_norm,
    'error_variable_name': lambda opt: opt['variable_name'] + 'AbsError',
    'test_harness_command_line': 'python script.py pre run post',
})
testing_dict.update(simulation_dict)


## OPTIONS TREE ASSEMBLY

# combine (sections of) predefined options arrays to make trees

# build tree for meshing
mesh_options_tree = dims
# only the second and third dimensions have a mesh type, and we will
# only use the regular mesh type here
mesh_options_tree[1:] *= mesh_types[0:1]

# the solution discontinuity makes the convergence very noisy,
# especially for 2D and 1D where there are fewer grid points.
mesh_options_tree[0] *= mesh_resolutions[0:4:3]
mesh_options_tree[1] *= mesh_resolutions[0:3:2]
mesh_options_tree[2] *= mesh_resolutions[0:2:1]

# populate the tree with geometry- and mesh-related dictionary
# entries.  Need to modify some of them for this test case.
mesh_options_tree.update(spatial_dict)


# do the same for simulations
sim_options_tree = subcases * submodels * mesh_options_tree
sim_options_tree.update(simulation_dict)


# and testing
test_options_tree = sim_options_tree * fields[1:]
test_options_tree.update(simulation_dict)
test_options_tree.update(testing_dict)

# try out two different error calculations
error_calcs = OptionsArray('error_calc', [
    OptionsNode('fromfield', {
        'error_calc_function': get_error_from_field}),
    
    OptionsNode('from1dref', {
        'error_calc_function': get_error_with_one_dimensional_solution})
])
test_options_tree = error_calcs[0] * test_options_tree



## FUNCTION OBJECTS

expand_geo = ExpandTemplate('geo_template_filename', 'geo_filename')
mesh = Mesh()
expand_sim_options = ExpandTemplate('simulation_options_template_filename',
                                    'simulation_options_filename')
simulate = Simulate('../../bin/darcy_impes')

postproc = Postprocess()

clean_meshes = Clean([expand_geo, mesh])
clean_sims = Clean([expand_sim_options, simulate])

write_xml = WriteXml()


## PROCESSING

# get any args from the command line
if len(sys.argv) > 1:
    commands = sys.argv[1:]
else:
    commands = ['pre', 'run', 'post']
    
if 'pre' in commands:
    smap("Expanding geometry files", expand_geo, mesh_options_tree)
    pmap("Meshing", mesh, mesh_options_tree, default_nprocs=nprocs)
    smap("Expanding options files", expand_sim_options, sim_options_tree)
    
if 'run' in commands:
    pmap('Running simulations', simulate, sim_options_tree,
         default_nprocs=nprocs)
    
if 'post' in commands:
    smap('Postprocessing', postproc, test_options_tree)
    
if 'clean' in commands:
    smap('Cleaning meshes', clean_meshes, mesh_options_tree)
    smap('Cleaning simulations', clean_sims, sim_options_tree)
    
if 'xml' in commands:
    smap('Expanding XML file', write_xml, test_options_tree)
