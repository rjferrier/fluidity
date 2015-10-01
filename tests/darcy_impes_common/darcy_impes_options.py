"""
Some common code for Darcy IMPES tests.  The classes defining
options can be converted to dictionaries and tree-like data structures
via the options_iteration package, and mapped to .geo and .diml files
via the Jinja 2 template engine.
"""

from os import getenv, makedirs
from sys import argv
from errno import EEXIST
from options_iteration import \
    OptionsArray, smap, pmap, ExpandTemplate, RunProgram, Jinja2Rendering
from options_iteration_extended_utilities import \
    WriteXmlForConvergenceTests, StudyConvergence, join


#------------------------------------------------------------------------------
# GLOBALS

nprocs_max = 6

problem_name = getenv('PROBLEM')
if not problem_name:
    raise Exception('define PROBLEM as an environment variable')

mesh_dir = getenv('MESHPATH')
if not mesh_dir:
    mesh_dir = '.'
    
simulation_dir = getenv('SIMPATH')
if not simulation_dir:
    simulation_dir = '.'


#------------------------------------------------------------------------------
# OPTIONS 

#------------------------------------------------------------------------------
# problem dimensions

class dim1:
    dim_number = 1
    geometry = "line"
    wall_ids = ()

class dim2:
    dim_number = 2
    geometry = "rectangle"
    wall_ids = (3, 4)

class dim3:
    dim_number = 3
    geometry = "cuboid"
    wall_ids = (3, 4, 5, 6)

    
# Make an array of these dimension options.  name_format changes
# dim<N> into <N>d.
dims = OptionsArray('dim', [dim1, dim2, dim3], 
                    name_format=lambda s: s[-1]+'d')

    
#------------------------------------------------------------------------------
# common to all

# some items (e.g. mesh_res) have been left for the user to define; a
# KeyError will be raised if these items are still missing at runtime
class common:

    # globals can be bundled with the other options for convenience
    problem_name = problem_name
    mesh_dir = mesh_dir
    simulation_dir = simulation_dir
    
    # SPATIAL/MESHING

    geometry_prefix = ''        # can be blank or 'curved'
    inlet_id = 1
    outlet_id = 2
    have_regular_mesh = True

    # Construct a filename for the geometry template.  Because this
    # entry takes the form of a function, it will self-evaluate
    # dynamically.
    def geo_template_filename(self):
        return join(self.geometry_prefix, self.geometry) + '.geo.template'
        
    # etc.
    def mesh_type(self):
        if self.dim_number == 1:
            return ''
        return 'reg' if self.have_regular_mesh else 'irreg'
    def mesh_name(self):
        return join(
            self.geometry_prefix, self.geometry, self.mesh_type,
            str(int(self.mesh_res)))
    def geo_filename(self):
        return self.mesh_name + '.geo'
    def mesh_filename(self): 
        return self.mesh_name + '.msh'
    def meshing_args(self):
        return ['gmsh', '-'+str(self.dim_number), self.geo_filename,
                '-o', self.mesh_filename]

    # Element number along domain edge should be calculated such that
    # dx, dy and dz are kept approximately the same but scale
    # consistently to higher mesh resolutions.  Note that irregular
    # meshes will use dx only and try to fill the domain with
    # uniformly sized elements.  This means that the domain probably
    # needs to be sized 'nicely' in each dimension if there is to be
    # good convergence on these meshes.
    domain_extents = (1.0, 1.2, 0.8)
    reference_element_numbers = (10, 12, 8)
    def element_numbers(self):
        return [self.mesh_res * self.reference_element_numbers[i] / 
                self.reference_element_numbers[0] for i in range(3)]
    def element_sizes(self):
        return [self.domain_extents[i] / self.element_numbers[i] 
                for i in range(3)]


    # SIMULATION

    simulator_path = '../../../bin/darcy_impes'
    simulation_options_extension = 'diml'
    simulation_error_extension = 'out'
    reference_timestep_number = 10
    preconditioner = 'mg'
    adaptive_timestepping = False
    

    def simulation_options_template_filename(self):
        return '{}.{}.template'.format(
            self.problem_name, self.simulation_options_extension)

    def simulation_options_filename(self):
        return '{}.{}'.format(self.simulation_name,
                              self.simulation_options_extension)

    def simulation_prerequisite_filenames(self):
        return [self.simulator_path, self.simulation_options_filename]

    def simulation_args(self):
        return [self.simulator_path, self.simulation_options_filename]

    def simulation_error_filename(self):
        return '{}.{}'.format(self.simulation_name,
                              self.simulation_error_extension)


    # RESULTS/TESTS

    xml_template_filename = 'regressiontest.xml.template'
    xml_target_filename = problem_name + '.xml'

    def error_variable_name(self):
        return self.variable_name + 'AbsError'        
    
    error_aggregation = 'l2norm'
    error_timestep_index = -1
    min_convergence_rate = 0.7
    
    def max_error_norm(self):
        """
        Since we're already testing convergence rates, let's only test the
        absolute error norm for the first mesh.
        """
        if self.get_position('mesh_res').is_first():
            # recover and loop over the embedded list of dictionaries
            # describing fields
            for od in self.examined_fields:
                if self.field == od.field:
                    return od.error_tolerance


#------------------------------------------------------------------------------
# JINJA2 HELPERS

try:
    from jinja2 import nodes
    from jinja2.ext import Extension
    from jinja2.exceptions import TemplateRuntimeError
except:
    pass


# from http://stackoverflow.com/questions/21778252/
# how-to-raise-an-exception-in-a-jinja2-macro
class RaiseExtension(Extension):
    # This is our keyword(s):
    tags = set(['raise'])
    
    # See also: jinja2.parser.parse_include()
    def parse(self, parser):
        # the first token is the token that started the tag. In our case we
        # only listen to "raise" so this will be a name token with
        # "raise" as value. We get the line number so that we can give
        # that line number to the nodes we insert.
        lineno = next(parser.stream).lineno

        # Extract the message from the template
        message_node = parser.parse_expression()

        return nodes.CallBlock(
            self.call_method('_raise', [message_node], lineno=lineno),
            [], [], [], lineno=lineno
        )

    def _raise(self, msg, caller):
        raise TemplateRuntimeError(msg)


#------------------------------------------------------------------------------
# MAIN FUNCTION

def main(mesh_options_tree, sim_options_tree, test_options_tree,
         jinja2_filters={}):

    # get/default directives from the command line
    commands = argv[1:]
    if len(commands) == 0:
        commands = ['pre', 'mesh', 'sim', 'post']
    
    # make directories if necessary
    if 'pre' in commands:
        for d in [mesh_dir, simulation_dir]:
            try:
                makedirs(d)
            except OSError as exc:
                if exc.errno != EEXIST:
                    raise

    # expand templates in serial
    if 'pre' in commands:
        renderer = Jinja2Rendering({'extensions': [RaiseExtension]},
                                   filters=jinja2_filters)
        
        smap(ExpandTemplate('geo_template_filename', 'geo_filename',
                            target_dir_key='mesh_dir',
                            rendering_strategy=renderer),
             mesh_options_tree,
             message="Expanding geometry files")
        
        smap(ExpandTemplate('simulation_options_template_filename',
                            'simulation_options_filename',
                            target_dir_key='simulation_dir',
                            rendering_strategy=renderer),
             sim_options_tree,
             message="Expanding options files")
    
        
    # mesh and run simulations in parallel
    if 'run' in commands:
        pmap(RunProgram('meshing_args', 'geo_filename', 'mesh_name',
                        working_dir_key='mesh_dir'),
             mesh_options_tree,
             nprocs_max=nprocs_max, in_reverse=True,
             clean_entries=True, recursive_freeze=True,
             message="Meshing")
    
        pmap(RunProgram('simulation_args',
                        'simulation_prerequisite_filenames',
                        'simulation_name',
                        working_dir_key='simulation_dir'),
             sim_options_tree,
             nprocs_max=nprocs_max, in_reverse=True,
             clean_entries=True, recursive_freeze=True,
             message="Running simulations")
        
        
    # study convergence in serial
    if 'post' in commands:
        smap(StudyConvergence('mesh_res', 'convergence.txt', 
                              results_dir=simulation_dir,
                              with_respect_to_resolution=True),
             test_options_tree,
             message="Postprocessing")
        
        
    # write tests in serial
    if 'xml' in commands:
        smap(WriteXmlForConvergenceTests('mesh_res', mesh_dir=mesh_dir, 
                                         simulation_dir=simulation_dir,
                                         with_respect_to_resolution=True),
             test_options_tree,
             message='Expanding XML file')
    
