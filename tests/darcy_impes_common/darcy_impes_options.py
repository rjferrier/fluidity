"""
Some common options for Darcy IMPES tests.  These can be converted
to dictionaries and tree-like data structures via the
options_iteration package, and mapped to .geo and .diml files via the
Jinja 2 template engine.
"""

from options_iteration import OptionsArray
import re

def join(*words):
    "Helper function.  Joins nonblank words with underscores."
    return '_'.join(([w for w in words if w]))


## GEOMETRY/MESHING 

# Define options that change with problem dimensions

class dim1:
    dim_number = 1
    geometry = "line"
    gravity_direction = (-1.,)
    wall_ids = ()

class dim2:
    dim_number = 2
    geometry = "rectangle"
    gravity_direction = (-1., 0.)
    wall_ids = (3, 4)

class dim3:
    dim_number = 3
    geometry = "cuboid"
    gravity_direction = (-1., 0., 0.)
    wall_ids = (3, 4, 5, 6)

    
# Define some universal options.  Some items (mesh_res,
# domain_extents, ...) have been left for the user to define; a
# KeyError will be raised if these items are still missing at runtime.
class global_options:
    
    # SPATIAL/MESHING OPTIONS

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
    def mesh_name(self):
        return join(
            self.geometry_prefix, self.geometry, str(int(self.mesh_res)))
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


    # SIMULATION OPTIONS
    
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


    # POSTPROCESSING OPTIONS

    xml_template_filename = 'regressiontest.xml.template'
    norm = 1
    
    def vtu_filename(self):
        return '{}_1.vtu'.format(self.simulation_name)

    # the following entries will depend on the pending 'field'
    # entry which takes the form
    # <variable-name-in-lower-case><phase-number>
    field = 'to_come'
    field_pat = '(.*)([0-9])'

    def phase_name(self):
        return 'Phase' + re.sub(self.field_pat, '\\2', self.field)
        
    def variable_name(self):
        return re.sub(
            self.field_pat, '\\1', self.field).capitalize()

    def error_variable_name(self): 
        return self.variable_name + 'AbsError'
    
    error_calculation = 'integral'
    error_timestep_index = -1


## HELPERS

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
