"""
This module is deprecated in favour of tree_elements.py, which
provides a more intuitive means of putting together combinations of
options.
"""

from collections import Iterable
from itertools import imap, izip, chain, product as _product
from functools import wraps
from copy import deepcopy
from inspect import getargspec, getargvalues


def iflatten(iterable):

    """
    iflatten(iterable)

    Flattens an arbitrary tree of iterators, e.g. (1, (2, 3)) -> (1, 2,
    3).  Taken from the webpage below, with an added condition to stop
    iterating if the iterable is a dictionary.
    
    http://stackoverflow.com/questions/2158395/
    flatten-an-irregular-list-of-lists-in-python
    """
    for el in iterable:
        if isinstance(el, Iterable) and \
                not isinstance(el, basestring) and \
                not isinstance(el, dict):
            for sub in iflatten(el):
                yield sub
        else:
            yield el

    
def iattach(parents, children):
    """iattach(parents, children)

    Attaches the elements of children to the elements of parents,
    assuming the arguments are the same length.  Example:
    ('A', 'B'), ((1, 2, 3), (4, 5)) 
       --> ('A', 1), ('A', 2), ('A', 3), ('B', 4), ('B', 5)

    More specifically, zips parents with children, and for each of
    these pairings performs a product.  The results are chained.
    Strings and dictionary elements are protected so that their
    elements don't explode.
    """
    def protect(el):
        if (isinstance(el, basestring) and len(el) > 1) or \
                isinstance(el, dict):
            return (el,)
        else:
            return el
    return chain.from_iterable(
        imap(lambda i: _product(*i),
             izip(imap(protect, parents),
                  children)))


def make_optionally_persistent(generator, persistent):
    """
    make_optionally_persistent(generator, persistent)

    Helper function to optionally convert a generator into a list.
    """
    if persistent:
        return list(generator)
    else:
        return generator

            
def flatten(iterable, persistent=True):
    """
    flatten(iterable, persistent=True)

    Optionally persistent version of iattach.  To repeat the 
    documentation:

    Flattens an arbitrary tree of iterators, e.g. (1, (2, 3)) -> (1, 2,
    3).  Taken from the webpage below, with an added condition to stop
    iterating if the iterable is a dictionary.
    
    http://stackoverflow.com/questions/2158395/
    flatten-an-irregular-list-of-lists-in-python
    """
    result = iflatten(iterable)
    return make_optionally_persistent(result, persistent)


def attach(parents, children, persistent=True):
    """
    attach(parents, children, persistent=True)

    Optionally persistent version of iattach.  To repeat the 
    documentation:

    Attaches the elements of children to the elements of parents,
    assuming the arguments are the same length.  Example:
    ('A', 'B'), ((1, 2, 3), (4, 5)) 
       --> ('A', 1), ('A', 2), ('A', 3), ('B', 4), ('B', 5)

    More specifically, zips parents with children, and for each of
    these pairings performs a product.  The results are chained.
    Strings and dictionary elements are protected so that their
    elements don't explode.
    """
    result = iattach(parents, children)
    return make_optionally_persistent(result, persistent)

        
def product(*iterables, **kwargs):
    """
    product(*iterables, repeat=None, persistent=True)

    Optionally persistent version of itertools' product.  To repeat 
    the documentation:

    Cartesian product of input iterables.

    Equivalent to nested for-loops in a generator expression. For
    example, product(A, B) returns the same as ((x,y) for x in A for y
    in B).

    The nested loops cycle like an odometer with the rightmost element
    advancing on every iteration. This pattern creates a lexicographic
    ordering so that if the input's iterables are sorted, the product
    tuples are emitted in sorted order.

    To compute the product of an iterable with itself, specify the
    number of repetitions with the optional repeat keyword argument. 
    For example, product(A, repeat=4) means the same as 
    product(A, A, A, A).
    """
    persistent = kwargs.pop('persistent', True)
    result = _product(*iterables, **kwargs)
    return make_optionally_persistent(result, persistent)


def merge(dict_combination):
    """
    merge(dict_combination)

    Flattens and merges a combination of dictionaries.  This may be
    useful when one wants to iterate over a collection of combinations
    produced by itertools.
    """
    single_dict = None
    if isinstance(dict_combination, dict):
        dict_combination = (dict_combination,)
    for i, el in enumerate(iflatten(dict_combination)):
        if single_dict is None:
            single_dict = el.copy()
        else:
            single_dict.update(el)
    return single_dict

    
def merges_dicts(client_function):
    """
    merges_dicts(client_function)

    A decorator that flattens and merges a combination of
    dictionaries, passing the result to the client function.  This may
    be useful when one wants to map the function to a collection of
    combinations produced by itertools.
    """
    if len(getargspec(client_function)[0])==2:
        # client_function has two args so is presumably bound to
        # something
        @wraps(client_function)
        def decorator(self, dict_combination):
            return client_function(self, merge(dict_combination))
    else:
        @wraps(client_function)
        def decorator(dict_combination):
            return client_function(merge(dict_combination))
    return decorator
    

class Lookup:
    """
    Lookup(key)
    
    Provides a function object that simply looks up a key in a
    dictionary or combination of dictionaries.  This functionality was
    originally implemented as a closure, but the multiprocessing
    module couldn't pickle it.
    """
    def __init__(self, key):
        self.key = key

    @merges_dicts
    def __call__(self, dictionary):
        return dictionary[self.key]
