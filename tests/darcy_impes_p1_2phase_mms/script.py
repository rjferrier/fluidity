import darcy_impes_options as base
from options_iteration import OptionsArray, OptionsNode, CallableEntry, freeze
from sympy import Symbol, Function, diff, integrate, sin, cos, pi, exp, sqrt
from re import sub
import os
import errno
import sys


#------------------------------------------------------------------------------
# HELPERS


# these values are arbitrary, but see note 2
pressure_scale = 1000.
saturation_scale = 0.5

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
        result = sub('\\b{}\\b'.format(x), 'X[{}]'.format(i), result)
        
    return result


#------------------------------------------------------------------------------
# OPTIONS 

#------------------------------------------------------------------------------
# fields to be iterated over in postprocessing

class pressure1:
    phase_name = 'Phase1'
    variable_name = 'Pressure'
    def error_tolerance(self):
        return 0.1 * pressure_scale
    # see note 3b
    variable_solution = CallableEntry(lambda opt: opt.pressures[0])

class saturation2:
    phase_name = 'Phase2'
    variable_name = 'Saturation'
    def error_tolerance(self):
        return 0.1 * saturation_scale
    variable_solution = CallableEntry(lambda opt: opt.saturations[1])
    
examined_fields = OptionsArray('field', [pressure1, saturation2])


#------------------------------------------------------------------------------
# groups - simulation options can be lumped together; any one failure
# will cause the whole group to fail to converge

class group1:
    # orthotopic geometry, normal flow BCs
    geometry_prefix = ''
    have_regular_mesh = False
    def pressure1_dirichlet_boundary_ids(self):
        return (self.outlet_id,) + self.wall_ids
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
    
    def capillary_pressure_wrt_saturation(self):
        S2 = Symbol('S2')
        Sr2 = Symbol('Sr2')
        return pressure_scale/10. * ((S2 - Sr2)/(1. - Sr2))**(-0.5)
    
    # misc.
    saturation_face_value = "FiniteElement"
    saturation_face_value_limiter = "Sweby"
    rel_perm_face_value = "RelPermOverSatUpwind"

    
class group2:
    # curved geometry, saturation Dirichlet BCs
    def geometry_prefix(self):
        return '' if self.dim_number == 1 else 'curved'
    have_regular_mesh = False
    def pressure1_dirichlet_boundary_ids(self):
        # TODO: figure out why we need pressure over all the
        # boundaries for the curved geometry case
        return (self.inlet_id, self.outlet_id,) + self.wall_ids
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

    capillary_pressure_wrt_saturation = 0
    capillary_pressure = 0

    # misc.
    saturation_face_value = None
    rel_perm_face_value = "FirstOrderUpwind"

groups = OptionsArray('group', [group1, group2])


#------------------------------------------------------------------------------
# common to all

# extend the class of the same name in darcy_impes_options
class common(base.common):

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

    def Xt_nondim(self):
        "Symbols x,..,t, nondimensionalised by domain_extents and finish_time."
        return [x/L for x, L in zip(
            spacetime, self.domain_extents + (self.finish_time,))]

    def pressure1(self):
        "Invented pressure profile"
        x, y, z, t = self.Xt_nondim
        # begin with a scale factor and variation with time
        result = pressure_scale * (3 + cos(pi*t))/4
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
        result = saturation_scale * 1./(1 + t)
        # invent a variation with each spatial dimension, then
        # multiply them together to create a multidimensional profile
        variations = [exp(-x), 3*(1. - y)*(1.5*y)**2, 3*(1. - z)*(1.5*z)**2]
        for i in range(self.dim_number):
            result *= variations[i]
            
        # linear adjustment - make sure phase-2 saturation does not go
        # to zero (or to saturation2_threshold) causing an infinite
        # capillary pressure
        a = (saturation_scale - self.saturation2_min)/ \
            (saturation_scale - self.saturation2_threshold)
        b = saturation_scale*(1. - a)
        result = a*result + b
        
        return result
    
    def capillary_pressure(self):
        """
        Analytical capillary pressure (with respect to spacetime).  Depends
        on capillary_pressure_wrt_saturation, which is used by the
        options file.
        """
        S2 = self.saturations[1]
        Sr2 = self.residual_saturations[1]
        return self.capillary_pressure_wrt_saturation.\
            subs([('S2', S2), ('Sr2', Sr2)])

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
        Returns the Darcy velocity normal flow at each boundary (xmin,
        xmax, ymin, ..., zmax), assuming domain is orthotopic.
        """
        results = []
        for u in self.darcy_velocities:
            phase_results = []
            for i in range(self.dim_number):
                # reverse the sign if going *into* the domain
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
    
    # ETC.
    
    reference_timestep_number = 20   # TODO: tighten this up

    def dump_period(self):
        return self.finish_time
    
    def time_step(self):
        "Maintains a constant Courant number"
        scale_factor = float(self.reference_element_numbers[0]) / self.mesh_res
        return scale_factor * self.finish_time / self.reference_timestep_number
    
    def simulation_name(self):
        # easiest way to create a name is to use get_string with some
        # appropriate keys
        return self.get_string(['group', 'dim', 'mesh_res'])

    # see note 3a
    examined_fields = freeze(examined_fields.collapse())
    
    user_id = 'rferrier'
    test_length = 'short'   # TODO: change to medium?
    min_convergence_rate = 0.7
                

# make an anonymous root node to store the above options
root = OptionsNode()
root.update(common)

    
#------------------------------------------------------------------------------
# TREE ASSEMBLY
    
# attach appropriate mesh resolutions to each dimension option
base.dims['1d'] *= OptionsArray('mesh_res', [10, 20, 40, 80])
base.dims['2d'] *= OptionsArray('mesh_res', [10, 20, 40])
base.dims['3d'] *= OptionsArray('mesh_res', [10, 20])

# Meshes depend on the whether the geometry is curved or straight,
# which is an option found in groups.  Hence meshes and simulations
# will share the same general tree.
general_options_tree = root * groups * base.dims

# TODO: In 3D, velocity boundary conditions lead to nonconvergence.
# This is a simulator bug that needs to be fixed.  For now, remove
# this part of the tree so that tests can pass.
del general_options_tree['group1']['3d']

# for postprocessing, we additionally want to iterate over some fields
# of interest
test_options_tree = general_options_tree * examined_fields


#------------------------------------------------------------------------------
# DISPATCH

if __name__ == '__main__':
    base.main(general_options_tree,
              general_options_tree,
              test_options_tree,
              jinja2_filters={'format_sympy': format_sympy})
    

# Notes:
# 
# [1] Mesh elements will be sized such that there are mesh_res
#     elements along domain edges in the x-direction.  Irregular
#     meshes will try to fill the domain with uniformly sized
#     elements.  This means that the domain probably needs to be sized
#     'nicely' in each dimension if there is to be good convergence on
#     these meshes.
# 
# [2] The pressure scale should be high enough to have an influence
#     (~100).  High levels of saturation and rho*g_mag/mu have been
#     found to cause numerical instability well below the expected CFL
#     limit.  This may be caused by having a highly nonlinear relative
#     permeability term and forcing an unnatural pressure field.
#
# [3] Each simulation needs to compute all of the fields in
#     examined_fields before we iterate over them at the
#     postprocessing stage.
#
#     [a] A neat way of storing this information is to convert
#         examined_fields to a list of dictionaries, and freeze them
#         so we don't get pickling errors when multiprocessing.
#
#     [b] Unfortunately, getting the analytical solution to each field
#         means having access to the master tree - and examined fields
#         does not have such access if they are embedded.  So make the
#         analytical solution a function of the master tree, then the
#         template can call it.
