import os
import multiprocessing
import subprocess
import numpy
import glob

from options_iteration import freeze

        
## DRIVERS

def smap(description, functor, options_tree):
    "Serial processing"
    functor.check_processing(False)
    functor.setup()
    print '\n' + description
    map(functor, options_tree.collapse())
    functor.teardown()

    
def pmap(description, functor, options_tree, default_nproc=1, in_reverse=True):
    "Parallel processing"
    nproc = os.getenv('NPROC')
    if not nproc:
        nproc = default_nproc
    functor.check_processing(True)
    functor.setup()
    p = multiprocessing.Pool(nproc)
    options_dicts = options_tree.collapse()
    if in_reverse:
        options_dicts.reverse()
    print '\n{} with {} processor(s)'.format(description, nproc)
    p.map(functor, freeze(options_dicts))
    p.close()
    functor.teardown()


## HELPERS

class State:
    def __init__(self, msg=''):
        self.msg = msg
    def __str__(self):
        return self.msg

class Success(State):
    successful = True
        
class Failure(State, Exception):
    successful = False

class FileNotFound(Failure):
    def __init__(self, input_filename):
        self.msg = input_filename + " not found"


## FUNCTOR BASE CLASSES

class Functor:
    def setup(self):
        "Code to be executed before iteration"
        pass
    
    def teardown(self):
        "Code to be executed after iteration"
        pass
        
    def subprocess(self, subprocess_args, target_name):
        try:
            subprocess.check_output(subprocess_args, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            err_filename = target_name + '.err'
            with open(err_filename, 'w') as err_file:
                err_file.write(str(e))
            raise Failure('FAILURE: see ' + err_filename)

    def template_call(self, options, operation, input_filename='', 
                      target_name='', naming_keys=None):
        self.print_start(target_name, options, naming_keys)
        try:
            self.check_file_exists(input_filename)
            operation()
            state = Success(target_name)
        except Failure as state:
            pass
        self.print_end(state, options, naming_keys)

    def check_file_exists(self, input_filename):
        if input_filename:
            if not os.path.isfile(input_filename):
                raise FileNotFound(input_filename)

            
        
class SerialFunctor(Functor):
    @staticmethod
    def check_processing(in_parallel):
        class ProcessingError(Exception):
            def __str__(self):
                return 'this functor is designed to be run in serial only.'
        if in_parallel:
            raise ProcessingError()

    @staticmethod
    def print_start(state, options=None, naming_keys=None):
        pass

    @staticmethod
    def print_end(state, options=None, naming_keys=None):
        msg = str(state)
        if options:
            if msg and '\n' not in msg:
                if state.successful:
                    sep = ' -> '
                else:
                    sep = ' -- '
            else:
                sep = ''
            print options.str(naming_keys, formatter='tree') + sep + msg
        else:
            if msg:
                print msg
        
            
class ParallelFunctor(Functor):
    @staticmethod
    def check_processing(in_parallel):
        # designed to be run either in serial or parallel
        pass

    @staticmethod
    def print_start(state, options=None, naming_keys=None):
        msg = str(state)
        if msg:
            print " "*4 + msg + ' ...'

    @staticmethod
    def print_end(state, options=None, naming_keys=None):
        msg = str(state)
        if state.successful:
            intro = 'finished '
        else:
            intro = ''
        if msg:
            print " "*8 + intro + msg
        
        
## FUNCTOR CONCRETE CLASSES

class ExpandTemplate(SerialFunctor):
    def __init__(self, template_key, results_key,
                 template_filename_format='./{}',
                 results_filename_format='./{}', 
                 naming_keys=None):
        self.template_key = template_key
        self.results_key = results_key
        self.template_filename_format = template_filename_format
        self.results_filename_format = results_filename_format
        self.naming_keys = naming_keys

    def __call__(self, options):
        template_filename = self.template_filename_format.\
                            format(options[self.template_key])
        results_filename = self.results_filename_format.\
                           format(options[self.results_key])

        self.template_call(
            options, lambda: options.expand_template_file(
                template_filename, results_filename, loops=2),
            template_filename, target_name=options[self.results_key],
            naming_keys=self.naming_keys)

    def get_output_filenames(self, options):
        return [self.results_filename_format.format(
            options[self.results_key])]
        


class Mesh(ParallelFunctor):
    def __init__(self, results_dir='.'):
        self.results_dir = results_dir + '/'
    
    def __call__(self, options):
        geo_filename = self.results_dir + options['geo_filename']
        mesh_filename = self.results_dir + options['mesh_filename']
        subp_args = ['gmsh', '-{}'.format(options['dim_number']), geo_filename,
                     '-o', mesh_filename]
        
        self.template_call(
            options, lambda: self.subprocess(subp_args, geo_filename),
            geo_filename, target_name=options['mesh_name'])

    def get_output_filenames(self, options):
        return [self.results_dir + options['mesh_filename']]
        
    
    

class Simulate(ParallelFunctor):
    def __init__(self, binary_path, results_dir='.', verbosity=0):
        self.binary_path = binary_path
        self.results_dir = results_dir + '/'
        self.verbosity = verbosity
    
    def __call__(self, options):
        input_filename = self.results_dir + \
                         options['simulation_options_filename']
        sim_name = options['simulation_name']
        subp_args = [self.binary_path]
        if self.verbosity > 0:
            subp_args += ['-v{0}'.format(self.verbosity),
                          '-l {0}.log'.format(sim_name)]
        subp_args.append(input_filename)

        self.template_call(
            options, lambda: self.subprocess(subp_args, sim_name),
            input_filename, target_name=sim_name)

    def get_output_filenames(self, options):
        stem = self.results_dir + options['simulation_name']
        return [stem + ext for ext in ['_*.vtu', '.stat', '.err']]


class Postprocess(SerialFunctor):
    error_format = '{:.3e}'
    rate_format = '{:.6f}'
    
    def __init__(self, error_calculator, report_filename=None,
                 naming_keys=None):
        self.error_calculator = error_calculator.with_host(self)
        self.naming_keys = naming_keys
        self.report_filename = report_filename
        self.resolutions = {}
        self.errors = {}
        self.rates = {}

    def setup(self):
        if self.report_filename:
            self.report_file = open(self.report_filename, 'w')
        else:
            self.report_file = None

    def teardown(self):
        if self.report_filename:
            self.report_file.close()
        
    def __call__(self, options):
        current_id = options.str(self.naming_keys)
        # n.b. need to convert from integer to float
        current_res = float(options['mesh_res'])
        try:
            current_err = self.error_calculator(options)
        except Failure as state:
            return self.print_end(state, options, self.naming_keys)
        
        # register current values
        self.resolutions[current_id] = current_res
        self.errors[current_id] = current_err
        msg = ' error: ' + self.error_format.format(current_err)
        
        # now try loading the values corresponding to the previous
        # mesh resolution and calculate the convergence rate
        try:
            previous_id = options.str(self.naming_keys,
                                      relative={'mesh_res': -1})
            previous_res = self.resolutions[previous_id]
            previous_err = self.errors[previous_id]
            # calculate convergence rate
            self.rates[current_id] = numpy.log(current_err/previous_err) / \
                                     numpy.log(previous_res/current_res)
            msg += '   rate: ' + \
                   self.rate_format.format(self.rates[current_id])
        except:
            # not enough info
            self.rates[current_id] = numpy.nan

        if self.report_file:
            self.report_file.write(
                '{}  {}\n'.format(options.str(self.naming_keys), msg))
            
        self.print_end(Success(msg), options, self.naming_keys)


class Clean(SerialFunctor):
    def __init__(self, functors, naming_keys=None):
        self.functors = functors
        self.naming_keys = naming_keys
        
    def __call__(self, options):
        msg_list = []
        for func in self.functors:
            filename_patterns = func.get_output_filenames(options)
            trash = []
            for fp in filename_patterns:
                trash += glob.glob(fp)
            try:
                for filename in trash:
                    os.remove(filename)
                    msg_list.append(options.indent() + 'removed ' + filename)
            except OSError:
                pass
        msg = '\n' + '\n'.join(msg_list) if msg_list else ""
        self.print_end(Success(msg), options, self.naming_keys)
