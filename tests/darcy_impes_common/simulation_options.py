from options_iteration import OptionsDict, OptionsNode, OptionsArray
import xml_snippets

field_pat = '(.*)([0-9])'
fields = OptionsArray('field', ['saturation2'], common_entries={
    'phase_name': lambda opt: 'Phase' + re.sub(field_pat, '\\2', opt['field']),
    'variable_name': lambda opt: re.sub(
        field_pat, '\\1', opt['field']).capitalize(),
})

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
    'simulation_options_template_filename': lambda opt: 
    'template_' + opt['case'] + '.diml',

    'simulation_name': lambda opt: opt.str(only=opt['simulation_naming_keys']),
    
    'simulation_options_filename': lambda opt: 
    opt['simulation_name'] + '.diml',

})

