from copy import copy
from base import OptionsBaseException, INodeInfo


class NodeInfoException(OptionsBaseException):
    pass

    
class NodeInfo(INodeInfo):
    """
    Abstract class for describing contextual information about a node.
    The concrete methods herein are special cases which defer to the
    more general subclass methods.
    """
    def copy(self):
        return self.from_other(self)

    def belongs_to_any(self, collection_names):
        """
        self.belongs_to_any(collection_names)
        
        Returns True if the node in question is associated with any of
        collection_names.
        """
        for cn in collection_names:
            if self.belongs_to(cn):
                return cn
        return False
    
    def is_first(self):
        """
        self.is_first()
        
        Checks that the node in question is at the beginning of its
        container.
        """
        return self.at(0)
        
    def is_last(self):
        """
        self.is_last()
        
        Checks that the node in question is at the end of its container.
        """
        return self.at(-1)

    def _create_index(self, default, absolute, relative):
        # Helper to subclass str() methods
        if absolute is None:
            index = default
        else:
            index = absolute
        if relative is not None:
            index += relative
            if index < 0:
                raise IndexError("list index out of range")
        return index
        
    def __str__(self):
        return self.str()
        

class OrphanNodeInfo(NodeInfo):
    """
    Describes a node which is not part of any collection.
    """
    def __init__(self, node_name):
        self.node_name = node_name

    @classmethod
    def from_other(Class, other):
        return Class(other.node_name)

    def belongs_to(self, collection_name):
        """
        self.belongs_to(collection_name)

        The node is not part of a collection, so this method will
        always return False.
        """
        return False
    
    def at(self, index):
        """
        self.at(index)

        Checks that the node is at the given index, which for an orphan
        node is only true for 0 (first) and -1 (last).
        """
        return index in (0, -1)

    def str(self, absolute=None, relative=None, collection_separator=None):
        """
        self.str(absolute=None, relative=None, collection_separator=None)
        
        Returns the name of the node in question.  The optional arguments
        are not applicable for an orphan node.
        """
        args = [absolute, relative]
        for i, a in enumerate(args):
            if isinstance(a, dict):
                args[i] = None
        if self.at(self._create_index(0, *args)):
            return self.node_name
        else:
            raise IndexError("list index out of range")

    def __eq__(self, other):
        result = isinstance(other, OrphanNodeInfo)
        if result:
            result *= self.node_name == other.node_name
        return result

        
class ArrayNodeInfo(NodeInfo):
    """
    Describes a node which is part of an array (or sequence).
    """
    def __init__(self, array_name, node_names, node_index):
        self.array_name = array_name
        self.node_names = node_names
        self.node_index = node_index

    @classmethod
    def from_other(Class, other):
        return Class(
            other.array_name, copy(other.node_names), other.node_index)

    def belongs_to(self, collection_name):
        """
        self.belongs_to(collection_name)

        Returns True if the node in question is associated with the
        given collection name.
        """
        return collection_name == self.array_name

    def at(self, index):
        """
        self.at(index)
        
        Checks that the node in question is at the given index, which can
        be negative to signify position from the end of the sequence.
        """
        return self.node_index == index or \
            self.node_index == index + len(self.node_names)
        
    def str(self, absolute=None, relative=None, collection_separator=None):
        """
        self.str(absolute=None, relative=None, collection_separator=None)
        
        Returns the name of the node in question or, if arguments are
        given, one of its siblings.  The optional arguments correspond
        to absolute and relative indices, respectively.  In accordance
        with Python indexing rules, a negative absolute index returns
        a node from the end of the array.  To prevent confusion,
        however, this shall not apply when a relative index is given.

        The optional arguments may also be supplied as dicts with
        entries of the form {array_name: index}.  In this case, the
        the indices will be dereferenced if possible using the present
        array name.

        If collection_separator is given, the array name will be
        prepended to the string followed by collection_separator.
        """
        args = [absolute, relative]
        for i, a in enumerate(args):
            try:
                # convert the argument from a dict to an index 
                args[i] = a[self.array_name]
            except KeyError:
                # lookup failed, so give up on this argument
                args[i] = None
            except TypeError:
                # if argument is not a dict, it is presumably already
                # an index
                pass
        result = ''
        if collection_separator is not None:
            result += self.array_name + collection_separator
        result += self.node_names[self._create_index(self.node_index, *args)]
        return result
        
    def __eq__(self, other):
        result = isinstance(other, ArrayNodeInfo)
        if result:
            result *= self.array_name == other.array_name
            result *= self.node_names == other.node_names
            result *= self.node_index == other.node_index
        return result


class SimpleFormatter:
    """
    Function object that represents a combination of nodes as
    c0:n0_c1:n1_c2:n2, where ci and ni are the collection and node
    names associated with the i'th node.  The ':' and '_' separators
    can be defined upon initialisation.
    """
    def __init__(self, node_separator='_', collection_separator=None):
        self.node_separator = node_separator
        self.collection_separator = collection_separator

    def __call__(self, node_info_list, absolute={}, relative={}, 
                 only_indent=False):
        if only_indent:
            return ''
        substrings = []
        for ni in node_info_list:
            substr = ''
            substr += ni.str(absolute=absolute, relative=relative, 
                             collection_separator=self.collection_separator)
            if substr:
                substrings.append(substr)
        if node_info_list:
            result = self.node_separator.join(substrings)
        else:
            result = ''.join(substrings)
        return result

        
class TreeFormatter:
    """
    Function object that represents a combination of nodes as a tree
    fragment, e.g.
    c0:n0
        c1:n1
            c2:n2
    where ci and ni are the collection and node names associated with
    the i'th node.  The indent and the ':' separator can be defined
    upon initialisation.

    When the object is made to operate on a complete list of node
    combinations in serial, the complete tree emerges.
    """
    def __init__(self, indent_string=' '*4, collection_separator=': '):
        self.indent_string = indent_string
        self.collection_separator = collection_separator
 
    def __call__(self, node_info_list, absolute={}, relative={}, 
                 only_indent=False):
        branch = ''
        indent = ''
        for level, ni in enumerate(node_info_list):
            # get a descriptor for the current node
            substr = ni.str(absolute=absolute, relative=relative, 
                            collection_separator=self.collection_separator)

            # if not the first node, the branch up to this point will
            # have already been printed, so reset the branch
            if not ni.is_first():
                branch = ''

            # cycle if blank
            if not substr:
                continue

            # if we are not at the root, do a newline in preparation
            # for the new node
            if branch:
                branch += '\n'

            # add the node to the branch and increase the indent for
            # next time
            branch += indent + substr
            indent += self.indent_string

        if only_indent:
            return indent
        else:
            return branch
