"""
This module contains functionality for examining error norms and
convergence rates, and writing the corresponding XML file for
interpretation by the fluidity test harness.  The functors herein are
designed to be used in conjunction with options_iteration, a package
for configuring and iterating over trees of options.

Example:
    func = WriteXmlForConvergenceTests('mesh_size')
    options_iteration.utilities.smap(func, options_tree)

Note that WriteXML needs the Jinja 2 template engine.
"""

from options_iteration.utilities import SerialFunctor, Failure, Success, \
    check_file_exists, Jinja2TemplateEngine
from fluidity_tools import stat_parser
from numpy import abs, log, nan

try:
    from jinja2 import Environment, FileSystemLoader
    HAVE_JINJA2 = True
except:
    HAVE_JINJA2 = False


def join(*words):
    "Helper function.  Joins nonblank words with underscores."
    return '_'.join([w for w in words if w])


def get_error_from_field(options, simulation_dir='.'):
    stat_filename = '{}/{}.stat'.format(
        simulation_dir, options.simulation_name)
    check_file_exists(stat_filename)
    stat = stat_parser(stat_filename)
    
    phase = options.phase_name
    var = options.error_variable_name
    agg = options.error_aggregation
    index = options.error_timestep_index
    try:
        # n.b. assume the last timestep is required
        return stat[phase][var][agg][index]
    except KeyError:
        raise Failure(
            ("\nget_error_from_field expected to find \n"+\
             "{0}::{1} in the stat file; \n"+\
             "has this been defined in the options file?").\
            format(phase, var))


class StudyConvergence(SerialFunctor):
    error_format = '{:.3e}'
    rate_format = '{:.6f}'

    def __init__(self, abscissa_key, report_filename=None, 
                 error_getter=get_error_from_field,
                 simulation_dir='.', report_dir='.',
                 with_respect_to_resolution=False):
        self.abscissa_key = abscissa_key
        self.report_filename = report_filename
        self.error_getter = error_getter
        self.simulation_dir = simulation_dir
        self.report_dir = report_dir
        self.with_respect_to_resolution = with_respect_to_resolution
        
    def preamble(self, options):
        self.report_file = None
        if self.report_filename:
            try:
                self.report_file = open('{}/{}'.format(
                    self.report_dir, self.report_filename), 'w')
            except IndexError:
                pass
        self.abscissae = {}
        self.errors = {}
        self.rates = {}

    def postamble(self, options):
        if self.report_file:
            self.report_file.close()
        
    def __call__(self, options):
        current_id = options.get_string()
        
        # n.b. need to convert from integer to float
        current_abs = float(options[self.abscissa_key])
        try:
            current_err = abs(
                self.error_getter(options, self.simulation_dir))
        except Failure as state:
            return self.print_end(state, options)
        
        # register current values
        self.abscissae[current_id] = current_abs
        self.errors[current_id] = current_err
        msg = ' error: ' + self.error_format.format(current_err)
        
        # now try loading the values corresponding to the previous
        # mesh resolution and calculate the convergence rate
        try:
            previous_id = options.get_string(relative={self.abscissa_key: -1})
            
            previous_abs = self.abscissae[previous_id]
            previous_err = self.errors[previous_id]
            
            # calculate convergence rate
            self.rates[current_id] = log(current_err/previous_err) / \
                                     log(current_abs/previous_abs)
            if self.with_respect_to_resolution:
                # if resolution rather than mesh/timestep size is
                # represented, the ratio of abscissae should be
                # reversed
                self.rates[current_id] *= -1
            msg += '   rate: ' + self.rate_format.\
                   format(self.rates[current_id])
        except:
            # not enough info
            self.rates[current_id] = nan

        if self.report_file:
            self.report_file.write('{}  {}\n'.format(current_id, msg))
            
        self.print_end(Success(msg), options)

        
class WriteXmlForConvergenceTests(SerialFunctor):
    def __init__(self, convergence_abscissa_key,
                 template_filename='regressiontest.xml.template',
                 target_filename=None,
                 template_dir='.', simulation_dir='.',
                 with_respect_to_resolution=False):
        if not HAVE_JINJA2:
            raise Exception('jinja2 not installed; needed by this functor')
        self.convergence_abscissa_key = convergence_abscissa_key
        self.template_dir = template_dir
        self.template_filename = template_filename
        # target_filename will be defaulted later
        self.target_filename = target_filename
        self.simulation_dir = simulation_dir
        self.with_respect_to_resolution = with_respect_to_resolution

        
    def preamble(self, options):
        # the following lists will accumulate items as we loop over
        # the tree
        self.simulations = []
        self.abscissa_variables = []
        self.error_variables = []
        self.rate_variables = []

        # the leaves of the options tree will overlap in simulation
        # commands.  There are different ways of dealing with this,
        # but the simplest is perhaps to keep a register to avoid
        # duplicating commands.
        self.register = []


    def append_commands(self, options):
        """
        Appends a command line to the 'commands' list.  When postamble() is
        called and the list is passed to the template engine, the
        lines will get joined together.
        """
        msg = ''

        if options.simulation_name not in self.register:
            self.simulations.append({
                'name': options.simulation_name,
                'args': options.simulation_args, })
            self.register.append(options.simulation_name)
            msg += '\nincluded ' + options.simulation_name

        return msg

        
    def append_abscissa_variable(self, options):
        label = 'abscissa_' + options.get_string()
        self.abscissa_variables.append({
            'label': label,
            'value': options[self.convergence_abscissa_key] })
        return '\nassigned ' + label

        
    def append_error_variable(self, options):
        label = 'error_' + options.get_string()
        try:
            rel_op = options.relational_operator
        except AttributeError:
            # default to 'error <' test
            rel_op = 'lt'
        self.error_variables.append({
            'label': label,
            'simulation_name': options.simulation_name,
            'phase_name': options.phase_name,
            'name': options.error_variable_name,
            'calculation': options.error_aggregation,
            'timestep_index': options.error_timestep_index,
            'rel_op': rel_op,
            'threshold': options.max_error_norm })
        return '\nassigned ' + label


    def get_rate_label(self, options):
        stem = options.get_string(exclude=[self.convergence_abscissa_key])
        # use the previous and current abscissae to form suffices for
        # the label
        try:
            suf1 = options.get_string(only=[self.convergence_abscissa_key],
            relative={self.convergence_abscissa_key: -1})
        except IndexError:
            # abort if the previous one doesn't exist
            return None
        suf2 = options.get_string(only=[self.convergence_abscissa_key])
        return 'rate_' + join(stem, suf1, suf2)


    def append_rate_variable(self, options):
        label = self.get_rate_label(options)
        if not label:
            # abort if rate cannot be calculated
            return ''
        try:
            rel_op = options.relational_operator
        except AttributeError:
            # default to 'rate >' test
            rel_op = 'gt'
        self.rate_variables.append({
            'label': label,
            'key': options.get_string(),
            'key_prev': options.get_string(
                relative={self.convergence_abscissa_key: -1}),
            'sign': '-' if self.with_respect_to_resolution else '',
            'rel_op': rel_op,
            'threshold': options.min_convergence_rate })
        return '\nassigned ' + label


    def __call__(self, options):
        msg = ''
        msg += self.append_commands(options)
        msg += self.append_abscissa_variable(options)
        msg += self.append_error_variable(options)
        msg += self.append_rate_variable(options)
        self.print_end(Success(msg), options)

            
    def postamble(self, options):
        jr = Jinja2()
        if self.target_filename:
            target_filename = self.target_filename
        else:
            target_filename = options.problem_name + '.xml'
        jr.render(self.template_filename, target_filename,
                  self.template_dir, '.', problem=options,
                  simulation_dir=self.simulation_dir,
                  simulations=self.simulations,
                  abscissa_variables=self.abscissa_variables,
                  error_variables=self.error_variables,
                  rate_variables=self.rate_variables)
        

class WriteRulesForMeshing(SerialFunctor):
    def __init__(self, target_filename='Meshing.mk', mesh_dir='.'):
        self.target_filename = target_filename
        self.mesh_dir = mesh_dir
        
    def preamble(self, options):
        self.target_file = open(self.target_filename, 'w')
        self.target_file.write('tk')
        # keep track of meshes we've already made rules for
        self.register = []

    def __call__(self, options):
        if options.mesh_name not in self.register:
            # tk
            self.target_file.write('tk')
            self.register.append(options.mesh_name)
            msg += '\nincluded ' + options.mesh_name
            
    def postamble(self, options):
        self.target_file.close()
