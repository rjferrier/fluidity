import os
import multiprocessing
import subprocess
import sys
import numpy
import glob

from options_iteration import freeze
from fluidity_tools import stat_parser

        
## PUBLIC FUNCTIONS

def smap(description, functor, options_tree):
    "Serial processing"
    functor.check_processing(False)
    options_dicts = options_tree.collapse()
    functor.setup(options_dicts[0])
    print '\n' + description
    map(functor, options_dicts)
    functor.teardown(options_dicts[-1])

    
def pmap(description, functor, options_tree, default_nprocs=1, in_reverse=True):
    "Parallel processing"
    nprocs = os.getenv('NPROC')
    if not nprocs:
        nprocs = default_nprocs
    functor.check_processing(True)
    options_dicts = options_tree.collapse()
    functor.setup(options_dicts[0])
    p = multiprocessing.Pool(nprocs)
    if in_reverse:
        options_dicts.reverse()
    print '\n{} with {} processor(s)'.format(description, nprocs)
    p.map(functor, freeze(options_dicts))
    p.close()
    functor.teardown(options_dicts[-1])

    
def find_in_report(report_filename, result_id, metric_name):
    """
    Opens and searches report_filename and returns the value associated
    with result_id and metric_name.
    """
    with open(report_filename, "r") as report:
        report.seek(0)
        v = numpy.nan
        # loop over lines
        for line in report:
            if not line.strip(): continue
            words = line.split()
            # loop over words in the line
            for i, w in enumerate(words):
                if i == 0 and w != result_id:
                    # not the right result name, so return to looping
                    # over the lines
                    break
                if metric_name in w:
                    # found metric_name
                    break
            if i > 0 and i < len(words) - 1:
                # if we found the right metric name, assume the metric
                # value is represented by the very next word
                v = float(words[i+1])
                break
    return v


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

    
def check_file_exists(input_filename):
    if input_filename:
        if not os.path.isfile(input_filename):
            raise Failure(input_filename + " not found")


            
## FUNCTOR STRATEGIES

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


## FUNCTOR BASE CLASSES

class Functor:
    """
    Do not subclass me; subclass SerialFunctor or ParallelFunctor
    instead.
    """
    def setup(self, options):
        "Code to be executed before iteration"
        pass
    
    def teardown(self, options):
        "Code to be executed after iteration"
        pass
        
    def subprocess(self, subprocess_args, error_filename):
        try:
            with open(error_filename, 'w') as err_file:
                subprocess.check_output(subprocess_args, stderr=err_file)
        except subprocess.CalledProcessError as e:
            raise Failure('FAILURE: see ' + error_filename)
        os.remove(error_filename)

    def template_call(self, options, operation, input_filename='', 
                      target_name=''):
        self.print_start(target_name, options)
        try:
            check_file_exists(input_filename)
            operation()
            state = Success(target_name)
        except Failure as state:
            pass
        self.print_end(state, options)

    def check_file_exists(self, input_filename):
        if input_filename:
            if not os.path.isfile(input_filename):
                raise FileNotFound(input_filename)
            
        
class SerialFunctor(Functor):
    "Subclass me."
    @staticmethod
    def check_processing(in_parallel):
        class ProcessingError(Exception):
            def __str__(self):
                return 'this functor is designed to be run in serial only.'
        if in_parallel:
            raise ProcessingError()

    def print_start(self, state, options=None, target=sys.stdout):
        pass

    def print_end(self, state, options=None, target=sys.stdout):
        msg = str(state)
        if options:
            if msg and '\n' not in msg:
                if state.successful:
                    sep = ' -> '
                else:
                    sep = ' -- '
            else:
                sep = ''
                msg = msg.replace('\n', '\n' + options.indent())
            branch = options.str(formatter='tree')
            target.write(branch + sep + msg + '\n')
        else:
            if msg:
                target.write(msg + '\n')
        
            
class ParallelFunctor(Functor):
    "Subclass me."
    @staticmethod
    def check_processing(in_parallel):
        # designed to be run either in serial or parallel
        pass

    def print_start(self, state, options=None, target=sys.stdout):
        msg = str(state)
        if msg:
            target.write(" "*4 + msg + ' ...\n')

    def print_end(self, state, options=None, target=sys.stdout):
        msg = str(state)
        if state.successful:
            intro = 'finished '
        else:
            intro = ''
        if msg:
            target.write(" "*8 + intro + msg + '\n')

        
## FUNCTOR CONCRETE CLASSES

class ExpandTemplate(SerialFunctor):
    def __init__(self, template_key, target_key,
                 template_dir='.', target_dir='.'):
        self.template_key = template_key
        self.target_key = target_key
        self.template_dir = template_dir
        self.target_dir = target_dir

    def __call__(self, options):
        template_filename = '{}/{}'.format(self.template_dir,
                                           options[self.template_key])
        target_filename = '{}/{}'.format(self.target_dir,
                                         options[self.target_key])
        self.template_call(
            options, lambda: options.expand_template_file(
                template_filename, target_filename, loops=3),
            template_filename, target_name=target_filename)


class Mesh(ParallelFunctor):
    def __init__(self, working_dir='.'):
        self.working_dir = working_dir

    def __call__(self, options):
        mesh_name = options['mesh_name']
        geo_filename = '{}/{}'.format(self.working_dir, options['geo_filename'])
        mesh_filename = '{}/{}'.format(self.working_dir, options['mesh_filename'])
        error_filename = '{}/{}.err'.format(self.working_dir, mesh_name)
        
        subp_args = ['gmsh', '-{}'.format(options['dim_number']), geo_filename,
                     '-o', mesh_filename]

        self.template_call(
            options, lambda: self.subprocess(subp_args, error_filename),
            geo_filename, target_name=mesh_name)
        
    
class Simulate(ParallelFunctor):
    def __init__(self, binary_path, verbosity=0, working_dir='.'):
        self.binary_path = binary_path
        self.verbosity = verbosity
        self.working_dir = working_dir
    
    def __call__(self, options):
        sim_name = options['simulation_name']
        sim_stem = '{}/{}'.format(self.working_dir, sim_name)
        input_filename = '{}/{}'.format(
            self.working_dir, options['simulation_options_filename'])
        error_filename = sim_stem + '.err'
        
        subp_args = [self.binary_path]
        if self.verbosity > 0:
            subp_args += ['-v{}'.format(self.verbosity),
                          '-l {}/{}.log'.format(self.working_dir, sim_stem)]
        subp_args.append(input_filename)

        self.template_call(
            options, lambda: self.subprocess(subp_args, error_filename),
            input_filename, target_name=sim_name)


class Postprocess(SerialFunctor):
    error_format = '{:.3e}'
    rate_format = '{:.6f}'

    def __init__(self, error_getter_class=GetErrorFromField,
                 naming_keys=[], excluded_naming_keys=[],
                 results_dir='.', report_dir='.'):
        self.error_getter = error_getter_class(results_dir)
        self.naming_keys = naming_keys
        self.excluded_naming_keys = excluded_naming_keys
        self.results_dir = results_dir
        self.report_dir = report_dir

    def setup(self, options):
        try:
            self.report_file = open('{}/{}'.format(
                self.report_dir, options['report_filename']), 'w')
        except IndexError:
            self.report_file = None
        self.resolutions = {}
        self.errors = {}
        self.rates = {}

    def teardown(self, options):
        if self.report_file:
            self.report_file.close()
        
    def __call__(self, options):
        current_id = options.str(only=self.naming_keys,
                                 exclude=self.excluded_naming_keys)
        
        # n.b. need to convert from integer to float
        current_res = float(options['mesh_res'])
        try:
            current_err = self.error_getter(options)
        except Failure as state:
            return self.print_end(state, options)
        
        # register current values
        self.resolutions[current_id] = current_res
        self.errors[current_id] = current_err
        msg = ' error: ' + self.error_format.format(current_err)
        
        # now try loading the values corresponding to the previous
        # mesh resolution and calculate the convergence rate
        try:
            previous_id = options.str(
                only=self.naming_keys,
                exclude=self.excluded_naming_keys,
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
            self.report_file.write('{}  {}\n'.format(current_id, msg))
            
        self.print_end(Success(msg), options)


class WriteXml(SerialFunctor):
    def __init__(self, naming_keys=[], excluded_naming_keys=[],
                 template_dir='.'):
        self.naming_keys = naming_keys
        self.excluded_naming_keys = excluded_naming_keys
        self.template_dir = template_dir
        
    def setup(self, options):
        self.tests = []

    def teardown(self, options):
        # Import the Jinja 2 package here so that systems that don't
        # have it can still use the other functors.
        import jinja2
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('.'))
        template = env.get_template('{}/{}'.format(
            self.template_dir, options['xml_template_filename']))
        
        with open(options['xml_target_filename'], 'w') as f:
            f.write(template.render(
                problem=options, tests=self.tests))
            
    def __call__(self, options):
        test_info = [['error', 'lt', options['max_error_norm']],
                     ['rate',  'gt', options['min_convergence_rate']]]
        msg = ''
        for ti in test_info:
            # do not write a test if a threshold is not given
            if not ti[2]:
                continue
            # do not write a rate test if this is the first mesh in
            # the series
            if ti[0] == 'rate' and options.get_node_info('mesh_res').is_first():
                continue
            self.tests.append({
                'key': options.str(only=self.naming_keys,
                                   exclude=self.excluded_naming_keys),
                'metric_type': ti[0],
                'rel_op'     : ti[1],
                'threshold'  : ti[2] })
            msg += '\nwrote test: {} &{}; {}'.format(*ti)
        self.print_end(Success(msg), options)


