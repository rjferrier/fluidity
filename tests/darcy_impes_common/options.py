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
import re


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

# Define options that change with problem dimensions.  We'll use
# capital letters to represent template placeholders.
dim1 = OptionsNode('1d', {
    'dim_number': 1,
    'geometry': "line",
    'GRAVITY_DIRECTION': "-1.",
    'WALL_IDS': "",
    'WALL_NUM': 0,
})

dim2 = OptionsNode('2d', {
    'dim_number': 2,
    'geometry': "rectangle",
    'GRAVITY_DIRECTION': "-1. 0.",
    'WALL_IDS': "3 4",
    'WALL_NUM': 2,
})

dim3 = OptionsNode('3d', {
    'dim_number': 3,
    'geometry': "cuboid",
    'GRAVITY_DIRECTION': "-1. 0. 0.",
    'WALL_IDS': "3 4 5 6",
    'WALL_NUM': 4,
})

dims = OptionsArray('dim', [dim1, dim2, dim3])
    
# define some universal options
spatial_dict = OptionsDict({
    'INLET_ID'               : "1",
    'OUTLET_ID'              : "2",
    
    # construct a name for the geometry template.  Because this entry
    # takes the form of a function, it will self-evaluate dynamically.
    'geo_template_name': 
    lambda opt: join((opt['geometry'], opt.str(['geo_type', 'mesh_type']))),
    
    # likewise for the mesh name 
    'mesh_name': 
    lambda opt: join((opt['geo_template_name'], opt.str('mesh_res'))),

    # etc.
    'geo_template_filename': lambda opt:
        opt['geo_template_name'] + '.geo.template',
    'geo_filename' : lambda opt: opt['mesh_name'] + '.geo',
    'mesh_filename' : lambda opt: opt['mesh_name'] + '.msh',
})

# add some expansions in x, y and z
for i, dim in enumerate(("X", "Y", "Z")):
    spatial_dict.update({
        'DOMAIN_LENGTH_'+dim : lambda opt: opt['domain_extents'][0],

        # element number along domain edge should be calculated such
        # that dx, dy and dz are kept approximately the same but scale
        # consistently to higher mesh resolutions
        'EL_NUM_'+dim        : lambda opt: 
            opt['mesh_res'] * opt['reference_element_nums'][i] / 
            opt['reference_element_nums'][0],

        # Here the optional argument is needed due to Python's late
        # binding of closures (see
        # http://docs.python-guide.org/en/latest/writing/gotchas/)
        'EL_SIZE_'+dim       : lambda opt, dim=dim: 
            opt['DOMAIN_LENGTH_'+dim] / opt['EL_NUM_'+dim]
    })

capitalise_keys(spatial_dict, ['dim_number', 'mesh_name'])


## SIMULATION

simulation_dict = OptionsDict({
    'simulation_options_extension': 'diml',

    'simulation_options_template_filename': lambda opt: 
    '{}.{}.template'.format(opt['case'], opt['simulation_options_extension']),
    
    'simulation_options_filename': lambda opt: 
        '{}.{}'.format(opt['simulation_name'],
                       opt['simulation_options_extension']),
})


## TESTING/RESULTS 

# in the next dict, some of the entries will depend on the pending
# 'field' entry which takes the form
# <variable-name-in-lower-case><phase-number>
field_pat = '(.*)([0-9])'

testing_dict = OptionsDict({
    'xml_template_filename': 'xml.template',
    'vtu_filename': lambda opt: '{}_1.vtu'.format(opt['simulation_name']),
    'norm': 1,
    'phase_name': lambda opt: 'Phase' + re.sub(field_pat, '\\2', opt['field']),
    'variable_name': lambda opt: re.sub(
        field_pat, '\\1', opt['field']).capitalize(),
    'field_descriptor': lambda opt: '{}::{}'.format(
        opt['phase_name'], opt['variable_name'])
})

