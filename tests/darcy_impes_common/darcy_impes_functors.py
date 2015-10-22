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

from opiter.utilities import SerialFunctor, Failure, Success, \
    check_file_exists
from fluidity_tools import stat_parser
from numpy import abs, log, nan

try:
    from jinja2 import Environment, FileSystemLoader
    HAVE_JINJA2 = True
except:
    HAVE_JINJA2 = False


def join(words):
    "Joins words with underscores."
    return '_'.join(([w for w in words if w]))


def get_error_from_field(options, results_dir='.'):
    stat_filename = '{}/{}.stat'.format(
        results_dir, options.simulation_name)
    check_file_exists(stat_filename)
    stat = stat_parser(stat_filename)
    
    phase = options.phase_name
    var = options.variable_name
    calc_type = options.error_aggregation
    index = options.error_timestep_index
    try:
        # n.b. assume the last timestep is required
        return stat[phase][var][calc_type][index]
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
                 results_dir='.', report_dir='.',
                 with_respect_to_resolution=False):
        self.abscissa_key = abscissa_key
        self.report_filename = report_filename
        self.error_getter = error_getter
        self.results_dir = results_dir
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
        current_id = options.get_string(only=['sim'])
        
        # n.b. need to convert from integer to float
        current_abs = float(options[self.abscissa_key])
        try:
            current_err = abs(
                self.error_getter(options, self.results_dir))
        except Failure as state:
            return self.print_end(state, options)
        
        # register current values
        self.abscissae[current_id] = current_abs
        self.errors[current_id] = current_err
        msg = ' error: ' + self.error_format.format(current_err)
        
        # now try loading the values corresponding to the previous
        # mesh resolution and calculate the convergence rate
        try:
            previous_id = options.get_string(
                only=['sim'], relative={self.abscissa_key: -1})
            
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



def render_error_from_field(options, var_name, results_dir='.'):
    return """
from fluidity_tools import stat_parser
stat = stat_parser('{0}/{1}.stat')
try:
    {2} = stat['{3}']['{4}']['{5}'][{6}]
except KeyError:
    print '''
Expected to find {3}::{4} in the stat file; 
has this been defined in the options file?'''
    raise""".format(results_dir, options.simulation_name, var_name,
           options.error_phase_name, options.error_variable_name,
           options.error_calculation, options.error_timestep_index)



class WriteXmlForConvergenceTests(SerialFunctor):
    def __init__(self, convergence_abscissa_key, 
                 error_renderer=render_error_from_field,
                 template_dir='.', mesh_dir='.', simulation_dir='.',
                 with_respect_to_resolution=False):
        if not HAVE_JINJA2:
            raise Exception('jinja2 not installed; needed by this functor')
        self.convergence_abscissa_key = convergence_abscissa_key
        self.error_renderer = error_renderer
        self.template_dir = template_dir
        self.mesh_dir = mesh_dir
        self.simulation_dir = simulation_dir
        self.with_respect_to_resolution = with_respect_to_resolution

        
    def preamble(self, options):
        # the following lists will accumulate items as we loop over
        # the tree
        self.mesh_commands = []
        self.simulation_commands = []
        self.variables = []

        # the leaves of the options tree will overlap in meshing and
        # simulation commands.  There are different ways of dealing
        # with this, but the simplest is perhaps to keep a register to
        # avoid duplicating commands.
        self.register = []


    def append_commands(self, options):
        """
        Appends a command line to the 'commands' list.  When postamble() is
        called and the list is passed to the template engine, the
        lines will get joined together.
        """
        msg = ''

        if options.mesh_name not in self.register:
            self.mesh_commands.append(
                ' '.join(options.meshing_args))
            self.register.append(options.mesh_name)
        msg += '\n' + options.mesh_name

        if options.simulation_name not in self.register:
            self.simulation_commands.append(
                'echo "Running {}"'.format(options.simulation_name))
            self.simulation_commands.append(
                ' '.join(options.simulation_args))
            self.register.append(options.simulation_name)
        msg += '\n' + options.simulation_name

        return msg

        
    def append_abscissa_variable(self, options):
        name = 'abscissa_' + options.str()
        self.variables.append({
            'name': name,
            'code': '\n{} = {}'.format(
                name, options[self.convergence_abscissa_key]),
            'test_code': '',
            'metric_type': 'abscissa',
            'rel_op': None,
            'threshold': None })
        return '\n' + self.variables[-1]['name']

        
    def append_error_variable(self, options):
        name = 'error_' + options.str()
        self.variables.append({
            'name': name,
            'code': self.error_renderer(options, name, self.simulation_dir),
            'test_code': '',
            'metric_type': 'error',
            'rel_op': 'lt',
            'threshold': options.max_error_norm })
        return '\n' + self.variables[-1]['name']


    def get_rate_name(self, options):
        stem = options.str(exclude=[self.convergence_abscissa_key])
        # use the previous and current abscissae to form suffices for
        # the name
        try:
            suf1 = options.str(only=[self.convergence_abscissa_key],
                               relative={self.convergence_abscissa_key: -1})
        except IndexError:
            # abort if the previous one doesn't exist
            return None
        suf2 = options.str(only=[self.convergence_abscissa_key])
        return 'rate_' + '_'.join(([s for s in [stem, suf1, suf2] if s]))


    def append_rate_variable(self, options):
        name = self.get_rate_name(options)
        if not name:
            # abort if rate cannot be calculated
            return ''
        self.variables.append({
            'name': name,
            'code': '',
            'test_code': self.render_rate(options, name),
            'metric_type': 'rate',
            'rel_op': 'gt',
            'threshold': options.min_convergence_rate })
        return '\n' + self.variables[-1]['name']


    def render_rate(self, options, rate_name):
        key = options.str()
        key_prev = options.str(relative={self.convergence_abscissa_key: -1})
        sign = '-' if self.with_respect_to_resolution else ''
        return """
import numpy
current_abscissa = float(abscissa_{0})
current_error = numpy.abs(error_{0})
previous_abscissa = float(abscissa_{1})
previous_error = numpy.abs(error_{1})
{3} = \\
    {2}numpy.log(current_error/previous_error) / \\
    numpy.log(current_abscissa/previous_abscissa)""".format(
        key, key_prev, sign, rate_name)


    def __call__(self, options):
        msg = ''
        msg += self.append_commands(options)
        msg += self.append_abscissa_variable(options)
        msg += self.append_error_variable(options)
        msg += self.append_rate_variable(options)
        self.print_end(Success(msg), options)

            
    def postamble(self, options):
        # fire up the template engine 
        env = Environment(
            loader=FileSystemLoader('.'))
        template = env.get_template('{}/{}'.format(
            self.template_dir, options.xml_template_filename))

        # pass it the final options dict, which will include general
        # information, and the lists we've been building up
        with open(options.xml_target_filename, 'w') as f:
            f.write(template.render(
                problem=options,
                mesh_dir = self.mesh_dir,
                simulation_dir = self.simulation_dir,
                mesh_commands=self.mesh_commands,
                simulation_commands=self.simulation_commands,
                variables=self.variables))
