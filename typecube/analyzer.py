

from __future__ import absolute_import

from ipdb import set_trace
from typecube import core as tccore
from typecube import ext as tcext
from typecube import errors
from typecube.utils import issubtype
from typecube.core import eprint

NONE = 0
FAILED = -1
STARTED = 1
SUCCESS = 2

class Analyzer(object):
    """ The semantic analyzer for a parsed onering expression tree.
    Does the following:

        1. Type checking of all function arguments and return types.
           All expressions will have their "inferred_type" parameters set.
        2. Resolves and fills in binding sites and scoping information for all 
           Variables and TypeRefs
        3. Any preliminary expression re-writes or transformations if necessary
    """
    def __init__(self, global_module, entities = None):
        """ Creates the analyzer.

        Params:
            global_module   -   The global module from which all modules stem.  This 
                                will be used as the initial look up of all dependant 
                                modules and entries.
            entities        -   Optional dictionary of entities to limit the 
                                analyzing to.
        """
        self.global_module = global_module
        self.resolvers = [global_module] if entities else []
        self.entities = entities or {"":self.global_module}
        self.analyzers = {
            tcext.Module: self.analyze_module,
            tccore.Fun: self.analyze_fun,
            tccore.Quant: self.analyze_quant,
            tccore.TypeOp: self.analyze_typeop,
            tccore.FunApp: self.analyze_funapp,
            tccore.QuantApp: self.analyze_quantapp,
            tccore.TypeApp: self.analyze_typeapp,
            tccore.FunType: self.analyze_funtype,
            tccore.Var: self.analyze_var,
            tccore.ProductType: self.analyze_container_type,
            tccore.SumType: self.analyze_container_type,
            tccore.AtomicType: self.analyze_atomic_type,

            tcext.ExprList: self.analyze_exprlist,
            tcext.Assignment: self.analyze_assignment,
            tcext.Index: self.analyze_index,
        }

    def analyze_var(self, var, visited):
        """ Resolves a name or a fqn given our current environment/resovler stack. """
        resolved_value = None
        for i in xrange(len(self.resolvers) - 1, -1, -1):
            resolver = self.resolvers[i]
            value = resolver.resolve_name(var.fqn)
            if value:
                resolved_value = value
                break

        if not resolved_value:
            raise errors.TCException("Cannot resolve '%s'" % var.fqn)

        thisentry = (id(resolver), var.fqn)
        new_visited = visited | {thisentry}

        # When resolving a variable entry a few things have to be considered:
        # 1. Who is resolving this variable?  Is it a module or a function?
        # 2. What kind of value is being resolved.  Is it a kind? a type?
        #    or an expression?  or another variable?
        # 3. If the binder is a function then is the function the immediate 
        #    parent or do we need to consider upvals/closures?
        var.binder = resolver
        self.analyze_entity(value, new_visited)

        if not value: set_trace()
        while value.isa(tccore.Var):
            self.analyze_var(value, new_visited)
            value = value.resolved_value

        if value.isa(tccore.TypeOp):
            # What does this mean to have a var that is referring
            # to a type op? eg something like:
            # a = map
            # Can this ever happen?
            # What should be the type of this ?
            var.inferred_type = value.inferred_type
            var.resolved_value = value
        else:
            if resolver.isa(tcext.Module):
                var.inferred_type = value.inferred_type
                var.resolved_value = value
            elif value.isany(tccore.Type):
                assert resolver.symtable.is_bound(var.fqn)
                var.inferred_type = value
                var.is_typevar = True
                # Var wont have a value - 
                # unless they are specified in a module in which case they will
                # TODO - Unify modules as "values" instead of special case
                # expressions so that values never need to have resolved values.
            else:
                set_trace()
                a = 3


    def analyze(self):
        for entry in self.entities.itervalues():
            old_resolvers = self.resolvers
            fqn = entry.fqn
            if fqn:
                parts = fqn.split(".")[:-1]
                self.resolvers = [self.global_module]
                if parts:
                    self.resolvers.append(self.global_module.get(parts))
            self.analyze_entity(entry, set())
            # reset resolvers
            self.resolvers = old_resolvers

    def analyze_entity(self, entry, visited):
        if not entry: set_trace()
        if getattr(entry, "analysis_status", NONE) in (NONE, FAILED, None):
            entry.analysis_status = STARTED
            self.analyzers[type(entry)](entry, visited)
            if not entry.inferred_type:
                entry.analysis_status = FAILED
                set_trace()
            entry.analysis_status = SUCCESS

    def analyze_module(self, entry, visited):
        map(self.analyze_entity, entry.child_entities)

    def analyze_fun(self, fun, visited):
        self.analyze_abs(fun, visited)
        self.resolvers.pop()

    def analyze_quant(self, quant, visited):
        self.analyze_abs(quant, visited)
        self.resolvers.pop()

    def analyze_typeop(self, typeop, visited):
        # For a typeop set the inferred type up front so we dont run into
        # trouble for recursive types
        typeop.inferred_type = tccore.make_fun_type(None, [tccore.KindType] * len(typeop.params), tccore.KindType)
        self.analyze_abs(typeop, visited)
        self.resolvers.pop()

    def analyze_funapp(self, funapp, visited):
        self.analyze_app(funapp, visited)

    def analyze_quantapp(self, quantapp, visited):
        self.analyze_app(quantapp, visited)

    def analyze_typeapp(self, typeapp, visited):
        self.analyze_app(typeapp, visited)

    def analyze_app(self, app, visited):
        """ Base analyzer for applications.
        1. Analyze expression and arguments.
        2. Ensure types of arguments match function signature 
        3. Checking currying semantics.
        """
        self.analyze_entity(app.expr, visited)
        [self.analyze_entity(a, visited) for a in app.args]
        # ensure that the abstraction's type args match the args passed to the application
        expr_type = app.expr.inferred_type
        if not expr_type:
            set_trace()
        for index,(stype,arg) in enumerate(zip(expr_type.source_types,app.args)):
            assert stype.isa(tccore.Ref)
            stype = stype.contents
            argtype = arg.inferred_type
            if not issubtype(argtype, stype):
                raise errors.TCException("Argument %d expects type %s but received type %s" % (index, repr(stype), repr(argtype)))

        # Types match so finalise the inferred type
        if len(app.args) > len(expr_type.source_types):
            raise TCException("Too many arguments for fun %s" % repr(app.expr))
        elif len(app.args) == len(expr_type.source_types):
            app.inferred_type = expr_type.return_type.contents
        else:
            set_trace()

        if app.expr.isany(tccore.App):
            # Here dont reduce it but just "collapse" multiple apps into one.
            # All Apps are kept just in the form (A b c d)
            set_trace()

    def analyze_abs(self, abs, visited):
        """ Base analyzer for abstractions.  
        1. Analyze child expression
        2. Ensure function return type is same as expression inferred type.
        """
        # Add the abs to our resolver stack first (the caller of this method will pop it off)
        if abs.fqn == 'apizen.common.models.Transformers.Http2AZValueResponse': set_trace()
        abs.resolved_value = abs
        self.resolvers.append(abs)
        if not abs.expr:
            # We have no expression, so set inferred_type to fun_type
            if not abs.fun_type:
                raise errors.TCException("Abstraction '%s' has neither a fun_type or expression to infer types from" % abs.fqn)
            self.analyze_entity(abs.fun_type, visited)
            abs.inferred_type = abs.fun_type
        else:
            self.analyze_entity(abs.expr, visited)
            if abs.fun_type:
                if not issubtype(abs.expr.inferred_type, abs.fun_type):
                    raise TCException("Abstractions %s declares return type %s but expressions returns %s" % (abs.fqn, repr(abs.expr.inferred_type), repr(abs.fun_type)))
                abs.inferred_type = abs.fun_type
            else:
                if abs.inferred_type is None: set_trace()
                assert abs.inferred_type is not None
                abs.fun_type = abs.inferred_type

    def analyze_funtype(self, funtype, visited):
        [self.analyze_entity(t.contents, visited) for t in funtype.source_types]
        if funtype.return_type:
            self.analyze_entity(funtype.return_type.contents, visited)
        funtype.inferred_type = tccore.KindType
        funtype.resolved_value = funtype

    def analyze_container_type(self, conttype, visited):
        conttype.inferred_type = tccore.KindType
        for ref in conttype.typerefs:
            self.analyze_entity(ref.contents, visited)

    def analyze_exprlist(self, exprlist, visited):
        for expr in exprlist.children:
            self.analyze_entity(expr, visited)
        exprlist.inferred_type = exprlist.children[-1].inferred_type

    def analyze_assignment(self, assignment, visited):
        var = assignment.expr.expr
        self.analyze_entity(assignment.expr, visited)
        assert assignment.expr.inferred_type
        parent = self.resolvers[-1]
        assert parent.isany(tccore.Abs)
        if assignment.is_temporary:
            parent.symtable.register(assignment.target.name, assignment.expr.inferred_type)
        self.analyze_entity(assignment.target, visited)
        # Ensure that target's type matches source expr's type
        issubtype(assignment.target.inferred_type, assignment.expr.inferred_type)
        assignment.inferred_type = assignment.expr.inferred_type

    def analyze_index(self, index, visited):
        self.analyze_entity(index.expr, visited)

        source_type = index.expr.inferred_type
        while source_type.isa(tccore.Ref):
            source_type = source_type.contents
        self.analyze_entity(source_type, visited)
        if source_type.isany(tccore.ContainerType):
            if type(index.key) in (str, unicode):
                assert index.expr.inferred_type.is_labelled
                index.inferred_type = source_type.type_for_param(index.key)
            else:
                assert type(index.index) in (int, long)
                index.inferred_type = source_type.type_at_index(index.key)
        elif source_type.isa(tccore.TypeApp):
            # A type application must first be reduced by applying its arguments to the
            # Type operator as here variables need to be bound.
            # We have a type application over a particular param so instead of reducing
            # the app via a substitution, just walk down the type with the param bindings
            # This is an opportunity for us to add a "constraint" to the type argument 
            # if it happens to be a type var.  The constraint would be "MustHaveField(key)"
            starting_type = source_type.expr.resolved_value.expr
            assert starting_type.isany(tccore.ContainerType)
            set_trace()
        else:
            set_trace()

    def analyze_atomic_type(self, atomic, visited):
        atomic.inferred_type = tccore.KindType
        atomic.resolved_value = atomic
