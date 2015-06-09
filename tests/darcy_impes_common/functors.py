import sys
import os
import subprocess
import multiprocessing
import re

from options_iteration import freeze

        
## DRIVERS

def smap(description, functor, options_tree):
    "Serial processing"
    functor.check_processing(False)
    print '\n' + description
    map(functor, options_tree.collapse())

    
def pmap(description, functor, options_tree, default_nproc=1, in_reverse=True):
    "Parallel processing"
    nproc = os.getenv('NPROC')
    if not nproc:
        nproc = default_nproc
    functor.check_processing(True)
    print '\n{} with {} processor(s)'.format(description, nproc)
    p = multiprocessing.Pool(nproc)
    options_dicts = options_tree.collapse()
    if in_reverse:
        options_dicts.reverse()
    p.map(functor, freeze(options_dicts))
    p.close()


## FUNCTOR BASE CLASSES

class Functor:
    def check_file_exists(self, input_filename, target_name=''):
        file_exists = os.path.isfile(input_filename)
        msg = self._get_token(file_exists)
        if file_exists and target_name:
            msg += target_name
        elif not file_exists:
            msg += input_filename + " not found"
        else:
            msg = ""
        return file_exists, msg

    def template_call(self, options, input_filename, kernel_function,
                      target_name='', naming_keys=None):
        self.report_start(target_name, options, naming_keys)
        file_exists, msg = self.check_file_exists(input_filename, target_name)
        if file_exists:
            kernel_function()
        self.report_end(msg, options, naming_keys)

        
class SerialFunctor(Functor):
    @staticmethod
    def check_processing(in_parallel):
        class ProcessingError(Exception):
            def __str__(self):
                return 'this functor is designed to be run in serial only.'
        if in_parallel:
            raise ProcessingError()

    @staticmethod
    def report_start(message, options=None, naming_keys=None):
        pass

    @staticmethod
    def report_end(message, options=None, naming_keys=None):
        if options:
            print options.str(naming_keys, formatter='tree'), message
        else:
            if message:
                print message

    @staticmethod
    def _get_token(successful):
        if successful:
            return '-> '
        else:
            return '-- '
        
            
class ParallelFunctor(Functor):
    @staticmethod
    def check_processing(in_parallel):
        # designed to be run either in serial or parallel
        pass

    @staticmethod
    def report_start(message, options=None, naming_keys=None):
        if message:
            print " "*4 + message + ' ...'

    @staticmethod
    def report_end(message, options=None, naming_keys=None):
        if message:
            print " "*8 + message

    @staticmethod
    def _get_token(successful):
        if successful:
            return 'finished '
        else:
            return ''
        
        
## FUNCTOR CONCRETE CLASSES

class ExpandTemplate(SerialFunctor):
    def __init__(self, template_key, results_key,
                 template_filename_format='{}', results_filename_format='{}', 
                 naming_keys=None):
        self.template_key = template_key
        self.results_key = results_key
        self.template_filename_format = template_filename_format
        self.results_filename_format = results_filename_format
        self.naming_keys = naming_keys
    
    def __call__(self, options):
        template_file = self.template_filename_format.\
                        format(options[self.template_key])
        results_file = self.results_filename_format.\
                       format(options[self.results_key])

        self.template_call(
            options, template_file, 
            lambda: options.expand_template_file(
                template_file, results_file, loops=2),
            target_name=options[self.results_key],
            naming_keys=self.naming_keys)


class Mesh(ParallelFunctor):
    def __init__(self, results_dir='.'):
        self.results_dir = results_dir + '/'
    
    def __call__(self, options):
        geo_file = self.results_dir + options['geo_filename']
        mesh_file = self.results_dir + options['mesh_filename']
        
        self.template_call(
            options, geo_file, 
            lambda: subprocess.call(
                ['gmsh', '-{}'.format(options['dim_number']), geo_file, '-o',
                 mesh_file],
                stdout=open(os.devnull, 'wb')),
            target_name=options['mesh_name']),


class Simulate(ParallelFunctor):
    def __init__(self, binary_path, results_dir='.', verbosity=0):
        self.binary_path = binary_path
        self.results_dir = results_dir + '/'
        self.verbosity = verbosity
        
    
    def __call__(self, options):
        sim_file = self.results_dir + options['simulation_options_filename']
        sim_name = options['simulation_name']

        subp_args = [self.binary_path]
        if self.verbosity > 0:
            subp_args += ['-v{0}'.format(self.verbosity),
                          '-l {0}.log'.format(sim_name)]
        subp_args.append(sim_file)

        self.template_call(
            options, sim_file, 
            lambda: subprocess.call(subp_args,
                                    stdout=open(os.devnull, 'wb')),
            target_name=sim_name)


class Postprocess(SerialFunctor):
    error_format = '{:.3e}'
    rate_format = '{:.6f}'
    
    def __init__(self, error_calculator, naming_keys=None):
        self.error_calculator = error_calculator
        self.naming_keys = naming_keys
        self.resolutions = {}
        self.errors = {}
        self.rates = {}
        
    def __call__(self, options):
        current_sim = options.str(self.naming_keys)
        # get current mesh resolution and associated error
        current_res = options['mesh_res']
        current_err = self.error_calculator(options)
        
        # register current values
        self.resolutions[current_sim] = current_res
        self.errors[current_sim] = current_err
        msg = '-- error:' + self.error_format(current_err)
        
        # now try loading the values corresponding to the previous
        # mesh resolution and calculate the convergence rate
        try:
            previous_sim = options.str(self.naming_keys,
                                       relative={'mesh_res': -1})
            previous_res = self.resolutions[previous_sim]
            previous_err = self.errors[previous_sim]
            # calculate convergence rate
            rates[current] = numpy.log(current_err/previous_err) / \
                             numpy.log(previous_res/current_res)
            msg += ' -- rate: ' + self.rate_format(rates[current])
            
        except IndexError:
            # not enough info
            rates[current] = numpy.nan

        self.report_end(msg)
