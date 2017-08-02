
from typecube import core as tccore
from typecube import ext as tcext

"""
This is the basic implementation of a runtime capable of executing and evaluating typecube expressions.
"""

class Frame(object):
    """ A frame against which the current execution is happening. """
    def __init__(self, parent = None):
        self.bindings = {}
        self.parent = parent

class Runtime(object):
    def __init__(self):
        self.currframe = Frame()
        self.global_module = tcext.Module(None)

        # Register the base types into our global module
        # coremod = self.global_module.ensure_module("typecube.core")
        # extmod = self.global_module.ensure_module("typecube.ext")

        # Essentially we need types for encapsulating the core structures 
        # (like Expr, Type etc) and the functions to access/manipulate them
        # coremod.add("Expr", 
        # self.global_module.

    def eval(self, expr):
        """ Evaluates a new expression against this runtime. """
        pass
