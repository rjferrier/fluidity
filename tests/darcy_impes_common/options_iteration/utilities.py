"""
Note: the functions and classes in this module are *not* supported
by tests.  Consider them recipes rather than part of the source code.
"""

import os
import multiprocessing
import subprocess
import sys
import numpy
import glob

from options_iteration import OptionsArray, OptionsNode

# TODO: make OptionsNode constructor more intelligent (see TODO.md) so
# we can phase this line out
from options_iteration.options_dict import OptionsDictException

try:
    import jinja2
    HAVE_JINJA2 = True
except:
    HAVE_JINJA2 = False


## TOP LEVEL FUNCTIONS 

def smap(description, functor, options_tree):
    "Serial processing"
    functor.check_processing(False)
    options_dicts = options_tree.collapse()
    functor.setup(options_dicts[0])
    print '\n' + description
    map(functor, options_dicts)
    functor.teardown(options_dicts[-1])
    

def pmap(description, functor, options_tree, nprocs_max=None, in_reverse=False):
    "Parallel processing"
    functor.check_processing(True)
    options_dicts = options_tree.collapse()
    nprocs = get_nprocs(len(options_dicts), nprocs_max)
    for opt in options_dicts:
        opt.freeze()
    if in_reverse:
        options_dicts.reverse()
    functor.setup(options_dicts[0])
    p = multiprocessing.Pool(nprocs)
    print '\n{} with {} processor(s)'.format(description, nprocs)
    p.map(functor, options_dicts)
    p.close()
    functor.teardown(options_dicts[-1])


## HELPERS

def get_nprocs(iterable_length, nprocs_max=None):
    nprocs = os.getenv('NPROC')
    if not nprocs:
        nprocs = multiprocessing.cpu_count()
    if nprocs_max:
        nprocs = min(nprocs, nprocs_max)        
    nprocs = min(nprocs, iterable_length)
    return nprocs

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
            raise Failure(input_filename
    + " not found")

class ChDir:
    "Context manager that temporarily changes working directory"
    def __init__(self, new_path):
        self.new_path = os.path.expanduser(new_path)
    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.new_path)
    def __exit__(self, etype, value, traceback):
        os.chdir(self.saved_path)


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
        
    def boilerplate(self, options, operations, dependencies=[], 
                    target_name=''):
        self.print_start(target_name, options)
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        try:
            for dep in dependencies:
                check_file_exists(dep)
            for op in operations:
                op()
            state = Success(target_name)
        except Failure as state:
            pass
        self.print_end(state, options)
            
        
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


## FUNCTOR HELPERS

class SimpleRendering:
    def __init__(self, nloops=1):
        self.nloops = nloops

    def get_operation(self, options, source_filename, target_filename,
                      source_dir, target_dir):
        "Creates and return a closure that can be executed with no args"

        def operation():
            with open('{}/{}'.format(source_dir, source_filename), 'r') as src:
                buf = src.read()
                buf = options.expand_template_string(buf, self.nloops)
            with open('{}/{}'.format(target_dir, target_filename), 'w') as tgt:
                tgt.write(buf)

        return operation

            
class Jinja2Rendering:
    def __init__(self, configuration={'trim_blocks': True,
                                      'lstrip_blocks': True}):
        if not HAVE_JINJA2:
            raise Exception('jinja2 not installed; needed by this functor')
        self.configuration = configuration

    def get_operation(self, options, source_filename, target_filename, 
                      source_dir, target_dir):
        "Creates and return a closure that can be executed with no args"

        def operation():
            print os.getcwd()
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(source_dir),
                **self.configuration)
            template = env.get_template(source_filename)
            with open('{}/{}'.format(target_dir, target_filename), 'w') as f:
                f.write(template.render(opt=options))

        return operation
    

## FUNCTOR CLASSES FOR PUBLIC USE

class ExpandTemplate(SerialFunctor):
    def __init__(self, source_filename_key, target_filename_key,
                 rendering_strategy=SimpleRendering(),
                 source_dir='.', target_dir='.'):
        self.source_filename_key = source_filename_key
        self.target_filename_key = target_filename_key
        self.rendering_strategy = rendering_strategy
        self.source_dir = source_dir
        self.target_dir = target_dir

    def __call__(self, options):
        source_filename = options[self.source_filename_key]
        target_filename = options[self.target_filename_key]
        operation = self.rendering_strategy.get_operation(
            options, source_filename, target_filename,
            self.source_dir, self.target_dir)

        self.boilerplate(
            options, [operation], [source_filename],
            target_name=target_filename)


class RunBinary(ParallelFunctor):
    def __init__(self, command_line_arguments_key,
                 prerequisite_filenames_key, target_name_key,
                 working_dir='.', error_filename_key=None):
        self.command_line_arguments_key = command_line_arguments_key
        self.prerequisite_filenames_key = prerequisite_filenames_key
        self.target_name_key = target_name_key
        # WARNING: working_dir doesn't seem to be respected.  To be
        # investigated.
        self.working_dir = working_dir
        self.error_filename_key = error_filename_key
    
    def __call__(self, options):
        subp_args = options[self.command_line_arguments_key]
        prerequisite_filenames = options[self.prerequisite_filenames_key]
        target_name = options[self.target_name_key]
        
        if self.error_filename_key:
            error_filename = options[self.error_filename_key]
        else:
            error_filename = target_name + '.err'

        with ChDir(self.working_dir):
            def operation():
                try:
                    with open(error_filename, 'w') as err_file:
                        subprocess.check_output(subp_args, stderr=err_file)
                except subprocess.CalledProcessError as e:
                    raise Failure('FAILURE: see ' + error_filename)
                os.remove(error_filename)
        
            self.boilerplate(
                options, [operation], prerequisite_filenames,
                target_name=target_name)
        

            
## ALTERNATIVE CONSTRUCTORS

class OptionsArrayFactory:
    """
    Provides an OptionsArray constructor with an alternative system
    for naming the nodes.  For example, where

       OptionsArray('array1', [class1, class2])
       OptionsArray('array2', range(3))

    produces nodes named ['class1', 'class2'] and ['0', '1', '2'],

       factory = OptionsArrayFactory()
       factory('array1', [class1, class2])
       factory('array2', range(3))

    produces nodes named ['A00', 'A01'] and ['B00', 'B01', 'B02'].
    """
    def __init__(self, array_index_formatter=None, node_index_formatter=None):
        self.array_index = 0
        if not array_index_formatter:
            self.array_index_formatter = self.default_array_index_formatter
        if not node_index_formatter:
            self.node_index_formatter = self.default_node_index_formatter

    @staticmethod
    def default_array_index_formatter(i):
        "Converts 0, 1, 2,... to A, B, C,... "
        return 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i]

    @staticmethod
    def default_node_index_formatter(i):
        "Converts 0, 1, 2,... to 00, 01, 02,... "
        return '{:02d}'.format(i)
        
    def __call__(self, array_name, elements):
        nodes = []
        for node_index, el in enumerate(elements):
            node_name = self.array_index_formatter(self.array_index) +\
                        self.node_index_formatter(node_index)
            try:
                # el is a class that represents some entries
                new_node = OptionsNode(node_name, el)
            except OptionsDictException:
                # el is a value that will be stored under array_name
                new_node = OptionsNode(node_name, {array_name: el})
            nodes.append(new_node)

        # bump the array counter for next time
        self.array_index += 1
        return OptionsArray(array_name, nodes)
