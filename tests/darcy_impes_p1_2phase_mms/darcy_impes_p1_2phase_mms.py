import darcy_impes_base as base
from opiter import OptionsArray, OptionsNode, CallableOption,\
    Check, Remove, missing_dependencies, unpicklable
from sympy import Symbol, Function, diff, integrate, sin, cos, pi, exp, sqrt
from re import sub
import os
import errno
import sys
import copy


#----------------------------------------------------------------------
# helpers

# these values are arbitrary, but see note [1]
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


#----------------------------------------------------------------------
# OPTIONS 

#----------------------------------------------------------------------
# fields to be iterated over in postprocessing

class pressure1:
    phase_name = 'Phase1'
    variable_name = 'Pressure'
    def error_tolerance(self):
        return 0.1 * pressure_scale
    choose_solution = CallableOption(
        lambda pressures, saturations: pressures[0])

class saturation2:
    phase_name = 'Phase2'
    variable_name = 'Saturation'
    def error_tolerance(self):
        return 0.1 * saturation_scale
    choose_solution = CallableOption(
        lambda pressures, saturations: saturations[1])

# we are defining this array now because it is going to be used twice:
# once, collapsed and embedded in the simulation options; again, for
# building the testing tree
examined_fields = OptionsArray('field', [pressure1, saturation2])


#----------------------------------------------------------------------

# extend simulation options defined in darcy_impes_options
class simulation(base.simulation):
    
    gravity_magnitude = 1.                   # see note [1]
    absolute_permeability = 1.567346939e-9 
    porosity = 0.4
    
    # per-phase properties: regard second phase as wetting
    viscosities = (1.725e-5, 1.e-3)
    densities = (1.284, 1000.)
    def permeabilities(self):
        # relperms to come
        return [self.absolute_permeability * k_rel \
                for k_rel in self.rel_perms]

    # space and time scales
    finish_time = 1.0

    def Xt_nondim(self):
        """
        Symbols x,..,t, nondimensionalised by domain_extents and
        finish_time.
        """
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
        return self.capillary_pressure_wrt_saturation.subs(
            [('S2', S2), ('Sr2', Sr2)])

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

    # see note [2]
    examined_fields = examined_fields.collapse()

    
class testing(base.testing):
    user_id = 'rferrier'
    test_length = 'short'   # TODO: change to medium?
    reference_timestep_number = 20   # TODO: tighten this up
                

#----------------------------------------------------------------------
# boundary condition types

# straight boundaries can easily support normal flow BCs for MMS tests
class normal_flow_bcs:
    def pressure1_dirichlet_boundary_ids(self):
        return (self.outlet_id,) + self.wall_ids
    saturation2_dirichlet_boundary_ids = ()
    normal_velocity1_dirichlet_boundary_ids = ()
    def normal_velocity2_dirichlet_boundary_ids(self):
        return (self.inlet_id,) + self.wall_ids

    
# curved boundaries are harder to work with, so marry them to
# saturation Dirichlet BCs
class saturation_bcs:
    def pressure1_dirichlet_boundary_ids(self):
        # TODO: figure out why we need pressure over all the
        # boundaries for the curved geometry case
        return (self.inlet_id, self.outlet_id,) + self.wall_ids
    def saturation2_dirichlet_boundary_ids(self):
        return (self.inlet_id,) + self.wall_ids
    normal_velocity1_dirichlet_boundary_ids = ()
    normal_velocity2_dirichlet_boundary_ids = ()
    

#----------------------------------------------------------------------
# relperms

class corey(base.corey):
    residual_saturations = (0.05, 0.1)
    def rel_perms(self):
        S = self.saturations
        Sr = self.residual_saturations
        return ((S[0] - Sr[0])**4,
                (1. - (S[0] - Sr[0])**2) * (1. - (S[0] - Sr[0]))**2)
    
class quadratic(base.quadratic):
    residual_saturations = (0.2, 0.3)
    def rel_perms(self):
        S = self.saturations
        Sr = self.residual_saturations
        n = self.rel_perm_relation_exponents
        return ((S[0]-Sr[0])**n[0],
                (S[1]-Sr[1])**n[1])

rel_perms = OptionsArray('rel_perm', [quadratic, corey])


#----------------------------------------------------------------------
# capillarity

class cap:
    capillary_pressure_wrt_saturation = Symbol('0')

class nocap:
    def capillary_pressure_wrt_saturation(self):
        S2 = Symbol('S2')
        Sr2 = Symbol('Sr2')
        return pressure_scale/10. * ((S2 - Sr2)/(1. - Sr2))**(-0.5)


#----------------------------------------------------------------------
# groups - simulation options can be lumped together; any one failure
# will cause nonconvergence of the whole group

class group1(normal_flow_bcs, quadratic, nocap, base.rpupwind):
    pass

class group2(saturation_bcs, corey, cap, base.modrpupwind_satfe):
    pass

    
#----------------------------------------------------------------------
# tree assembly

# make a root node to store basic options
root = OptionsNode()
root.update(base.admin)
root.update(base.spatial)
root.update(simulation)
root.update(testing)

# Make arrays representing domain dimensions and mesh resolutions.
# These will be used to form both mesh names and simulation names, so
# tag both accordingly.
dims = OptionsArray('dim', [base.onedim, base.twodim, base.threedim],
                    names=['1d', '2d', '3d'], tags=['mesh', 'sim'])
resolutions = OptionsArray('res', [10, 20, 40, 80],
                           tags=['mesh', 'sim'])

def make_subtree(higher_dim_options):
    """
    Makes a fresh tree out of the 'dims' array, with mesh resolution
    decreasing with dimension (for computational economy), and higher
    dimensional options being inserted for 2D and 3D.
    """
    result = OptionsNode()      # initialise a fresh tree
    result *= dims
    result['1d'] *= resolutions[0:4]
    result['2d'] *= higher_dim_options * resolutions[0:3]
    result['3d'] *= higher_dim_options * resolutions[0:2]
    return result


# combine straight boundaries with regular mesh, curved boundaries
# with irregular mesh
boundaries = OptionsArray('boundary', [base.straight, base.curved],
                          tags=['mesh'])
mesh_types = OptionsArray('mesh_type', [base.reg, base.irreg],
                          tags=['mesh'])
higher_dim_options = boundaries + mesh_types


# for the mesh tree, use all of higher_dim_options in a call to
# make_subtree
mesh_options_tree = root * make_subtree(higher_dim_options)
mesh_options_tree.item_hooks = [Remove(missing_dependencies)]

# Marry simulation groups with mesh groups.  For this we need to split
# higher_dim_options into separate subtrees before adding to groups.
# Note that normal_flow_bcs (group1) must be married to straight
# boundaries because we haven't defined analytical normal-velocity
# solutions for curved boundaries.
groups = OptionsArray('group', [group1, group2], tags=['sim'])
subtrees = [make_subtree(hdo) for hdo in higher_dim_options]
groups += subtrees
sim_options_tree = root * groups
sim_options_tree.item_hooks = [Remove(missing_dependencies)]


# # TODO: In 3D, velocity boundary conditions lead to nonconvergence.
# # This is a bug that needs to be fixed.  For now, remove this part of
# # the tree so that tests can pass.
# del general_options_tree['group1']['3d']

# for postprocessing, we additionally want to iterate over some fields
# of interest
test_options_tree = sim_options_tree * examined_fields
test_options_tree.update(base.testing)

# pretty_print(mesh_options_tree)
# pretty_print(sim_options_tree)

#----------------------------------------------------------------------
# dispatch to main routine in darcy_impes_base

if __name__ == '__main__':
    base.main(mesh_options_tree, sim_options_tree, test_options_tree,
              jinja2_filters={'format_sympy': format_sympy})
    

# Notes:
# 
# [1] The pressure scale should be high enough to have an influence
#     (~100).  High levels of saturation and rho*g_mag/mu have been
#     found to cause numerical instability well below the expected CFL
#     limit.  This may be caused by having a highly nonlinear relative
#     permeability term and forcing an unnatural pressure field.
#
# [2] Each simulation needs to compute all of the fields in
#     examined_fields before we iterate over them at the
#     postprocessing stage.  One way of storing this information is to
#     convert examined_fields to a list of dictionaries.
