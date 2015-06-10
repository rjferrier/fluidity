
## SETTINGS

case_name = 'darcy_impes_p1_2phase_bl'
simulation_naming_keys = ['submodel', 'dim', 'mesh_res']
results_naming_keys = simulation_naming_keys + ['field']
nprocs = 6


## UPDATE DICTIONARIES 

from simulation_options import *
from mesh_options import *

# update existing dictionaries to suit this test case
spatial_dict.update({
    'domain_extents': (1., 1., 1.), 
    'EL_NUM_X': lambda opt: opt['mesh_res'],
    'EL_NUM_Y': 2,
    'EL_NUM_Z': 2,
})
simulation_dict.update({
    'case': case_name,
    'simulation_naming_keys': simulation_naming_keys})

def max_error_norm(options):
    if 'saturation' in options['field']:
        if options['mesh_res'] == 10:
            return 0.1
    return None
        
        
testing_dict.update({
    'case': case_name,
    'user_id': 'rferrier',
    'xml_template_filename': 'darcy_impes_p1_2phase_bl.xml.template',
    'xml_target_filename': 'darcy_impes_p1_2phase_bl.xml',
    'min_convergence_rate': 0.7,
    'max_error_norm': max_error_norm,
    'error_variable_name': lambda opt: opt['variable_name'] + 'AbsError',
    'test_harness_command_line': 'python script.py pre run post',
})
testing_dict.update(simulation_dict)


## OPTIONS TREE ASSEMBLY

# build tree for meshing
mesh_options_tree = dims
# only the second and third dimensions have a mesh type
mesh_options_tree[1:] *= mesh_types[0:1]

# run four different resolutions in 1D; three in 2D; two in 1D
mesh_options_tree[0] *= mesh_resolutions[0:4]
mesh_options_tree[1] *= mesh_resolutions[0:3]
mesh_options_tree[2] *= mesh_resolutions[0:2]

# populate the tree with geometry- and mesh-related dictionary
# entries.  Need to modify some of them for this test case.
mesh_options_tree.update(spatial_dict)

# build tree for simulation
sim_options_tree = submodels * mesh_options_tree
sim_options_tree.update(simulation_dict)

# and results
results_options_tree = sim_options_tree * fields[1:]
results_options_tree.update(simulation_dict)
results_options_tree.update(testing_dict)


## FUNCTION OBJECTS

from functors import *
from buckley_leverett_tools import *

expand_geo = ExpandTemplate('geo_template_filename', 'geo_filename')
mesh = Mesh()
expand_sim_options = ExpandTemplate('simulation_options_template_filename',
                                    'simulation_options_filename',
                                    naming_keys=simulation_naming_keys)

simulate = Simulate('../../bin/darcy_impes')
postproc = Postprocess(AnalyticalErrorCalculator, testing_dict,
                       naming_keys=results_naming_keys)

clean_meshes = Clean([expand_geo, mesh])
clean_sims = Clean([expand_sim_options, simulate])

write_xml = WriteXml(testing_dict, naming_keys=results_naming_keys)


## PROCESSING

import sys

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
    smap('Postprocessing', postproc, results_options_tree)
    
if 'clean' in commands:
    smap('Cleaning meshes', clean_meshes, mesh_options_tree)
    smap('Cleaning simulations', clean_sims, sim_options_tree)
    
if 'xml' in commands:
    smap('Expanding XML file', write_xml, results_options_tree)
