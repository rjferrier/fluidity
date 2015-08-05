from copy import deepcopy
from types import FunctionType
from string import Template
from warnings import warn

from base import OptionsBaseException
from node_info import OrphanNodeInfo, ArrayNodeInfo, SimpleFormatter, \
    TreeFormatter, NodeInfoException



class OptionsDictException(OptionsBaseException):
    pass

        
class OptionsDict(dict):
    """
    An OptionsDict inherits from a conventional dict, but it has a few
    enhancements:
    
    (1) In a similar way to Django and Jinja2, entries can be set and
        accessed using attribute setter/getter (dot) syntax.  
        For example, as an alternative to
            opt['foo'] = 'bar'
            print opt['foo']
        we may write
            opt.foo = 'bar'
            print opt.foo

        To prevent clashes with the existing attribute namespace,
        - Any name registered in the mutable_attributes class variable
          escapes item setting so that the associated attribute can be
          manipulated as usual.
        - Setting an item with a name registered in protected_attributes,
          or with a leading underscore, is disallowed.

        As an added convenience, the OptionsDict can be constructed or
        updated from a class whose attributes represent the new
        entries.  Any class methods will go on to become dynamic
        entries (see next note).
            class basis:
                foo = 'bar'
                def baz(self):
                    return self.foo
            opt.update(basis)
        
    (2) Values can be runtime-dependent upon the state of other values
        in the dictionary.  Each of these special values is specified
        by a function accepting a single dictionary argument (i.e. the
        OptionsDict itself).  The argument is used to look things up
        dynamically.  An OptionsDict can be constructed or updated
        with a list of functions instead of the usual key-value pairs,
        in which case the functions' names become the keys.

        N.B.  If dynamic entries are created using more exotic
        constructs such lambdas or closures, it will be necessary to
        call OptionsDict.freeze() before using the multiprocessing
        module, because it seems that such constructs cause pickling
        problems.  freeze() gets around the problems by converting the
        dynamic entries back to static ones.

    (3) An OptionsDict can be given 'node information' which lends the
        OptionsDict a name and describes its position in a tree.  This
        node information accumulates when OptionsDicts are merged via
        the update() method, and can be used to form a string
        identifier for the ensemble.  For example, updating node 'A'
        with node 'B' will produce node 'A_B'.  The identifier can be
        accessed via the usual str() idiom, but a str() method is also
        provided with optional arguments for customising the
        identifier and inferring the identifiers of other
        combinations.

    (4) An OptionsDict can expand strings as simple templates.  (For
        more complex templates, it is recommended that the OptionsDict
        be passed to a template engine such as Jinja2.)
    """

    # mutable attributes should be prefixed with underscores so that
    # the client does not confuse them with dictionary items.
    mutable_attributes = ['_node_info']
    protected_attributes = [
        'another', 'donate_copy', 'indent', 'create_array_node_info',
        'create_node_info_formatter', 'create_orphan_node_info',
        'copy', 'expand_template_file', 'get_node_info', 'freeze',
        'from_class', 'set_node_info', 'str', 'update']
    
    def __init__(self, entries={}):
        """
        Returns an OptionsDict with no node information.  The entries
        argument can be more than just key-value pairs; see the update
        method for more information.
        """
        # With just an entries argument, treat as a simple dict.  Set
        # the node_info list first.  This is necessary to prevent
        # dynamic entries from possibly referencing the component
        # before it exists.
        self._node_info = []
        self.update(entries)

    @classmethod
    def another(Class, entries={}):
        return Class(entries)

    @classmethod
    def from_class(Class, basis):
        # ignore magic/hidden attributes, which are prefixed with a
        # double underscore
        entries  = {k: basis.__dict__[k] \
                    for k in basis.__dict__.keys() if '__' not in k}
        return Class(entries)

    @classmethod
    def node(Class, name, entries={}):
        """
        Returns an OptionsDict as an orphan node, i.e. having a name
        for identification purposes but not belonging to a collection.
        """

        warn("\nThis is a deprecated method.  Consider using "+\
             "tree_elements.OptionsNode \ninstead.")
        
        # check name argument
        if not name:
            name = ''
        elif not isinstance(name, str):
            raise OptionsDictException(
                "name argument must be a string (or None).")
        # instantiate object and set the first node information
        obj = Class(entries)
        obj._node_info.append(obj.create_orphan_node_info(name))
        return obj

        
    @classmethod
    def array(Class, array_name, elements, common_entries={},
              name_format='{}'):
        """
        Returns a list of OptionsDicts, wrapping the given elements as
        necessary.

        If a given element is not already an OptionsDict node, it is
        converted to a string which becomes the name of a new
        OptionsDict.  The new OptionsDict acquires the entry
        {array_name: element}.  This feature is useful for setting up
        an independent variable with an associated array of values.
        For example,
           OptionsDict.array('velocity', [0.01, 0.02, 0.04])
        would be equivalent to
          [OptionsDict.node('0.01', {'velocity': 0.01}),
           OptionsDict.node('0.02', {'velocity': 0.02}),
           OptionsDict.node('0.04', {'velocity': 0.04})]
        except that the NodeInfo components are different.

        If an element is already an OptionsDict node, it simply
        acquires the entry {array_name: str(element)}.
        
        All dicts are initialised with common_entries if this argument
        is given.  The element-to-string conversion is governed by
        name_format, which can either be a format string or a callable
        that takes the element value and returns a string.
        """

        warn("\nThis is a deprecated method.  Consider using "+\
             "tree_elements.OptionsArray\n instead.")

        options_dicts = []
        node_names = []
        
        # First pass: instantiate OptionsDict elements
        for index, el in enumerate(elements):
            if isinstance(el, OptionsDict):
                # If the element is already an OptionsDict object,
                # copy it and add a special entry using array_name.
                # Keep track of the node name.
                od = el.copy()
                node_name = str(el)
                od.update({array_name: node_name})
            else:
                # otherwise, instantiate a new OptionsDict node with
                # the original element stored under array_name.
                # Determine the node name.
                try:
                    node_name = name_format(el)
                except TypeError:
                    try:
                        node_name = name_format.format(el)
                    except AttributeError:
                        raise OptionsDictException(
                            "name_format must be a callable "+\
                            "or a format string.")
                od = Class.node(node_name, {array_name: el})

            # add entries
            od.update(common_entries)
            # append to the lists
            options_dicts.append(od)
            node_names.append(node_name)

        # Second pass: set array node information.  This will replace
        # the preexisting orphan node information.
        for index, od in enumerate(options_dicts):
            od.set_node_info(
                od.create_array_node_info(array_name, node_names, index))
        
        return options_dicts


    def copy(self):
        obj = self.another(dict.copy(self))
        obj._node_info = [ni.copy() for ni in self._node_info]
        return obj

        
    def create_orphan_node_info(self, node_name):
        """
        Overrideable factory method, used by OptionsDict.node().
        """
        return OrphanNodeInfo(node_name)

        
    def create_array_node_info(self, array_name, node_names, node_index):
        """
        Overrideable factory method, used by OptionsDict.array().
        """
        return ArrayNodeInfo(array_name, node_names, node_index)

    
    def update(self, entries):
        """
        As with conventional dicts, updates entries with the key-value
        pairs given in the entries argument.  Alternatively, a list of
        functions may be supplied which will go on to become dynamic
        entries, or a class may be supplied whose attributes and
        methods will go on to become conventional and dynamic entries,
        respectively.
        """
        default_err = OptionsDictException(
            "argument must be a dict, an iterable of dynamic entries \n"+\
            "(i.e. functions), or a class with attributes and/or methods.")
        for strategy in [self._update_from_dict,
                         self._update_from_dynamic_entries,
                         self._update_from_class]:
            try:
                strategy(entries, default_err)
                return
            except (AttributeError, TypeError):
                # tolerate certain exceptions by moving onto the next
                # update strategy
                pass

        # if we've looped through all the strategies and come to the end, 
        # the argument was incompatible
        raise default_err

    def freeze(self):
        """
        Converts all dynamic entries to static ones.  This may be
        necessary before multiprocessing, because Python's native
        pickle module has trouble serialising any lambdas (anonymous
        functions) residing in the dict.
        """
        for k in self.keys():
            self[k] = self[k]
        # return self so as to be inlineable
        return self

            
    def str(self, only=[], exclude=[], absolute={}, relative={}, 
            formatter=None, only_indent=False):
        """
        Returns a string identifier, providing more control than the
        str() idiom through optional arguments.

        Specifically, if the OptionsDict was part of a collection
        and/or has been updated from other such OptionsDicts, it is
        possible to control which substrings appear through the 'only'
        and 'exclude' arguments.  These arguments take a collection
        name or list of collection names.

        If the OptionsDict was part of a tree, the 'absolute' and
        'relative' arguments can be used to infer the name of an
        OptionsDict corresponding to a different node in the tree.
        These arguments take the form of key-value pairs with
        collection names as the keys and indices as the values.  In
        accordance with Python indexing rules, a negative absolute
        index returns a node from the end of the array.  To prevent
        confusion, however, this shall not apply when a relative index
        is given.
        
        If the formatter argument is a string or omitted, the
        OptionsDict constructs and applies a formatter object (see
        OptionsDict.create_node_info_formatter).  Alternatively, the
        client may construct and pass a formatter object directly.
        """
        # wrap 'only' and 'exclude' strings as lists if necessary
        if isinstance(only, str):
            only = [only]
        if isinstance(exclude, str):
            exclude = [exclude]

        # filter the nodes to represent
        filtered_node_info = []
        for ni in self._node_info:
            # filter nodes according to corresponding collection names
            # given in the optional args
            if only:
                if not ni.belongs_to_any(only):
                    continue
            if ni.belongs_to_any(exclude):
                continue
            # if we are still in the loop at this point, we can include
            # the current node info in the result.
            filtered_node_info.append(ni)

        # create a formatter object if necessary
        if isinstance(formatter, str) or not formatter:
            formatter = self.create_node_info_formatter(formatter)
        # pass the filtered list to the formatter object
        return formatter(filtered_node_info, 
                         absolute=absolute, relative=relative,
                         only_indent=only_indent)

        
    def create_node_info_formatter(self, which=None):
        """
        Overrideable factory method, used by OptionsDict.str().  The
        argument may be 'simple', 'tree', or omitted (defaulting to
        'simple').
        """
        if not which:
            which = 'simple'
        if which == 'simple':
            return SimpleFormatter()
        elif which == 'tree':
            return TreeFormatter()
        else:
            raise OptionsDictException("'{}' not recognised.".format(which))

            
    def indent(self, only=[], exclude=[], absolute={}, relative={}, 
            formatter='tree'):
        return self.str(only=only, exclude=exclude, absolute=absolute,
                        relative=relative, formatter=formatter,
                        only_indent=True)
            
        
    def get_node_info(self, collection_name=None):
        """
        Returns the OptionDict's first NodeInfo object.  If the
        OptionsDict has accumulated several NodeInfo objects, the
        client can get a particular one by passing in the
        corresponding collection name.
        """
        if collection_name is None:
            try:
                return self._node_info[0]
            except IndexError:
                raise NodeInfoException(
                    "there aren't any node_info objects")
        else:
            for ni in self._node_info:
                if ni.belongs_to(collection_name):
                    return ni
            raise NodeInfoException(
                "couldn't find any node information corresponding to '{}'".\
                format(collection_name))
        
    def set_node_info(self, new_node_info, collection_name=None):
        """
        Sets the OptionDict's first NodeInfo object.  If the
        OptionsDict has accumulated several NodeInfo objects, the
        client can set a particular one by passing in the
        corresponding collection name.
        """
        if collection_name is None:
            try:
                self._node_info[0] = new_node_info
            except IndexError:
                self._node_info.append(new_node_info)
        else:
            for i, ni in enumerate(self._node_info):
                if ni.belongs_to(collection_name):
                    self._node_info[i] = new_node_info
                    return
            raise NodeInfoException(
                "couldn't find any node information corresponding to '{}'".\
                format(collection_name))
        
    def expand_template_string(self, buffer_string, loops=1):
        """
        In buffer_string, replaces substrings prefixed '$' with
        corresponding values in the OptionsDict.  More than one loop
        will be needed if the placeholders are nested.
        """
        for i in range(loops):
            buffer_string = Template(buffer_string)
            buffer_string = buffer_string.safe_substitute(self)
        return buffer_string
        
        
    def expand_template_file(self, source_filename, target_filename, 
                             loops=1):
        """
        As expand_template_string, but does the reading and writing of
        files for you.
        """
        with open(source_filename, 'r') as src:
            buf = src.read()
            buf = self.expand_template_string(buf, loops)
        with open(target_filename, 'w') as tgt:
            tgt.write(buf)


    def donate_copy(self, acceptor):
        # polymorphic; used by tree_elements
        acceptor.update(self)
        return acceptor, []

    def _update_from_dict(self, other, default_error):
        # update OptionsDict attributes
        if isinstance(other, OptionsDict):
            self._node_info += other._node_info
            # if len(self._node_info) > 1: raise Exception
        # now check item names and pass to superclass
        for k in other.keys():
            self._check_new_item_name(k)
        dict.update(self, other)

    def _update_from_dynamic_entries(self, functions, default_error):
        for func in functions:
            if not isinstance(func, FunctionType):
                raise default_error
            varnames = func.func_code.co_varnames
            self._check_new_item_name(func.__name__)
            self[func.__name__] = func

    def _update_from_class(self, basis_class, default_error):
        # recurse through the basis_class' superclasses first
        if basis_class.__bases__:
            for b in basis_class.__bases__:
                self._update_from_class(b, default_error)

        # ignore magic/hidden attributes, which are prefixed with
        # a double underscore
        entries = {k: basis_class.__dict__[k] \
                   for k in basis_class.__dict__.keys() \
                   if '__' not in k}
        # can now call update again
        self.update(entries)

    def _check_new_item_name(self, name):
        if name[0] == '_':
            raise OptionsDictException(
                "Prefixing an item with an underscore is not allowed "+\
                "because it \nmight clash with a hidden attribute.  If you "+\
                "want to set this attribute,\n you will need to register "+\
                "the name in mutable_attributes.")
        elif name in self.protected_attributes:
            raise OptionsDictException(
                "Setting an item called '{}' is not allowed because it "+\
                "would clash \nwith an attribute of the same name.  If you "+\
                "want to set this attribute,\n you will need to register "+\
                "the name in mutable_attributes.")
            
    def __str__(self):
        return self.str()

    def __repr__(self):
        return dict.__repr__(self) + repr(self._node_info)

    def __iter__(self):
        yield self

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError("'{}'".format(name))

    def __setattr__(self, name, value):
        if name in self.mutable_attributes:
            self.__dict__[name] = value
        else:
            self._check_new_item_name(name)
            self[name] = value
        
    def __eq__(self, other):
        result = isinstance(other, OptionsDict)
        if result:
            result *= self._node_info == other._node_info
            result *= dict.__eq__(self, other)
        return result

    def __ne__(self, other):
        return not self==other
    
    def __getitem__(self, key):
        try:
            value = dict.__getitem__(self, key)
        except:
            raise
        # recurse until the return value is no longer a function
        if isinstance(value, FunctionType):
            # dynamic entry
            return value(self)
        else:
            # normal entry
            return value

        
class CallableEntry:
    """
    Because the OptionsDict works by evaluating all function objects
    recursively, it is not able to return other functions specified by
    the client unless these are wrapped as callable objects.  This class
    provides such a wrapper.
    """
    def __init__(self, function):
        self.function = function
        
    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)


class Lookup:
    """
    Provides a function object that simply looks up a key in a
    dictionary.  This functionality was originally implemented as a
    closure, but the multiprocessing module couldn't pickle it.
    """
    def __init__(self, key):
        self.key = key

    def __call__(self, dictionary):
        return dictionary[self.key]


class Str:
    """
    Provides a function object that calls the str() method when passed
    an OptionsDict.  Optional arguments can be given upon
    initialisation.  See OptionsDict.str for further information.
    """
    def __init__(self, only=[], exclude=[], absolute={}, relative={}, 
                 formatter=None):
        self.only = only
        self.exclude = exclude
        self.absolute = absolute
        self.relative = relative
        self.formatter = formatter

    def __call__(self, options_dict):
        return options_dict.str(
            only=self.only, exclude=self.exclude, absolute=self.absolute,
            relative=self.relative, formatter=self.formatter)


def freeze(options_dicts):
    """
    Freezes the given OptionsDicts.  See OptionsDict.freeze for
    further information.
    """
    result = deepcopy(options_dicts)
    for od in result:
        od.freeze()
    return result
