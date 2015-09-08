"""
This module contains functionality for batch-processing
simulations, interpolating between simulated fields and quasi-analytic
solutions, examining error norms and convergence rates, and writing an
XML file to do all of the above.  The packages options_iteration and
jinja2 are required.

About the interpolations: for the Buckley-Leverett test case, it is
straightforward to compare the the 1D simulations to the expected 1D
quasi-analytical solution at the latter's point locations; a
piecewise-linear interpolant is constructed between the simulation's
points (get_error_with_1d_solution).  This is difficult to extend to
2D and 3D, but not if the interpolation is done the other way round -
the analytical solution is used to interpolate at each simulation
point (get_error_from_field).  The jump discontinuity of the
analytical solution will be ill-represented, but we can still expect
first order convergence of the l1-errors.  However, l2-errors are
deprecated.  Their reported convergence rates can be seen to be much
less than their l1 counterparts, presumably as a result of the
squaring of errors at the discontinuity.
"""

from options_iteration.utilities import SerialFunctor, Failure, Success, \
    check_file_exists
import numpy
import vtktools
from fluidity_tools import stat_parser

try:
    import jinja2
    HAVE_JINJA2 = True
except:
    HAVE_JINJA2 = False


def interp_using_one_dimensional_solution(
        x, one_dimensional_solution_filename):
    """
    Interpolates at point x using the given 1D profile.
    """
    [xa, va] = read_reference_solution(one_dimensional_solution_filename)
    return numpy.interp(x, xa, va)

    
def read_reference_solution(filename):
    """
    Converts a file containing a column of x-coordinates and a column
    of values into corresponding lists.
    """
    x, v = [], []
    with open(filename, "r") as f:
        f.seek(0)
        for l in f:
            if not l.strip(): continue
            x.append(float(l.split()[0]))
            v.append(float(l.split()[1]))
    return sort(x, v)


def read_numerical_solution(filename, field_descriptor):
    """
    Converts a vtu file into a list of x-coordinates and field
    values.
    """
    vtu_obj = vtktools.vtu(filename)
    x = vtu_obj.GetLocations()[:,0]
    v = vtu_obj.GetScalarField(field_descriptor)
    return sort(x, v)

def sort(x, v):
    isort = sorted(range(len(x)), key=lambda i: x[i])
    x = numpy.array([x[i] for i in isort])
    v = numpy.array([v[i] for i in isort])
    return x, v

        
def get_error_with_1d_solution(options, results_dir='.'):
    """
    Computes the L1 norm.  Uniform, linear elements are assumed, so
    the integral over the domain can be approximated by the
    trapezium rule.
    """
    reference_filename = options['reference_solution_filename']
    check_file_exists(reference_filename)        
    [xa, va] = read_reference_solution(reference_filename)
    
    numerical_filename = '{}/{}'.format(results_dir, options['vtu_filename'])
    check_file_exists(numerical_filename)        
    [xn, vn] = read_numerical_solution(numerical_filename,
                                       options['field_descriptor'])
    
    vn_interp = numpy.interp(xa, xn, vn)
    eps = numpy.abs(vn_interp - va)
    return (eps[0]/2 + sum(eps[1:-1]) + eps[-1]/2)*options['el_size_x']
   

def get_error_from_field(options, results_dir='.'):
    stat_filename = '{}/{}.stat'.format(
        results_dir, options['simulation_name'])
    check_file_exists(stat_filename)
    stat = stat_parser(stat_filename)
    
    phase = options['phase_name']
    var = options['error_variable_name']
    calc_type = options['error_calculation']
    timestep_index = options['timestep_index']
    try:
        # n.b. assume the last timestep is required
        return stat[phase][var][calc_type][timestep_index]
    except KeyError:
        raise Failure(
            ("\nget_error_from_field expected to find \n"+\
             "{0}::{1} in the stat file; \n"+\
             "has this been defined in the options file?").\
            format(phase, var))


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
    raise""".format(results_dir, options['simulation_name'], var_name,
           options['phase_name'], options['error_variable_name'],
           options['error_calculation'], options['timestep_index'])


class StudyConvergence(SerialFunctor):
    error_format = '{:.3e}'
    rate_format = '{:.6f}'

    def __init__(self, abscissa_key, report_filename, 
                 error_getter=get_error_from_field,
                 naming_keys=[], excluded_naming_keys=[],
                 results_dir='.', report_dir='.',
                 with_respect_to_resolution=False):
        self.abscissa_key = abscissa_key
        self.report_filename = report_filename
        self.error_getter = error_getter
        self.naming_keys = naming_keys
        self.excluded_naming_keys = excluded_naming_keys
        self.results_dir = results_dir
        self.report_dir = report_dir
        self.with_respect_to_resolution = with_respect_to_resolution
        
    def preamble(self, options):
        try:
            self.report_file = open('{}/{}'.format(
                self.report_dir, self.report_filename), 'w')
        except IndexError:
            self.report_file = None
        self.abscissae = {}
        self.errors = {}
        self.rates = {}

    def postamble(self, options):
        if self.report_file:
            self.report_file.close()
        
    def __call__(self, options):
        current_id = options.str(only=self.naming_keys,
                                 exclude=self.excluded_naming_keys)
        
        # n.b. need to convert from integer to float
        current_abs = float(options[self.abscissa_key])
        try:
            current_err = numpy.abs(
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
            previous_id = options.str(
                only=self.naming_keys,
                exclude=self.excluded_naming_keys,
                relative={self.abscissa_key: -1})
            
            previous_abs = self.abscissae[previous_id]
            previous_err = self.errors[previous_id]
            
            # calculate convergence rate
            self.rates[current_id] = numpy.log(current_err/previous_err) / \
                                     numpy.log(current_abs/previous_abs)
            if self.with_respect_to_resolution:
                # if resolution rather than mesh/timestep size is
                # represented, the ratio of abscissae should be
                # reversed
                self.rates[current_id] *= -1
            msg += '   rate: ' + self.rate_format.\
                   format(self.rates[current_id])
        except:
            # not enough info
            self.rates[current_id] = numpy.nan

        if self.report_file:
            self.report_file.write('{}  {}\n'.format(current_id, msg))
            
        self.print_end(Success(msg), options)



class WriteXml(SerialFunctor):
    trim_blocks = True
    lstrip_blocks = True

    def __init__(self, convergence_abscissa_key, 
                 error_renderer=render_error_from_field,
                 naming_keys=[], excluded_naming_keys=[],
                 template_dir='.', mesh_dir='.', simulation_dir='.',
                 with_respect_to_resolution=False):
        
        if not HAVE_JINJA2:
            raise Exception('jinja2 not installed; needed by this functor')
        self.convergence_abscissa_key = convergence_abscissa_key
        self.error_renderer = error_renderer
        self.naming_keys = naming_keys
        self.excluded_naming_keys = excluded_naming_keys
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

        if options['mesh_name'] not in self.register:
            self.mesh_commands.append(
                ' '.join(options['meshing_args']))
            self.register.append(options['mesh_name'])
        msg += '\n' + options['mesh_name']

        if options['simulation_name'] not in self.register:
            self.simulation_commands.append(
                'echo "Running {}"'.format(options['simulation_name']))
            self.simulation_commands.append(
                ' '.join(options['simulation_args']))
            self.register.append(options['simulation_name'])
        msg += '\n' + options['simulation_name']

        return msg

        
    def append_abscissa_variable(self, options):
        name = 'abscissa_' + options.str(
            only=self.naming_keys, exclude=self.excluded_naming_keys)
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
        name = 'error_' + options.str(
            only=self.naming_keys, exclude=self.excluded_naming_keys)
        self.variables.append({
            'name': name,
            'code': self.error_renderer(options, name, self.simulation_dir),
            'test_code': '',
            'metric_type': 'error',
            'rel_op': 'lt',
            'threshold': options.max_error_norm })
        return '\n' + self.variables[-1]['name']


    def get_rate_name(self, options):
        stem = options.str(
            only=self.naming_keys,
            exclude=self.excluded_naming_keys+[self.convergence_abscissa_key])
        # use the previous and current abscissae to form suffices for
        # the name
        try:
            suf1 = options.str(only=[self.convergence_abscissa_key],
                               relative={self.convergence_abscissa_key: -1})
        except IndexError:
            # abort if the previous one doesn't exist
            return None
        suf2 = options.str(only=[self.convergence_abscissa_key])
        return 'rate_{}_{}_{}'.format(stem, suf1, suf2)        


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
        key = options.str(only=self.naming_keys,
                          exclude=self.excluded_naming_keys)
        key_prev = options.str(only=self.naming_keys,
                               exclude=self.excluded_naming_keys,
                               relative={self.convergence_abscissa_key: -1})
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
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('.'))
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
