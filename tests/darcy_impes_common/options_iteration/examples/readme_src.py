import sys
sys.path.append('..')

from __init__ import OptionsNode, OptionsArray, OptionsDict, Lookup, Str, \
    freeze
import multiprocessing

# setup

pipe_dias  = OptionsArray('pipe_diameter', [0.10, 0.15])
velocities = OptionsArray('velocity', [0.01, 0.02, 0.04])
options_tree = pipe_dias * velocities

class water:
    density = 1.00e3
    dynamic_viscosity = 0.89e-3

class ethanol:
    density = 0.79e3
    dynamic_viscosity = 1.09e-3

fluids = OptionsArray('fluid', [water, ethanol])
options_tree *= fluids

print "\nUsing serial loop:\n"

options_dicts = options_tree.collapse()

for opt in options_dicts:
    kinematic_visc = opt.dynamic_viscosity / opt.density
    Re = opt.velocity * opt.pipe_diameter / kinematic_visc
    print '{:20s}: Reynolds number = {:.2e}'.format(opt.str(), Re)

print "\nUsing parallel iterator:\n"

def calculate_Re(opt):
  kinematic_visc = opt.dynamic_viscosity / opt.density
  return opt.velocity * opt.pipe_diameter / kinematic_visc

p = multiprocessing.Pool(4)
Reynolds_numbers = p.map(calculate_Re, options_tree.collapse())

# for completeness...
for descr, Re in zip(map(Str(), options_tree.collapse()), Reynolds_numbers):
    print '{:20s}: Reynolds number = {:.2e}'.format(descr, Re)
    

print "\nUsing dynamic entries:\n"

class fluid:
    def kinematic_viscosity(self):
        return self.dynamic_viscosity / self.density
class water(fluid):
    density = 1.00e3
    dynamic_viscosity = 0.89e-3
class ethanol(fluid):
    density = 0.79e3
    dynamic_viscosity = 1.09e-3

fluids = OptionsArray('fluid', [water, ethanol])
options_tree = pipe_dias * velocities * fluids

options_tree.update({
    'Reynolds_number': lambda opt: opt.velocity * opt.pipe_diameter /
    opt.kinematic_viscosity})

def observation(opt):
    if opt.Reynolds_number < 2100.:
        return 'laminar'
    elif opt.Reynolds_number < 4000.:
        return 'transitional'
    else:
        return 'turbulent'
options_tree.update([observation])

options_dicts = options_tree.collapse()
Reynolds_numbers = p.map(Lookup('Reynolds_number'), freeze(options_dicts))

# for completeness...
observations = p.map(Lookup('observation'), freeze(options_dicts))
for descr, Re, obs in \
    zip(map(Str(), options_tree.collapse()), Reynolds_numbers, observations):
    print '{:20s}: Reynolds number = {:.2e}, {}'.format(descr, Re, obs)
