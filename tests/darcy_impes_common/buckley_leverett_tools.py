import numpy
import vtktools

import functors


def interp_using_analytic(x, analytic_filename):
    """Interpolates at point x using the profile given by
    analytic_filename."""
    [xa, va] = read_analytic_solution(analytic_filename)
    return numpy.interp(x, xa, va)

def read_analytic_solution(filename):
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

def read_numeric_solution(filename, field_descriptor):
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


class BuckleyLeverettErrorCalculator:

    analytic_naming_keys = ['field']
    
    def __init__(self, analytic_filename_format,
                 simulation_naming_keys=None,
                 simulation_results_suffix='_1.vtu'):
        self.analytic_filename_format = analytic_filename_format
        self.simulation_naming_keys = simulation_naming_keys
        self.simulation_results_suffix = simulation_results_suffix
        self.host_functor = None

    def with_host(self, host_functor):
        self.host_functor = host_functor
        return self
        
    def __call__(self, options):
        """
        Computes the L1 norm.  Uniform, linear elements are assumed, so
        the integral over the domain can be approximated by the
        trapezium rule.
        """
        [xa, va] = self.read_analytic_solution(options)
        [xn, vn] = self.read_numeric_solution(options)
        vn_interp = numpy.interp(xa, xn, vn)
        eps = numpy.abs(vn_interp - va)
        return (eps[0]/2 + sum(eps[1:-1]) + eps[-1]/2)*options['EL_SIZE_X']
      
    def read_analytic_solution(self, options):
        """
        Converts a file containing a column of x-coordinates and a column
        of values into corresponding lists.
        """
        filename = self.analytic_filename_format.format(
            options.str(self.analytic_naming_keys))
        return read_analytic_solution(filename)
        
    def read_numeric_solution(self, options):
        """
        Converts a vtu file into a list of x-coordinates and field
        values.
        """
        filename = options['simulation_name'] + self.simulation_results_suffix
        self.host_functor.check_file_exists(filename)
        return read_numeric_solution(filename, options['field_descriptor'])
