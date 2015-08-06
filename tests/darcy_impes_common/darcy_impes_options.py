"""
In addition to the 'dims' OptionsArray, the dynamic entries in
this file will depend on the following entries.  The client should
makes sure these are represented in the options trees.

'mesh_type'              : 'reg', 'irreg', 'curved_irreg'
'mesh_res'               : any integer
'domain_extents'         : list of three floats   # see note [1]
'reference_element_nums' : list of three integers
'simulation_name'        : string

Note:
[1] mesh elements will be sized such that there are mesh_res elements
    along domain edges in the x-direction.  Irregular meshes will try
    to fill the domain with uniformly sized elements.  This means that
    the domain probably needs to be sized 'nicely' in each dimension
    if there is to be good convergence on these meshes.
"""

from options_iteration import OptionsDict, OptionsNode, OptionsArray
import os
import re

simulator_path = os.getenv('FLUIDITYPATH') + '/bin/darcy_impes'


## HELPERS

def join(words):
    "Joins words with underscores."
    return '_'.join(([w for w in words if w] ))

def capitalise_keys(options_dict, keys):
    """
    Duplicates entries, converting keys to uppercase.  This is useful
    when said keys double as placeholders in templates, where the
    placeholders follow an uppercase convention.
    """
    options_dict.update(
        {k.upper(): lambda opt, k=k: opt[k] for k in keys})
    

## GEOMETRY/MESHING 

# Define options that change with problem dimensions.
class dim1:
    dim_number = 1
    geometry = "line"
    gravity_direction = "-1."
    wall_ids = ""
    wall_num = 0

class dim2:
    dim_number = 2
    geometry = "rectangle"
    gravity_direction = "-1. 0."
    wall_ids = "3 4"
    wall_num = 2

class dim3:
    dim_number = 3
    geometry = "cuboid"
    gravity_direction = "-1. 0. 0."
    wall_ids = "3 4 5 6"
    wall_num = 4

dims = OptionsArray('dim', [dim1, dim2, dim3])

    
# define some universal options
class global_spatial_options:
    inlet_id = "1"
    outlet_id = "2"

    # construct a name for the geometry template.  Because this entry
    # takes the form of a function, it will self-evaluate dynamically.
    def geo_template_name(self):
        return join((self.geometry, self.str(['geo_type', 'mesh_type'])))

    # construct a name for the geometry template.  Because this entry
    # takes the form of a function, it will self-evaluate dynamically.
    def geo_template_name(self):
        return 'orthotope_{}d'.format(self.dim_number)
        
    # likewise for the mesh name 
    def mesh_name(self):
        return join((self.geometry,
                     self.str(['geo_type', 'mesh_type', 'mesh_res'])))
        
    # etc.
    def geo_template_filename(self):
        return self.geo_template_name + '.geo.template'
    def geo_filename(self):
        return self.mesh_name + '.geo'
    def mesh_filename(self): 
        return self.mesh_name + '.msh'
    def meshing_args(self):
        return ['gmsh', '-'+str(self.dim_number), self.geo_filename,
                '-o', self.mesh_filename]

    # element number along domain edge should be calculated such
    # that dx, dy and dz are kept approximately the same but scale
    # consistently to higher mesh resolutions
    def element_numbers(self):
        return [self.mesh_res * self.reference_element_nums[i] / 
                self.reference_element_nums[0] for i in range(3)]
    def element_sizes(self):
        return [self.domain_extents[i] / self.element_numbers[i] 
                for i in range(3)]
    
# monkey-patch some expansions in x, y and z.  Watch out for late
# binding: need to replace dim index with a default argument (i=i) on
# the lambdas
tgt = global_spatial_options.__dict__
for i, dim in enumerate('xyz'):
    tgt['domain_length_'+dim] = lambda self, i=i: self.domain_extents[i]
    tgt['el_num_'+dim] = lambda self, i=i: self.element_numbers[i]
    tgt['el_size_'+dim] = lambda self, i=i: self.element_sizes[i]


## SIMULATION

class global_simulation_options:
    simulation_options_extension = 'diml'

    def simulation_options_template_filename(self):
        return '{}.{}.template'.format(
            self.case, self.simulation_options_extension)

    def simulation_options_filename(self):
        return '{}.{}'.format(self.simulation_name,
                              self.simulation_options_extension)

    def simulation_prerequisite_filenames(self):
        return [simulator_path, self.simulation_options_filename]

    def simulation_args(self):
        return [simulator_path, self.simulation_options_filename]


## TESTING/RESULTS 

# in the next dict, some of the entries will depend on the pending
# 'field' entry which takes the form
# <variable-name-in-lower-case><phase-number>
field_pat = '(.*)([0-9])'

class global_testing_options:
    xml_template_filename = 'xml.template'
    norm = 1
    
    def vtu_filename(self):
        return '{}_1.vtu'.format(self.simulation_name)
        
    def phase_name(self):
        return 'Phase' + re.sub(field_pat, '\\2', self.field)
        
    def variable_name(self):
        return re.sub(
            field_pat, '\\1', self.field).capitalize()

    def field_descriptor(self):
        return '{}::{}'.format(
            self.phase_name, self.variable_name)
