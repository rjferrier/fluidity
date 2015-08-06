
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
   

class GetErrorFromField:
    def __init__(self, results_dir='.'):
        self.results_dir = results_dir

    def __call__(self, options):
        # settings
        calc_type = 'integral'      # can be integral or l2norm
        timestep_index = -1
        
        stat_filename = '{}/{}.stat'.format(
            self.results_dir, options['simulation_name'])
        check_file_exists(stat_filename)
        stat = stat_parser(stat_filename)
        
        phase = options['phase_name']
        var = options['error_variable_name']
        try:
            # n.b. assume the last timestep is required
            return stat[phase][var][calc_type][timestep_index]
        except KeyError:
            raise Failure(
                ("\nGetErrorFromField expected to find \n"+\
                 "{0}::{1} in the stat file; \n"+\
                 "has this been defined in the options file?").\
                format(phase, var))
 
        
class GetErrorWithOneDimensionalSolution:
    def __init__(self, results_dir='.'):
        self.results_dir = results_dir

    def __call__(self, options):
        """
        Computes the L1 norm.  Uniform, linear elements are assumed, so
        the integral over the domain can be approximated by the
        trapezium rule.
        """
        reference_filename = options['reference_solution_filename']
        check_file_exists(reference_filename)        
        [xa, va] = read_reference_solution(reference_filename)
        
        numerical_filename = '{}/{}'.format(
            self.results_dir, options['vtu_filename'])
        check_file_exists(numerical_filename)        
        [xn, vn] = read_numerical_solution(numerical_filename,
                                           options['field_descriptor'])
        
        vn_interp = numpy.interp(xa, xn, vn)
        eps = numpy.abs(vn_interp - va)
        return (eps[0]/2 + sum(eps[1:-1]) + eps[-1]/2)*options['EL_SIZE_X']


class StudyConvergence(SerialFunctor):
    error_format = '{:.3e}'
    rate_format = '{:.6f}'

    def __init__(self, abscissa_key,
                 error_getter_class=GetErrorFromField,
                 naming_keys=[], excluded_naming_keys=[],
                 source_dir='.', target_dir='.',
                 with_respect_to_resolution=False):
        self.abscissa_key = abscissa_key
        self.error_getter = error_getter_class(source_dir)
        self.naming_keys = naming_keys
        self.excluded_naming_keys = excluded_naming_keys
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.with_respect_to_resolution = with_respect_to_resolution
        
    def setup(self, options):
        try:
            self.report_file = open('{}/{}'.format(
                self.target_dir, options.report_filename), 'w')
        except IndexError:
            self.report_file = None
        self.abscissae = {}
        self.errors = {}
        self.rates = {}

    def teardown(self, options):
        if self.report_file:
            self.report_file.close()
        
    def __call__(self, options):
        current_id = options.str(only=self.naming_keys,
                                 exclude=self.excluded_naming_keys)
        
        # n.b. need to convert from integer to float
        current_abs = float(options[self.abscissa_key])
        try:
            current_err = numpy.abs(self.error_getter(options))
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
            msg += '   rate: ' + \
                   self.rate_format.format(self.rates[current_id])
        except:
            # not enough info
            self.rates[current_id] = numpy.nan

        if self.report_file:
            self.report_file.write('{}  {}\n'.format(current_id, msg))
            
        self.print_end(Success(msg), options)


# class WriteToFile(SerialFunctor):
    

class WriteXml(SerialFunctor):
    def __init__(self, convergence_abscissa_key, naming_keys=[],
                 excluded_naming_keys=[], template_dir='.'):
        if not HAVE_JINJA2:
            raise Exception('jinja2 not installed; needed by this functor')
        self.convergence_abscissa_key = convergence_abscissa_key
        self.naming_keys = naming_keys
        self.excluded_naming_keys = excluded_naming_keys
        self.template_dir = template_dir
        
    def setup(self, options):
        self.tests = []

    def teardown(self, options):
        # Import the Jinja 2 package here so that systems that don't
        # have it can still use the other functors.
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('.'))
        template = env.get_template('{}/{}'.format(
            self.template_dir, options.xml_template_filename))
        
        with open(options.xml_target_filename, 'w') as f:
            f.write(template.render(
                problem=options, tests=self.tests))
            
    def __call__(self, options):
        test_info = [['error', 'lt', options.max_error_norm],
                     ['rate',  'gt', options.min_convergence_rate]]
        msg = ''
        for ti in test_info:
            # do not write a test if a threshold is not given
            if not ti[2]:
                continue
            # do not write a convergence rate test if this is the
            # first result in the series
            if ti[0] == 'rate' and options.get_node_info(
                    self.convergence_abscissa_key).is_first():
                continue
            self.tests.append({
                'key': options.str(only=self.naming_keys,
                                   exclude=self.excluded_naming_keys),
                'metric_type': ti[0],
                'rel_op'     : ti[1],
                'threshold'  : ti[2] })
            msg += '\nwrote test: {} &{}; {}'.format(*ti)
        self.print_end(Success(msg), options)


