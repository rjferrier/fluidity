import numpy
import vtktools

   
class BuckleyLeverettErrorCalculator:

    analytic_naming_keys = ['field']
    
    def __init__(self, analytic_filename_format,
                 simulation_naming_keys=None,
                 simulation_results_suffix='_1.vtu'):
        self.analytic_filename_format = analytic_filename_format
        self.simulation_naming_keys = simulation_naming_keys
        self.simulation_results_suffix = simulation_results_suffix
        
    def __call__(self, options):
        """
        Computes the L1 norm.  Uniform, linear elements are assumed, so
        the integral over the domain can be approximated by the
        trapezium rule.
        """
        [xa, va] = self.read_analytic_solution(options)
        [xn, vn] = self.read_numeric_solution(options)
        vn_interp = numpy.interp(x_a, x_n, v_n)
        eps = numpy.abs(vn_interp - v_a)
        return (eps[0]/2 + sum(eps[1:-1]) + eps[-1]/2)*options['EL_SIZE_X']

    def read_analytic_solution(self, options):
        """
        Converts a file containing a column of x-coordinates and a column
        of values into corresponding lists.
        """
        filename = self.analytic_filename_format.format(
            options.str(self.analytic_naming_keys))
        x, v = [], []
        with open(filename, "r") as f:
            f.seek(0)
            for l in f:
                if not l.strip(): continue
                x.append(float(l.split()[0]))
                v.append(float(l.split()[1]))
        return self.sort(x, v)

    def read_numeric_solution(self, options):
        """
        Converts a vtu file into a list of x-coordinates and field
        values.
        """
        filename = options['simulation_name'] + self.simulation_results_suffix
        vtu_obj = vtktools.vtu(filename)
        x = vtu_obj.GetLocations()[:,0]
        v = vtu_obj.GetScalarField(field_name)
        return self.sort(x, v)

    @staticmethod
    def sort(x, v):
        isort = sorted(range(len(x)), key=lambda i: x[i])
        x = numpy.array([x[i] for i in isort])
        v = numpy.array([v[i] for i in isort])
        return x, v
