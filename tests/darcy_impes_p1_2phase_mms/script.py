import darcy_impes_options as base
from options_iteration import OptionsArray, OptionsNode
from options_iteration.utilities import smap, pmap, ExpandTemplate, \
    Jinja2Rendering, RunProgram, get_nprocs, check_entries
from options_iteration_extended_utilities import WriteXmlForConvergenceTests, \
    StudyConvergence
from sympy import Symbol, Function, diff, integrate, sin, cos, pi, exp, sqrt
from jinja2 import StrictUndefined
from re import sub
import os
import errno
import sys

## SETTINGS

problem_name = 'darcy_impes_p1_2phase_mms'
user_id = 'rferrier'
nprocs_max = 6

mesh_dir = 'meshes'
simulation_dir = 'simulations'


## HELPERS

spacetime = [Symbol(x) for x in 'xyzt']

def grad(scalar, dim_number):
    return [diff(scalar, spacetime[i]) for i in range(dim_number)]

def div(vector):
    try:
        return sum([diff(component, spacetime[i]) \
                    for i, component in enumerate(vector)])
    except TypeError:
        # not a list/tuple - differentiate wrt x
        return diff(vector, spacetime[0])
    
def mag(vector):
    try:
        return sqrt(sum([component**2 for component in vector]))
    except TypeError:
        # not a list/tuple - assume single component
        return abs(vector)
    
def format_sympy(expression):
    """
    Takes a Sympy expression and converts to a string which can be
    used in the body of a val(X,t) python function.
    """
    
    # start by stripping whitespace
    result = str(expression).rstrip()
    
    # sympy writes fractions with integers, e.g. 1/2, so we need to
    # append decimal points to all integers that aren't acting as
    # exponents, array subscripts or labels.  "1/2." is fine though.
    # A second pass is needed in case the pattern absorbs neighbouring
    # candidates.
    for i in range(2):
        result = sub('([^e*][ /*\-+()][0-9]+)([ /*\-+()"])', '\\1.\\2',
                     result)
        
    # another important conversion
    result = sub('Abs', 'abs', result)
        
    # replace x, y, z with X[0], X[1], X[2]
    for i, x in enumerate('xyz'):
        result = sub('([^a-z]){}([^a-z])'.format(x),
                     '\\1X[{}]\\2'.format(i), result)
        
    return result

        
## OPTIONS TREES

# define some global options
class global_options(base.global_options):

    # MMS-RELATED
    
    gravity_magnitude = 1.                   # see note 2
    absolute_permeability = 1.567346939e-9 
    porosity = 0.4
    
    # per-phase properties: regard second phase as wetting
    viscosities = (1.725e-5, 1.e-3)
    densities = (1.284, 1000.)
    def permeabilities(self):
        # relperms to come
        return [self.absolute_permeability * k_rel \
                for k_rel in self.relperms]

    # space and time scales
    domain_extents = (1.0, 1.2, 0.8)         # see note 1
    finish_time = 1.0
    
    # pressure and saturation scales (arbitrary, but see note 2)
    pressure1_scale = 1000.
    saturation2_scale = 0.5

    def pressure1_dirichlet_boundary_ids(self):
        return self.wall_ids + (self.outlet_id,)

    def Xt_nondim(self):
        "Symbols x,..,t, nondimensionalised by domain_extents and finish_time."
        return [x/L for x, L in zip(
            spacetime, self.domain_extents + (self.finish_time,))]

    def pressure1(self):
        "Invented pressure profile"
        x, y, z, t = self.Xt_nondim
        # begin with a scale factor and variation with time
        result = self.pressure1_scale * (3 + cos(pi*t))/4
        # invent a variation with each spatial dimension, then
        # multiply them together to create a multidimensional profile
        variations = [cos(pi*x), sin(pi*y), sin(pi*z)]
        for i in range(self.dim_number):
            result *= variations[i]
        return result

    saturation2_min = 0.2
    saturation2_threshold = 0.0
    
    def saturation2(self):
        "Invented saturation profile"
        x, y, z, t = self.Xt_nondim
        # begin with a scale factor and variation with time
        result = self.saturation2_scale * 1./(1 + t)
        # invent a variation with each spatial dimension, then
        # multiply them together to create a multidimensional profile
        variations = [exp(-x), 3*(1. - y)*(1.5*y)**2, 3*(1. - z)*(1.5*z)**2]
        for i in range(self.dim_number):
            result *= variations[i]
            
        # linear adjustment - make sure phase-2 saturation does not go
        # to zero (or to saturation2_threshold) and therefore does not
        # cause an infinite capillary pressure
        a = (self.saturation2_scale - self.saturation2_min)/ \
            (self.saturation2_scale - self.saturation2_threshold)
        b = self.saturation2_scale*(1. - a)
        result = a*result + b
        
        return result

    def pressures(self):
        pressure2 = self.pressure1 - self.capillary_pressure
        return (self.pressure1, pressure2)

    def saturations(self):
        return (1 - self.saturation2, self.saturation2)

    def gravity_direction(self):
        result = [0] * self.dim_number
        result[0] = 1
        return result
    
    def gravity(self):
        return [self.gravity_magnitude * g_dir \
                for g_dir in self.gravity_direction]
    
    def darcy_velocities(self):
        results = []
        # loop over phases
        for i in range(2):
            # get relevant scalars
            K = self.permeabilities[i]
            mu = self.viscosities[i]
            rho = self.densities[i]
            # compute vectors
            grad_p = grad(self.pressures[i], self.dim_number)
            results.append(
                [-K/mu*(grad_p_j - rho*g_j) \
                 for grad_p_j, g_j in zip(grad_p, self.gravity)])
        return results
    
    def boundary_normal_darcy_velocities(self):
        """
        Returns the Darcy velocity normal flow at each Cartesian boundary
        (xmin, xmax, ymin, ..., zmax).
        """
        results = []
        for u in self.darcy_velocities:
            phase_results = []
            for i in range(self.dim_number):
                for sign in (-1, 1):
                    phase_results.append(sign * u[i])
            results.append(phase_results)
        return results
                
    def saturation_sources(self):
        results = []
        t = spacetime[-1]
        # loop over phases
        for i in range(2):
            S = self.saturations[i]
            u = self.darcy_velocities[i]
            results.append(
                diff(self.porosity*S, t) + div(u))
        return results
                
    def divergence_check(self):
        return sum(div(u) - q for u, q in \
                   zip(self.darcy_velocities, self.saturation_sources))

    
    # SIMULATION
    
    problem_name = problem_name
    mesh_dir = mesh_dir
    simulation_dir = simulation_dir

    def dump_period(self):
        return self.finish_time
    
    reference_timestep_number = 20   # TODO tighten this up
    
    def time_step(self):
        "Maintains a constant Courant number"
        scale_factor = float(self.reference_element_numbers[0]) / self.mesh_res
        return scale_factor * self.finish_time / self.reference_timestep_number
    
    def simulation_name(self):
        return base.join(self.group,
                         self.dim[-1] + 'd',
                         str(int(self.mesh_res)))

    # RESULTS/TESTS
    
    user_id = user_id
    xml_target_filename = problem_name + '.xml'
    test_length = 'short'   # TODO change to medium?
    min_convergence_rate = 0.7
    def report_filename(self): 
        self.problem_name + '_report.txt'
    def max_error_norm(self):
        """
        Since we're already testing convergence rates, let's only test the
        absolute error norm for the first mesh.
        """
        scale = None
        # TODO replace get_node_info in options_iteration
        if self.get_node_info('mesh_res').is_first():
            if 'saturation' in self.field:
                scale = 1.
            elif 'pressure' in self.field:
                scale = self.pressure1_scale
        if scale:
            return 0.1 * scale
        else:
            return None


#---------------------------------------------------------------------

# Simulation options can be lumped together in groups; any one failure
# will cause the whole group to fail.

class group1:
    # orthotopic geometry, normal flow BCs
    geometry_prefix = ''
    have_regular_mesh = True
    saturation2_dirichlet_boundary_ids = ()
    def normal_velocity2_dirichlet_boundary_ids(self):
        return (self.inlet_id,) + self.wall_ids

    # Brooks-Corey relation
    relperm_relation_name = 'Corey2Phase'
    relperm_relation_exponents = None
    residual_saturations = (0.05, 0.1)
    def relperms(self):
        S = self.saturations
        Sr = self.residual_saturations
        n = self.relperm_relation_exponents
        return ((S[0] - Sr[0])**4,
                (1. - (S[0] - Sr[0])**2) * (1. - (S[0] - Sr[0]))**2)
    
    def capillary_pressure(self):
        S2 = Symbol('S2')
        Sr2 = Symbol('Sr2')
        return self.pressure1_scale/10. * ((S2 - Sr2)/(1. - Sr2))**(-0.5)
    
    # misc.
    saturation_face_value = None
    rel_perm_face_value = "FirstOrderUpwind"

    
class group2:
    # curved geometry, saturation Dirichlet BCs
    def geometry_prefix(self):
        return '' if self.dim_number == 1 else 'curved'
    have_regular_mesh = False
    def saturation2_dirichlet_boundary_ids(self):
        return (self.inlet_id,) + self.wall_ids
    normal_velocity2_dirichlet_boundary_ids = ()

    # quadratic relperm
    relperm_relation_name = 'PowerLaw'
    relperm_relation_exponents = (2, 2)
    residual_saturations = (0.2, 0.3)
    
    def relperms(self):
        S = self.saturations
        Sr = self.residual_saturations
        n = self.relperm_relation_exponents
        return ((S[0]-Sr[0])**n[0],
                (S[1]-Sr[1])**n[1])

    capillary_pressure = 0
    
    # misc.
    saturation_face_value = "FiniteElement"
    saturation_face_value_limiter = "Sweby"
    rel_perm_face_value = "RelPermOverSatUpwind"


#---------------------------------------------------------------------

root = OptionsNode()
root.update(global_options)

dims = OptionsArray('dim', [base.dim1, base.dim2, base.dim3], 
                    name_format=lambda s: s[-1]+'d')
groups = OptionsArray('group', [group1, group2])
    
# Create options trees.  Meshes depend on the whether the geometry is
# curved or straight, which is an option found in groups.  Hence
# meshes and simulations will share the same tree.
general_options_tree = dims
general_options_tree['1d'] *= OptionsArray('mesh_res', [10, 20, 40, 80])
general_options_tree['2d'] *= OptionsArray('mesh_res', [10, 20, 40])
general_options_tree['3d'] *= OptionsArray('mesh_res', [10, 20])
general_options_tree = root * groups * general_options_tree

# for od in general_options_tree.collapse():
#     print od.str(formatter='tree')

# for postprocessing, we additionally want to iterate over a couple of fields
test_options_tree = general_options_tree * \
                    OptionsArray('field', ['pressure1', 'saturation2'])

# # update all trees with global options
# general_options_tree.update(global_options)
# test_options_tree.update(global_options)

check_entries(general_options_tree)
check_entries(test_options_tree)



## PROCESSING


# get any args from the command line
if len(sys.argv) > 1:
    commands = sys.argv[1:]
else:
    commands = ['pre', 'mesh', 'run', 'post']
    

# make directories if necessary
if 'pre' in commands:
    for d in [mesh_dir, simulation_dir]:
        try:
            os.makedirs(d)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise

    
if 'xml' in commands:
    smap(WriteXmlForConvergenceTests('mesh_res', mesh_dir=mesh_dir, 
                                     simulation_dir=simulation_dir,
                                     with_respect_to_resolution=True),
         test_options_tree,
         message='Expanding XML file')
    
    
if 'pre' in commands:
    smap(ExpandTemplate('geo_template_filename', 'geo_filename',
                        target_dir_key='mesh_dir',
                        rendering_strategy=Jinja2Rendering({
                            'extensions': [base.RaiseExtension]})),
         general_options_tree,
         message="Expanding geometry files")

    smap(ExpandTemplate('simulation_options_template_filename',
                        'simulation_options_filename',
                        target_dir_key='simulation_dir',
                        rendering_strategy=Jinja2Rendering(
                            filters={'format_sympy': format_sympy})),
         general_options_tree,
         message="Expanding options files")

    
if 'mesh' in commands:
    pmap(RunProgram('meshing_args', 'geo_filename', 'mesh_name',
                    working_dir_key='mesh_dir'),
         general_options_tree,
         nprocs_max=nprocs_max, in_reverse=True, message="Meshing")

    
if 'run' in commands:
    pmap(RunProgram('simulation_args',
                    'simulation_prerequisite_filenames',
                    'simulation_name',
                    error_filename_key='simulation_error_filename',
                    working_dir_key='simulation_dir'),
         general_options_tree,
         nprocs_max=nprocs_max, in_reverse=True,
         message="Running simulations")
    
if 'post' in commands:
    smap(StudyConvergence('mesh_res', problem_name + '.txt', 
                          results_dir=simulation_dir,
                          with_respect_to_resolution=True),
         test_options_tree,
         message="Postprocessing")
    

# Notes:
# 
# [1] mesh elements will be sized such that there are mesh_res
# elements along domain edges in the x-direction.  Irregular meshes
# will try to fill the domain with uniformly sized elements.  This
# means that the domain probably needs to be sized 'nicely' in each
# dimension if there is to be good convergence on these meshes.
# 
# [2] The pressure scale should be high enough to have an influence
# (~100).  High levels of saturation and rho*g_mag/mu have been found
# to cause numerical instability well below the expected CFL limit.
# This may be caused by having a highly nonlinear relative
# permeability term and forcing an unnatural pressure field.
    
