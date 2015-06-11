from options_iteration import OptionsDict, OptionsNode, OptionsArray
import xml_snippets

def join(words):
    "Helper function"
    return '_'.join(([w for w in words if w] ))


## NODES AND ARRAYS

# Define options that change with problem dimensions.  We'll use
# capital letters to represent template placeholders.  In future it
# would be worth using a more sophisticated template engine like
# jinja2.
dim1 = OptionsNode('1d', {
    'dim_number': 1,
    'geometry': "line",
    'GRAVITY_DIRECTION': "-1.",
    'WALL_IDS': "",
    'WALL_NUM': 0,
    'WALL_FLOW_BC_SNIPPET': "",
})

dim2 = OptionsNode('2d', {
    'dim_number': 2,
    'geometry': "rectangle",
    'GRAVITY_DIRECTION': "-1. 0.",
    'WALL_FLOW_BC_SNIPPET': xml_snippets.wall_no_normal_flow_bc,
    'WALL_IDS': "3 4",
    'WALL_NUM': 2,
})

dim3 = OptionsNode('3d', {
    'dim_number': 3,
    'geometry': "cuboid",
    'GRAVITY_DIRECTION': "-1. 0. 0.",
    'WALL_FLOW_BC_SNIPPET': xml_snippets.wall_no_normal_flow_bc,
    'WALL_IDS': "3 4 5 6",
    'WALL_NUM': 4,
})

# Chain these together as we would for a parameter sweep.
dims = OptionsArray('dim', [dim1, dim2, dim3])

# Define mesh 'type' options for the multidimensional cases.
mesh_types = OptionsArray('mesh_type', ['reg', 'irreg', 'curved_irreg'])

# We can define a sweep for mesh resolution, but the range may be
# overridden depending on the case.
mesh_resolutions = OptionsArray('mesh_res', [10, 20, 40, 80])



## DICTIONARY ENTRIES
    
# Define some universal options.
spatial_dict = OptionsDict({
    'domain_extents'         : (1.0, 1.2, 0.8),   # see note [1]
    'reference_element_nums' : (10, 12, 8),
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


# duplicate entries that double as template placeholders to capitalise
# their keys.
spatial_dict.update({k.upper(): lambda opt, k=k: opt[k] for k in 
                     ['dim_number', 'mesh_name']})


# Notes:
# 
# [1] mesh elements will be sized such that there are mesh_res
# elements along domain edges in the x-direction, where mesh_res is
# 5 for mesh 'A', 10 for 'B', etc.  Irregular meshes will try to
# fill the domain with uniformly sized elements.  This means that
# the domain probably needs to be sized 'nicely' in each dimension
# if there is to be good convergence on these meshes.
