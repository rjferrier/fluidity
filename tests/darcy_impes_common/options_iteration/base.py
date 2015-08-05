"""
This module contains helper functions, a base exception for the
package, and pure abstract base classes that may be useful for testing
and extension purposes.
"""

from functools import wraps


def nonmutable(method):
    """
    Decorator that calls method but provides a new object instead of
    modifying the current one.  This means the call can be inlined
    neatly without mutating the operands.
    """
    def decorator(self, other):
        result = self.copy()
        method(result, other)
        return result
    return decorator

    
class OptionsBaseException(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


class INodeInfo:
    def copy(self):
        raise NotImplementedError
        
    def belongs_to(self, collection_name):
        raise NotImplementedError
        
    def belongs_to_any(self, collection_names):
        raise NotImplementedError
        
    def at(self, index):
        raise NotImplementedError
        
    def is_first(self):
        raise NotImplementedError
        
    def is_last(self):
        raise NotImplementedError
        
    def str(self, absolute=None, relative=None, collection_separator=None):
        raise NotImplementedError
