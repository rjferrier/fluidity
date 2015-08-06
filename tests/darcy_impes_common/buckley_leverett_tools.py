import numpy
import vtktools
# from functors import check_file_exists

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

        
# class GetErrorWithOneDimensionalSolution:
#     def __init__(self, results_dir='.'):
#         self.results_dir = results_dir

#     def __call__(self, options):
#         """
#         Computes the L1 norm.  Uniform, linear elements are assumed, so
#         the integral over the domain can be approximated by the
#         trapezium rule.
#         """
#         reference_filename = options['reference_solution_filename']
#         check_file_exists(reference_filename)        
#         [xa, va] = read_reference_solution(reference_filename)
        
#         numerical_filename = '{}/{}'.format(
#             self.working_dir, options['vtu_filename'])
#         check_file_exists(numerical_filename)        
#         [xn, vn] = read_numerical_solution(numerical_filename,
#                                            options['field_descriptor'])
        
#         vn_interp = numpy.interp(xa, xn, vn)
#         eps = numpy.abs(vn_interp - va)
#         return (eps[0]/2 + sum(eps[1:-1]) + eps[-1]/2)*options['EL_SIZE_X']
