from options_iteration import OptionsDict, OptionsNode, OptionsArray
import xml_snippets
import re


## SIMULATION

submodels = OptionsArray('submodel', [
    OptionsNode('relpermupwind', {
        'REL_PERM_FACE_VALUE': "FirstOrderUpwind",
        'SAT_FACE_VALUE_OPTION': "",
    }),
    OptionsNode('modrelpermupwind', {
        'REL_PERM_FACE_VALUE': "RelPermOverSatUpwind",
        'SAT_FACE_VALUE_OPTION': xml_snippets.sat_face_value_fe_sweby,
    }),
])


simulation_dict = OptionsDict({
    'simulation_options_extension': 'diml',

    'simulation_options_template_filename': lambda opt: 
    '{}.{}.template'.format(opt['case'], opt['simulation_options_extension']),
    
    'simulation_options_filename': lambda opt: 
    '{}.{}'.format(opt['simulation_name'], opt['simulation_options_extension']),

})


## TESTING AND RESULTS 

field_pat = '(.*)([0-9])'
fields = OptionsArray(
    'field', ['pressure1', 'saturation2'],
    
    common_entries={
    'phase_name': lambda opt: 'Phase' + re.sub(field_pat, '\\2', opt['field']),
    'variable_name': lambda opt: re.sub(
        field_pat, '\\1', opt['field']).capitalize(),
    'field_descriptor': lambda opt: '{}::{}'.format(
        opt['phase_name'], opt['variable_name'])
})


testing_dict = OptionsDict({
    'report_filename': lambda opt: opt['case'] + '.out',
    'vtu_filename': lambda opt: opt['simulation_name'] + '_1.vtu',
    'norm': 1,
})
