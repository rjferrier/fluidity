from itertools import islice
from operator import mul

from base import nonmutable, OptionsBaseException
from options_dict import OptionsDict
from node_info import OrphanNodeInfo, ArrayNodeInfo


class OptionsNodeException(OptionsBaseException):
    pass

class OptionsArrayException(OptionsBaseException):
    pass

    
class OptionsTreeElement:
    """
    Abstract class to be inherited by OptionsArray and OptionsNode.
    This inheritance hierarchy is similar to the Composite pattern in
    that it can be used to build an arbitrary tree.  However,
    OptionsNode can act as a branch as well as a leaf, so it shares
    some of the parent-child functionality.
    """

    def __ne__(self, other):
        return not self == other

    @nonmutable
    def __mul__(self, other):
        self.multiply_attach(other)

    @nonmutable
    def __rmul__(self, other):
        # this conditional stops us trying to multiply with 1 during a
        # product() call
        if isinstance(other, OptionsTreeElement):
            self.multiply_attach(other)

    @nonmutable
    def __add__(self, other):
        self.attach(other)

    @nonmutable
    def __radd__(self, other):
        # this conditional stops us trying to add to 0 during a
        # product() call
        if isinstance(other, OptionsTreeElement):
            self.attach(other)

    def __imul__(self, other):
        self.multiply_attach(other)
        return self

    def __iadd__(self, other):
        self.attach(other)
        return self

    
class OptionsNode(OptionsTreeElement):
    """
    Contains an options dictionary and optionally a child
    OptionsTreeElement, hence forming a tree structure.
    """
    def __init__(self, name_or_class, entries={}, child=None,
                 array_name=None):
        try:
            # if name_or_class is a class, use it to extract a name
            # and create the options dictionary
            self.name = name_or_class.__name__
            self.options_dict = self.create_options_dict(name_or_class)
            
        except AttributeError:
            # otherwise, type-check name_or_class and set name
            if name_or_class is None:
                name_or_class = ''
            elif not isinstance(name_or_class, str):
                raise OptionsNodeException(
                    "name_or_class argument must be a string or a named "+\
                    "class (or None)" + str(name_or_class))
            self.name = name_or_class

            # set attributes.  Note that the entries argument may
            # still be a class, in which case its attributes and
            # methods will be converted to entries even if its name is
            # ignored.
            self.options_dict = self.create_options_dict(entries)

        # check child argument
        if child is not None and not isinstance(child, OptionsTreeElement):
            raise OptionsNodeException(
                "child argument must be an OptionsTreeElement (or None)")
        self.child = child

        
    @classmethod
    def another(Class, name, entries={}, child=None):
        return Class(name, entries, child)

        
    def create_options_dict(self, entries):
        """
        Overrideable factory method, used by the OptionsNode
        constructor.
        """
        od = OptionsDict(entries)
        od.set_node_info(self.create_info())
        return od

        
    def create_info(self):
        """
        Overrideable factory method, used by
        OptionsNode.create_options_dict.
        """
        return OrphanNodeInfo(self.name)

        
    def copy(self):
        return self.another(
            self.name, entries=self.options_dict.copy(),
            child=self.child.copy() if self.child else None)

        
    def collapse(self):
        """
        Returns a list of options dictionaries corresponding to the leaves
        in the the present tree structure.  Each dictionary is the
        result of a merge from the root, through the branch nodes, to
        the corresponding leaf.
        """
        try:
            # recurse 
            result = []
            for sub_od in self.child.collapse():
                # copy, inform and update the present dictionary with
                # each element in the result of the recursion
                od = self.options_dict.copy()
                od.update(sub_od)
                result.append(od)
            # return the merged dictionaries
            return result
            
        except AttributeError:
            # this is a leaf, so just return the current options
            # dictionary as a one-element list
            result = [self.options_dict.copy()]

        return result

            
    def multiply_attach(self, tree):
        """
        Appends a copy of tree to each leaf node in the present
        tree structure.
        """
        try:
            # recurse
            self.child.multiply_attach(tree)
        except AttributeError:
            self.child = tree.copy()

            
    def attach(self, tree):
        """
        Appends a copy of each root node in the tree argument (or
        whichever elements get traversed during iteration) to a
        corresponding leaf node in the present tree.  Returns the
        depleted source tree.
        """
        if not tree:
            # no more elements to attach, so exit early
            return None
        elif not self.child:
            # This is a leaf.  Copy and split the tree, making the
            # first element the child of this node and returning the
            # rest to the client.
            try:
                # polymorphic implementation, needed for handling
                # embedded node info correctly
                self.child, remainder = tree.donate_copy(self.child)
                return remainder
            except AttributeError:
                # manual implementation, for native iterables
                self.child = tree[0].copy()
                return tree[1:]
        else:
            # keep going
            return self.child.attach(tree)


    def donate_copy(self, acceptor):
        node_copy = self.copy()
        if acceptor:
            acceptor.attach(node_copy)
        else:
            acceptor = node_copy
        return acceptor, []

        
    def count_leaves(self):
        if self.child:
            return self.child.count_leaves()
        else:
            return 1

                
    def update(self, entries):
        """
        Updates the leaf dictionaries with entries.
        """
        if self.child:
            self.child.update(entries)
        else:
            self.options_dict.update(entries)

    
    def update_info(self, node_info=None):
        """
        Updates the nodes with node information.  If the argument is
        omitted, node info appropriate to an OptionsNode is
        constructed.
        """
        # default node info
        if not node_info:
            node_info = self.create_info()
        # delegate
        self.options_dict.set_node_info(node_info)

        
    def __eq__(self, other):
        result = isinstance(other, OptionsNode)
        if result:
            result *= self.name == other.name
            result *= self.options_dict == other.options_dict
            result *= self.child == other.child
        return result

    def __str__(self):
        return str(self.name)



class OptionsArray(OptionsTreeElement):
    """
    A sequence of OptionsNodes.
    """

    def __init__(self, array_name, elements, common_entries={},
                 name_format='{}'):
        """
        Returns an OptionsArray, wrapping the given elements as
        OptionsNodes where necessary.

        If a given element is not already an OptionsNode, it is
        converted to a string which becomes the name of a new
        OptionsNode.  The embedded dictionary acquires the entry
        {array_name: element}.  This feature is useful for setting up
        an independent variable with an associated array of values.

        For example,
           OptionsArray('velocity', [0.01, 0.02, 0.04])
        will contain
          [OptionsNode('0.01', {'velocity': 0.01}),
           OptionsNode('0.02', {'velocity': 0.02}),
           OptionsNode('0.04', {'velocity': 0.04})]
        but the nodes will contain different node info.
        
        All embedded dictionaries are initialised with common_entries
        if this argument is given.  The element-to-string conversion
        is governed by name_format, which can either be a format
        string or a callable that takes the element value and returns
        a string.
        """
        self.name = array_name
        self.nodes = []
        self.name_format = name_format
                
        # instantiate and record OptionsNodes
        for el in elements:
            node = self.create_options_node_general(el)
            # add entries
            node.update(common_entries)
            # append to the list
            self.nodes.append(node)

        # set array node information in each node.  This will replace
        # any preexisting node information.
        self.update_node_info()


    @classmethod
    def another(Class, array_name, elements, common_entries={},
                name_format='{}'):
        return Class(array_name, elements, common_entries, name_format)


    def create_options_node_general(self, thing):
        if isinstance(thing, dict):
            raise OptionsArrayException(
                "Creating an options node from a dictionary is not allowed, "+\
                "because it\n is not obvious how to name it or what to "+\
                "enter under the array key.\n Please construct an "+\
                "OptionsNode explicitly.")
            
        # If the thing is already an OptionsNode, simply copy it
        if isinstance(thing, OptionsNode):
            node = thing.copy()
            return node

        # If the thing is a named class, use it to instantiate a new
        # OptionsNode
        if hasattr(thing, '__name__'):
            return self.create_options_node(thing)

        # otherwise, instantiate a new OptionsNode with the original
        # thing stored under array_name.  Determine the node name.
        try:
            node_name = self.name_format(thing)
        except TypeError:
            try:
                node_name = self.name_format.format(thing)
            except AttributeError:
                raise OptionsArrayException(
                    "name_format must be a callable or a format string.")
        node = self.create_options_node(node_name)
        node.update({self.name: thing})
        return node
        
        
    def create_options_node(self, name_or_class):
        """
        Overrideable factory method, used by
        OptionsArray.create_options_node_general.
        """
        return OptionsNode(name_or_class)

        
    def copy(self):
        return self.another(self.name, [el.copy() for el in self])

        
    def collapse(self):
        """
        Returns a list of options dictionaries corresponding to the leaves
        in the the present tree structure.  Each dictionary is the
        result of a merge from the root, through the branch nodes, to
        the corresponding leaf.
        """
        result = []
        for el in self:
            result += el.collapse()
        return result

        
    def multiply_attach(self, tree):
        """
        Appends a copy of the given tree to each leaf node in the
        present tree.
        """
        # delegate to each node
        for el in self:
            el.multiply_attach(tree)


    def attach(self, tree):
        """
        Appends a copy of each root node in the tree argument (or
        whichever elements get traversed during iteration) to a
        corresponding leaf node in the present tree.  Returns the
        depleted source tree.
        """
        # delegate to each node
        for el in self:
            tree = el.attach(tree)
        return tree


    def donate_copy(self, acceptor):
        # It is nice to preserve array information, so grab a
        # one-element slice rather than a node.  The slice preserves
        # the OptionsArray type.
        one_node_array = self[0:1]
        one_node_array.update_node_info()
        if acceptor:
            acceptor.attach(one_node_array)
        else:
            acceptor = one_node_array
        # also return (a copy of) the depleted array
        return acceptor, self[1:]


    def count_leaves(self):
        return sum([el.count_leaves() for el in self.nodes])

        
    def update(self, entries):
        """
        Updates the leaf dictionaries with entries.
        """
        for el in self:
            el.update(entries)


    def update_node_info(self):
        """
        Updates the nodes with node information appropriate to an
        OptionsArray.
        """
        for i, node in enumerate(self.nodes):
            node.update_info(self.create_node_info(i))

        
    def create_node_info(self, index):
        """
        Overrideable factory method, used by
        OptionsArray.update_node_info.
        """
        node_names = [str(node) for node in self.nodes]
        return ArrayNodeInfo(self.name, node_names, index)


    def append(self, item):
        if not isinstance(item, OptionsNode):
            raise OptionsArrayException("item needs to be an OptionsNode")
        self.nodes.append(item)
        self.update_node_info()
            
    def pop(self):
        node = self.nodes.pop()
        # update node info on both sides
        node.update_info()
        self.update_node_info()
        return node
        
    def __len__(self):
        return len(self.nodes)
            
    def __eq__(self, other):
        result = isinstance(other, OptionsArray)
        if result:
            result *= self.name == other.name
            result *= len(self.nodes) == len(other.nodes)
            for node, other in zip(self.nodes, other.nodes):
                result *= node == other
        return result


    def __getitem__(self, index_or_name_or_slice):
        try:
            # treat argument as a slice
            indices = index_or_name_or_slice.indices(len(self.nodes))
            return self.another(self.name, islice(self.nodes, *indices))
        except AttributeError:
            pass

        try:
            # treat argument as a name
            index = [str(n) for n in self.nodes].index(index_or_name_or_slice)
        except ValueError:
            # default to an index
            index = index_or_name_or_slice

        return self.nodes[index]


    def __setitem__(self, index_or_slice, value_or_values):
        # convert to nodes
        try:
            value_or_values = [self.create_options_node_general(v) \
                               for v in value_or_values]
        except TypeError:
            value_or_values = self.create_options_node_general(value_or_values)
        self.nodes[index_or_slice] = value_or_values
        self.update_node_info()
        
    def __str__(self):
        return str(self.name)

    
def product(iterable):
    return reduce(mul, iterable, 1)
