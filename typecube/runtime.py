
from ipdb import set_trace
from typecube import core as tccore
from typecube import ext as tcext
from typecube import errors

"""
This is the basic implementation of a runtime capable of executing and evaluating typecube expressions.
"""

class Context(object):
    """ Used to store naming contexts for all variables declared during static and runtime phases of the evaluation.
    The context supports nesting as well as layering.  By nesting, entities inside parent entities (indexed by fully qualified names)
    are allowed.  For instance:

        a record Foo in the module a.b.c is simply the following module structure:

            {
                'a': {
                    'b': {
                        'c': {
                            'Foo': record { .... }
                        }
                    }
                 }
            }

        We can also have layering - That is when environments are pushed and popped to handle function entries and exits.
    """
    def __init__(self, binder, previous = None):
        # A context is usually created when a new "binding" object like a module, 
        # or a function or a dictionary takes over.  This is specified in this binder object.
        self.binder = binder
        self.previous = previous
        self.bindings = {}

    def get(self, fqn_or_parts):
        """ Search for an entry in the given context by its FQN or recursively in parent contexts. """
        parts = fqn_or_parts
        if type(fqn_or_parts) in (unicode, str):
            parts = fqn_or_parts.split(".")
        curr = self.bindings
        for part in parts:
            if part not in curr:
                return None
            curr = curr[part]
        return curr

    def set(self, fqn_or_parts, value):
        """ Sets the value of an entry given its FQN to its new value. """
        parts = fqn_or_parts
        if type(fqn_or_parts) in (unicode, str):
            parts = fqn_or_parts.split(".")
        parts, last = parts[:-1], parts[-1]
        curr = self.bindings
        for part in parts:
            if part not in curr:
                curr[part] = {}

            if not isinstance(part, dict):
                set_trace()
            curr = curr[part]
        curr[last] = value

    def push(self, binder):
        """ Push a new context as a result of a function entry. """
        return Context(binder, self)

    def pop(self):
        """ Pop the last pushed context due to a function return. """
        return self.previous

class Runtime(object):
    def __init__(self):
        self.context = None
        self.global_module = tcext.Module(None)

        # Register the base types into our global module
        # coremod = self.global_module.ensure_module("typecube.core")
        # extmod = self.global_module.ensure_module("typecube.ext")

        # Essentially we need types for encapsulating the core structures 
        # (like Expr, Type etc) and the functions to access/manipulate them
        # coremod.add("Expr", 
        # self.global_module.

    def push_context(self, binder): self.context = self.context.push(binder)
    def pop_context(self): self.context = self.context.pop()

    def eval(self, expr):
        """ Evaluates a new expression against this runtime. """
        set_trace()
        pass

    def analyze(self, expr):
        """ Before an eval is called an expression must be analyzed against the context.  
        This ensures that the expression passes through name resolution, bindings and 
        type checks before it is dynamically ready for evalution.

        When is the analysis phase of an expression too early?  For example if we want
        late binding then we could leave variables as is and have them late bound, but
        this could be too slow?

        For example in a function application - late binding simply binds a variables to
        the bound param.  

        But in a record declaration or a module, late binding *may* not make sense unless
        the module is created inside a function!   So we can decide that here.  If the 
        binder for a variable is a function/abstraction then keep it ephemeral.  Otherwise
        make it permanent.  Another option is for the binding to indicate whether it is to
        be permanent or temporary.
        """
        set_trace()
        unprocessed, processed = [expr], []

        # General idea is we want to eliminate recursion as much as possible
        # This is done with an interative post order processing of the expression tree
        # because an expression's children need to be processed before the node itself
        # is processed.  Unlike a normal traversal after processing of the children
        # the parent expression has to be called again to "handle" the processed
        # children.
        #
        # This is done by maintaining two stacks (as with the vanilla post order processing)
        # But instead of processed and unprocessed stacks, we maintain unprocessed and
        # "pending" stacks.  Like in the normal PO processing, we add the expression that
        # was fetched from the unprocessed stack onto the pending stack.  This is done to 
        # break down the analysis to "resolve" and "validate" phases.  The resolve and
        # validate phases happen in an interweaved fashion where as soon as the children
        # are resolved and validated, the parent is validated and so on.

        while stack:
            next = stack.pop()
            if next.isany(tccore.App):
                # An application so take care of expressiona nd 
                # Take care of expression and arguments first, 
                pass

    def resolve(self, expr):
        """ The resolution phase simply binds variables and other names to their binding sites.
        This phase when seperated makes the analysis phase easier so everything is known about
        a symbol instead of having to be found.  Also this way if resolution is not required 
        (ie the parser can do this) we can totally skip this step.

        But doing this poses one problem.  Unlike in the analysis phase we cannot fail if a 
        resolution fails for a failure because it may be due to lazy loading or out of phase
        loading of entries.   Subsequent resolutions can succeed as new entries are loaded.

        So for this the runtime can maintain a list of unresolved entries.
        """
        t = type(expr)
        if t in (tccore.AtomicType, tccore.Literal):
            pass
        elif isinstance(expr, tcext.Module):
            old_context = runtime.context
            if isinstance(runtime.context.binder, tcext.Module):
                # nested objects do not extend scope - they just replace it - for now
                runtime.context = Context(expr)
            else:
                runtime.push_context(expr)
            map(self.resolve, entry.itervalues())
            runtime.context = old_context
        elif isinstance(expr, tccore.Abs):
            abs = expr
            if abs.expr:
                # First extend the context with our params
                runtime.push_context(abs)
                for p in abs.params:
                    context.set(p, {'binder': abs})
                self.resolve(abs.expr)
                runtime.pop_context()
        elif isinstance(expr, tccore.App):
            self.resolve(expr.expr)
            map(self.resolve, expr.args)
        elif isinstance(expr, tccore.FunType):
            funtype = expr
            [self.resolve(t.contents) for t in funtype.source_types]
            if funtype.return_type:
                self.resolve(funtype.return_type.contents)
        elif isinstance(expr, tccore.ContainerType):
            conttype = expr
            for ref in conttype.typerefs:
                self.resolve(ref.contents, visited)
        elif isinstance(expr, tccore.ExprList):
            map(self.resolve, expr.children)
        elif isinstance(expr, tcext.Assignment):
            asgn = expr
            parent = self.context.binder
            assert parent.isany(tccore.Abs)
            self.resolve(asgn.expr)
            if asgn.is_temporary:
                parent.symtable.register(asgn.target.name, None)
            self.resolve(assignment.target)
        elif isinstance(expr, tcext.Macro):
            expr = expr.expression
            self.resolve(expr)
        elif isinstance(expr, tccore.Var):
            var.binder = self.get_var_binder(expr)
        else:
            set_trace()
        
    def get_var_binder(self, var):
        curr = self.context
        last = None
        while curr:
            last = curr
            resvalue = curr.binder.resolve_name(var.fqn)
            if resvalue:
                return curr.binder
            curr = curr.parent

        if last != self.global_module:
            resvalue = self.global_module.resolve_name(var.fqn)
            if resvalue:
                return self.global_module

        raise errors.TCException("Cannot resolve '%s'" % var.fqn)
