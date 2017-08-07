

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

    def analyze_var(self, var):
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


        # When resolving a variable entry a few things have to be considered:
        # 1. Who is resolving this variable?  Is it a module or a function?
        # 2. What kind of value is being resolved.  Is it a kind? a type?
        #    or an expression?  or another variable?
        # 3. If the binder is a function then is the function the immediate 
        #    parent or do we need to consider upvals/closures?
        var.binder = resolver
        self.analyze_entity(value)

        if not value: set_trace()
        while value.isa(tccore.Var):
            self.analyze_var(value)
            value = value.reference

        if value.isa(tccore.Var): set_trace()

        if value.isa(tccore.TypeOp):
            # What does this mean to have a var that is referring
            # to a type op? eg something like:
            # a = map
            # Can this ever happen?
            # What should be the type of this ?
            var.inferred_type = value.inferred_type
            var.reference = value
        else:
            if resolver.isa(tcext.Module):
                var.inferred_type = value.inferred_type
                var.reference = value
            else:
                if value.isany(tccore.Type):
                    assert resolver.symtable.is_bound(var.fqn)
                    var.inferred_type = value
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
            self.analyze_entity(entry)
            # reset resolvers
            self.resolvers = old_resolvers

    def analyze_entity(self, entry):
        if not entry: set_trace()
        if getattr(entry, "analysis_status", NONE) in (NONE, FAILED, None):
            entry.analysis_status = STARTED
            self.analyzers[type(entry)](entry)
            if not hasattr(entry, "inferred_type"):
                entry.analysis_status = FAILED
                set_trace()
                assert entry.inferred_type is not None
            entry.analysis_status = SUCCESS

    def analyze_module(self, entry):
        map(self.analyze_entity, entry.child_entities)

    def analyze_fun(self, fun):
        self.analyze_abs(fun)
        self.resolvers.pop()

    def analyze_quant(self, quant):
        self.analyze_abs(quant)
        self.resolvers.pop()

    def analyze_typeop(self, typeop):
        # For a typeop set the inferred type up front so we dont run into
        # trouble for recursive types
        typeop.inferred_type = tccore.make_fun_type(None, [tccore.KindType] * len(typeop.params), tccore.KindType)
        self.analyze_abs(typeop)
        self.resolvers.pop()

    def analyze_funapp(self, funapp):
        self.analyze_app(funapp)

    def analyze_quantapp(self, quantapp):
        self.analyze_app(quantapp)

    def analyze_typeapp(self, typeapp):
        self.analyze_app(typeapp)
        # Here we want to apply the type op to its arguments and get
        # a reduced value
        if typeapp.expr.isa(tccore.Var) and typeapp.expr.fqn not in ("list", "map"):
            set_trace()
        typeapp.reduced_value, reduced = typeapp.reduce()

    def analyze_app(self, app):
        """ Base analyzer for applications.
        1. Analyze expression and arguments.
        2. Ensure types of arguments match function signature 
        3. Checking currying semantics.
        """
        self.analyze_entity(app.expr)
        map(self.analyze_entity, app.args)
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

    def analyze_abs(self, abs):
        """ Base analyzer for abstractions.  
        1. Analyze child expression
        2. Ensure function return type is same as expression inferred type.
        """
        # Add the abs to our resolver stack first (the caller of this method will pop it off)
        self.resolvers.append(abs)
        if not abs.expr:
            # We have no expression, so set inferred_type to fun_type
            if not abs.fun_type:
                raise errors.TCException("Abstraction '%s' has neither a fun_type or expression to infer types from" % abs.fqn)
            self.analyze_entity(abs.fun_type)
            abs.inferred_type = abs.fun_type
        else:
            self.analyze_entity(abs.expr)
            if abs.fun_type:
                if not issubtype(abs.expr.inferred_type, abs.fun_type):
                    raise TCException("Abstractions %s declares return type %s but expressions returns %s" % (abs.fqn, repr(abs.expr.inferred_type), repr(abs.fun_type)))
            else:
                assert abs.inferred_type is not None
                abs.fun_type = abs.inferred_type

    def analyze_funtype(self, funtype):
        [self.analyze_entity(t.contents) for t in funtype.source_types]
        if funtype.return_type:
            self.analyze_entity(funtype.return_type.contents)
        funtype.inferred_type = tccore.KindType
        funtype.resolved_value = funtype

    def analyze_container_type(self, conttype):
        for ref in conttype.typerefs:
            self.analyze_entity(ref.contents)
        conttype.inferred_type = tccore.KindType

    def analyze_exprlist(self, exprlist):
        for expr in exprlist.children:
            self.analyze_entity(expr)
        exprlist.inferred_type = exprlist.children[-1].inferred_type

    def analyze_assignment(self, assignment):
        var = assignment.expr.expr
        self.analyze_entity(assignment.expr)
        assert assignment.expr.inferred_type
        parent = self.resolvers[-1]
        assert parent.isany(tccore.Abs)
        if assignment.is_temporary:
            parent.symtable.register(assignment.target.name, assignment.expr.inferred_type)
        self.analyze_entity(assignment.target)
        # Ensure that target's type matches source expr's type
        issubtype(assignment.target.inferred_type, assignment.expr.inferred_type)
        assignment.inferred_type = assignment.expr.inferred_type


    def analyze_index(self, index):
        self.analyze_entity(index.expr)

        source_type = index.expr.inferred_type
        while source_type.isa(tccore.Ref):
            source_type = source_type.contents
        self.analyze_entity(source_type)
        if source_type.isany(tccore.ContainerType):
            if type(index.key) in (str, unicode):
                assert index.expr.inferred_type.is_labelled
                index.inferred_type = source_type.type_for_param(index.key)
            else:
                assert type(index.index) in (int, long)
                index.inferred_type = source_type.type_at_index(index.key)
        else:
            set_trace()

    def analyze_atomic_type(self, atomic):
        atomic.inferred_type = tccore.KindType
        atomic.resolved_value = atomic
