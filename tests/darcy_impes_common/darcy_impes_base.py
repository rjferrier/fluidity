"""
Globals, basic options and a runner function.  Some options
(e.g. res) have been left for the user to define; a KeyError will
be raised if these items are still missing at runtime.
"""

import os
import sys
import errno
from opiter import OptionsArray, smap, pmap, \
    ExpandTemplate, Jinja2TemplateEngine, RunProgram, \
    unlink, Check, Remove, missing_dependencies, unpicklable
from darcy_impes_functors import StudyConvergence

try:
    from jinja2 import nodes
    from jinja2.ext import Extension
    from jinja2.exceptions import TemplateRuntimeError
except:
    pass

#-----------------------------------------------------------------------
# settings

# This variable is for ad-hoc running of simulations.  The Fluidity
# test harness will run tests in serial.
nprocs_max = 6

# It is quite easy to end up with the following situation: variables
# dependent on simulation options end up in the mesh options tree
# where the dependencies don't exist yet.  We could take care to
# ensure this never happens, but it is easier to provide hooks that
# simply strip out the offending items.
smap_hooks = {'item_hooks': [Remove(missing_dependencies)]}

# Additionally, putting in a list-reversing hook for parallel
# processing means that the more expensive higher-dimensional tests
# will tend to get run first.
pmap_hooks = {'list_hooks': [lambda l: l.reverse()],
              'item_hooks': [Remove(missing_dependencies), unlink,
                             Remove(unpicklable)]}

#-----------------------------------------------------------------------
# globals from environment

fluidity_dir = os.getenv('FLUIDITYPATH')
if not fluidity_dir:
    raise Exception(
        'need to define FLUIDITYPATH as an environment variable')

problem_name = os.getenv('PROBLEM')
if not problem_name:
    raise Exception('need to define PROBLEM as an environment variable')

mesh_dir = os.getenv('MESHPATH')
if not mesh_dir:
    mesh_dir = '.'
    
simulation_dir = os.getenv('SIMPATH')
if not simulation_dir:
    simulation_dir = '.'

simulator_path = fluidity_dir + '/bin/darcy_impes'
simulation_options_extension = 'diml'
simulation_error_extension = 'out'


#----------------------------------------------------------------------
# sets of options to define tree elements

class admin:
    # globals can be bundled with options for convenience
    problem_name = problem_name
    mesh_dir = mesh_dir
    simulation_dir = simulation_dir
    
    def geo_template_filename(self):
        return self.geometry_prefix + self.geometry + '.geo.template'
    def mesh_name(self):
        # limit to mesh tags
        return self.get_string(only=['mesh'])
    def geo_filename(self):
        return self.mesh_name + '.geo'
    def mesh_filename(self): 
        return self.mesh_name + '.msh'
    def mesh_path_relative_to_simulation_dir(self):
        # assume meshes exist in a parallel folder
        return '../{}/{}'.format(self.mesh_dir, self.mesh_filename)
    def meshing_args(self):
        # TODO: use interval for 1D as I'm not sure gmsh produces an
        # adaptivity-compatible line mesh.
        return ['gmsh', '-'+str(self.dim_number), self.geo_filename,
                '-o', self.mesh_filename]

    def simulation_options_template_filename(self):
        return '{}.{}.template'.format(
            self.problem_name, simulation_options_extension)
    def simulation_name(self):
        return self.get_string(only=['sim'])
    def simulation_options_filename(self):
        return '{}.{}'.format(self.simulation_name,
                              simulation_options_extension)
    def simulation_prerequisite_filenames(self):
        return [simulator_path, self.mesh_path_relative_to_simulation_dir,
                self.simulation_options_filename]
    def simulation_args(self):
        return [simulator_path, self.simulation_options_filename]
    def simulation_error_filename(self):
        return '{}.{}'.format(self.simulation_name,
                              simulation_error_extension)

    xml_template_filename = 'regressiontest.xml.template'
    
    def xml_target_filename(self):
        return self.problem_name + '.xml'
    

#----------------------------------------------------------------------

class spatial:
    inlet_id = 1
    outlet_id = 2
    domain_extents = (1.0, 1.2, 0.8)               # see note [1]
    reference_element_numbers = (10, 12, 8)
    def element_numbers(self):
        return [self.res * self.reference_element_numbers[i] / 
                self.reference_element_numbers[0] for i in range(3)]
    def element_sizes(self):
        return [self.domain_extents[i] / self.element_numbers[i] 
                for i in range(3)]

class simulation:
    reference_timestep_number = 10
    preconditioner = 'mg'
    adaptive_timestepping = False

    def dump_period(self):
        return self.finish_time
    
    def time_step(self):
        "Maintain a constant Courant number"
        scale_factor = float(self.reference_element_numbers[0]) / \
                       self.res
        return scale_factor * self.finish_time / \
            self.reference_timestep_number


class testing:
    error_timestep_index = -1
    error_aggregation = 'l2norm'
    min_convergence_rate = 0.7

    def error_variable_name(self):
        return self.variable_name + 'AbsError'        
    
    def max_error_norm(self):
        """
        Since we're already testing convergence rates, let's only test the
        absolute error norm for the first mesh.
        """
        if self.get_position('res').is_first():
            # recover and loop over the embedded list of dictionaries
            # describing fields
            for od in self.examined_fields:
                if self.field == od.field:
                    return od.error_tolerance

                
#----------------------------------------------------------------------

class onedim:
    dim_number = 1
    geometry = "line"
    wall_ids = ()
    geometry_prefix = ''
    have_regular_mesh = True

class twodim:
    dim_number = 2
    geometry = "rectangle"
    wall_ids = (3, 4)

class threedim:
    dim_number = 3
    geometry = "cuboid"
    wall_ids = (3, 4, 5, 6)


#----------------------------------------------------------------------

class straight:
    geometry_prefix = ''
    
class curved:
    def geometry_prefix(self):
        # can't have curved 1D meshes
        return 'curved_' if self.dim_number > 1 else ''

    
#----------------------------------------------------------------------

class reg:
    have_regular_mesh = True
    
class irreg:
    have_regular_mesh = False

    
#----------------------------------------------------------------------

class corey:
    rel_perm_relation_name = 'Corey2Phase'
    rel_perm_relation_exponents = None
    
class quadratic:
    rel_perm_relation_name = 'PowerLaw'
    rel_perm_relation_exponents = (2, 2)


#----------------------------------------------------------------------

class rpupwind:
    saturation_face_value = None
    rel_perm_face_value = "FirstOrderUpwind"

class modrpupwind_satfe:
    saturation_face_value = "FiniteElement"
    saturation_face_value_limiter = "Sweby"
    rel_perm_face_value = "RelPermOverSatUpwind"

# face_vals = OptionsArray('face_val', [rpupwind, modrpupwind_satfe])


#----------------------------------------------------------------------
# helpers and main function called by individual scripts

class Jinja2RaiseError(Extension):
    tags = set(['raise'])
    def parse(self, parser):
        lineno = next(parser.stream).lineno
        message_node = parser.parse_expression()
        return nodes.CallBlock(
            self.call_method('_raise', [message_node], lineno=lineno),
            [], [], [], lineno=lineno)
    def _raise(self, msg, caller):
        raise TemplateRuntimeError(msg)

    
def safe_mkdir(dir_name):
    if not dir_name:
        return
    try:
        os.makedirs(dir_name)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise

        
def main(mesh_options_tree, sim_options_tree, test_options_tree,
         jinja2_filters={}):

    # get/default directives from the command line
    commands = sys.argv[1:]
    if len(commands) == 0:
        commands = ['pre', 'run', 'post']
    
    # make directories if necessary
    if 'pre' in commands:
        for d in [mesh_dir, simulation_dir]:
            safe_mkdir(d)

    # expand templates in serial
    if 'pre' in commands:
        engine = Jinja2TemplateEngine(
            {'extensions': [Jinja2RaiseError]}, filters=jinja2_filters)
        
        smap(ExpandTemplate('geo_template_filename', 'geo_filename',
                            target_dir_key='mesh_dir',
                            engine=engine),
             mesh_options_tree,
             message="Expanding geometry files",
             **smap_hooks)
        
        # smap(WriteRulesForMeshing('res',
        #                           mesh_dir=mesh_dir),
        #      test_options_tree,
        #      message='Expanding meshing rules')
        
        smap(ExpandTemplate('simulation_options_template_filename',
                            'simulation_options_filename',
                            target_dir_key='simulation_dir',
                            engine=engine),
             sim_options_tree,
             message="Expanding options files",
             **smap_hooks)

        smap(WriteXmlForConvergenceTests('res',
                                         simulation_dir=simulation_dir,
                                         with_respect_to_resolution=True),
             test_options_tree,
             message='Expanding XML file',
             **smap_hooks)
        
    
    # mesh and run simulations in parallel
    if 'run' in commands:
        pmap(RunProgram('meshing_args', 'geo_filename', 'mesh_name',
                        working_dir_key='mesh_dir'),
             mesh_options_tree,
             nprocs_max=nprocs_max, 
             message="Meshing",
             **pmap_hooks)
    
        pmap(RunProgram('simulation_args',
                        'simulation_prerequisite_filenames',
                        'simulation_name',
                        working_dir_key='simulation_dir'),
             sim_options_tree,
             nprocs_max=nprocs_max,
             message="Running simulations",
             **pmap_hooks)
        
        
    # study convergence in serial
    if 'post' in commands:
        smap(StudyConvergence('res', 'convergence.txt', 
                              results_dir=simulation_dir,
                              with_respect_to_resolution=True),
             test_options_tree,
             message="Postprocessing",
             **smap_hooks)

        
#----------------------------------------------------------------------

# Notes:
# 
# [1] Mesh elements will be sized such that there are res
#     elements along domain edges in the x-direction.  Irregular
#     meshes will use dx only and try to fill the domain with
#     uniformly sized elements.  This means that the domain probably
#     needs to be sized 'nicely' in each dimension if there is to be
#     good convergence on these meshes.
