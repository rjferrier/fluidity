
## SETTINGS

case_name = 'darcy_impes_p1_2phase_bl'
simulation_naming_keys = ['case', 'submodel', 'dim', 'mesh_res']
default_nproc = 6


## OPTIONS TREE ASSEMBLY

from simulation_options import *
from mesh_options import *

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
mesh_options_tree.update({
    'domain_extents': (1., 1., 1.), 
    'EL_NUM_X': lambda opt: opt['mesh_res'],
    'EL_NUM_Y': 2,
    'EL_NUM_Z': 2,
})

# build a tree for simulations 
root = OptionsArray('case', [case_name], {
    'simulation_naming_keys': simulation_naming_keys})
sim_options_tree = root * submodels * mesh_options_tree
sim_options_tree.update(simulation_dict)

# and results
results_options_tree = sim_options_tree * fields


## PROCESSING

import sys
from functors import *
from buckley_leverett_tools import *

# get any args from the command line
if len(sys.argv) > 1:
    commands = sys.argv[1:]
else:
    commands = ['pre', 'run', 'post']
    

if 'pre' in commands:
    smap("Expanding geometry files",
         ExpandTemplate('geo_template_filename', 'geo_filename'),
         mesh_options_tree)
    
    pmap("Meshing", Mesh(), mesh_options_tree, default_nproc=default_nproc)
    
    smap("Expanding options files",
         ExpandTemplate('simulation_options_template_filename',
                        'simulation_options_filename',
                        naming_keys=simulation_naming_keys),
         sim_options_tree)

    
if 'run' in commands:
    pmap('Running simulations', Simulate('../../bin/darcy_impes'),
         sim_options_tree, default_nproc=default_nproc)

    
if 'post' in commands:
    error_calc = BuckleyLeverettErrorCalculator(
        'reference_solution/analytic_BL_QuadraticPerm_withgravity_updip_{}.txt',
        simulation_naming_keys=simulation_naming_keys)
    
    smap('Postprocessing',
         Postprocess(error_calc, naming_keys=simulation_naming_keys),
         results_options_tree)

    
if 'clean' in commands:
    smap('Cleaning meshes', Clean('MESH_NAME'), meshes)
    smap('Cleaning simulations', Clean('SIMULATION_NAME'), sims)
