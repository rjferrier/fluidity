
## SETTINGS

case_name = 'darcy_impes_p1_2phase_bl'
simulation_naming_keys = ['submodel', 'dim', 'mesh_res']
default_nproc = 6


## OPTIONS TREE ASSEMBLY

from simulation_options import *
from mesh_options import *

# update existing dictionaries to suit this test case
simulation_dict.update({
    'case': case_name,
    'simulation_naming_keys': simulation_naming_keys})
spatial_dict.update({
    'domain_extents': (1., 1., 1.), 
    'EL_NUM_X': lambda opt: opt['mesh_res'],
    'EL_NUM_Y': 2,
    'EL_NUM_Z': 2,
})

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


## FUNCTION OBJECTS

from functors import *
from buckley_leverett_tools import *

expand_geo = ExpandTemplate('geo_template_filename', 'geo_filename')
mesh = Mesh()
expand_sim_options = ExpandTemplate('simulation_options_template_filename',
                                    'simulation_options_filename',
                                    naming_keys=simulation_naming_keys)
simulate = Simulate('../../bin/darcy_impes')
error_calc = BuckleyLeverettErrorCalculator(
    'reference_solution/analytic_BL_QuadraticPerm_withgravity_updip_{}.txt',
    simulation_naming_keys=simulation_naming_keys)
postproc = Postprocess(error_calc, report_filename=case_name + '.txt',
                       naming_keys=simulation_naming_keys)

clean_meshes = Clean([expand_geo, mesh])
clean_sims = Clean([expand_sim_options, simulate])

## PROCESSING

import sys

# get any args from the command line
if len(sys.argv) > 1:
    commands = sys.argv[1:]
else:
    commands = ['pre', 'run', 'post']
    
if 'pre' in commands:
    smap("Expanding geometry files", expand_geo, mesh_options_tree)
    pmap("Meshing", mesh, mesh_options_tree, default_nproc=default_nproc)
    smap("Expanding options files", expand_sim_options, sim_options_tree)
    
if 'run' in commands:
    pmap('Running simulations', simulate, sim_options_tree,
         default_nproc=default_nproc)
    
if 'post' in commands:
    smap('Postprocessing', postproc, results_options_tree)
    
if 'clean' in commands:
    smap('Cleaning meshes', clean_meshes, mesh_options_tree)
    smap('Cleaning simulations', clean_sims, sim_options_tree)
