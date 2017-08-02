

from __future__ import absolute_import

from ipdb import set_trace
from typecube import core as tccore
from typecube import ext as tcext
from typecube import errors
from typecube.core import eprint

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
            tccore.Ref: self.analyze_ref,
            tccore.Var: self.analyze_var,
            tccore.ProductType: self.analyze_container_type,
            tccore.SumType: self.analyze_container_type,
            tccore.AtomicType: self.analyze_atomic_type,

            tcext.ExprList: self.analyze_exprlist,
            tcext.Assignment: self.analyze_assignment,
            tcext.Index: self.analyze_index,
        }

    def resolve_variable(self, var):
        """ Resolves a name or a fqn given our current environment/resovler stack. """
        resolved_value = None
        for i in xrange(len(self.resolvers) - 1, -1, -1):
            resolver = self.resolvers[i]
            value = resolver.resolve_name(var.fqn)
            if value:
                resolved_value = value
                break

        if not resolved_value:
            raise errors.TCException("Cannot resolve '%s'" % name)

        var.binder = resolver
        set_trace()
        if value.isany(tccore.Type):
            var.inferred_type = tccore.KindType
        else:
            if value.isa(tccore.ProductType): set_trace()
            self.analyze_entity(value)
            # TODO - Cycles?
            var.inferred_type = value.inferred_type
            var.resolved_value = value.resolved_value

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
        NONE = 0
        FAILED = -1
        STARTED = 1
        SUCCESS = 2
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
        self.analyze_abs(typeop)
        typeop.inferred_type = tccore.make_fun_type(None, [tccore.KindType] * len(typeop.params), tccore.KindType)
        typeop.resolved_value = typeop
        self.resolvers.pop()

    def analyze_funapp(self, funapp):
        self.analyze_app(funapp)

    def analyze_quantapp(self, quantapp):
        self.analyze_app(quantapp)

    def analyze_typeapp(self, typeapp):
        self.analyze_app(typeapp)
        # Do the application and set that as the resolved value
        typeapp.resolved_value, reduced = typeapp.reduce()
        if typeapp.resolved_value.isany(tccore.Type):
            typeapp.inferred_type = tccore.KindType
        elif typeapp.resolved_value.isa(tccore.TypeOp):
            typeop = typeapp.resolved_value
            assert len(typeop.params) > 0, "TypeOp cannot have 0 type params"
            typeop.inferred_type = tccore.make_fun_type(None, [tccore.KindType] * len(typeop.params), tccore.KindType)
        else:
            assert False

    def analyze_app(self, app):
        """ Base analyzer for applications.
        1. Analyze expression and arguments.
        2. Ensure types of arguments match function signature 
        3. Checking currying semantics.
        """
        self.analyze_entity(app.expr)
        map(self.analyze_entity, app.args)

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
            set_trace()

    def analyze_ref(self, ref):
        self.analyze_entity(ref.contents)
        ref.inferred_type = ref.contents.inferred_type
        ref.resolved_value = ref.contents.resolved_value

    def analyze_var(self, var):
        self.resolve_variable(var)

    def analyze_funtype(self, funtype):
        [self.analyze_entity(t.contents) for t in funtype.source_types]
        if funtype.return_type:
            self.analyze_entity(funtype.return_type.contents)
        funtype.inferred_type = tccore.KindType
        funtype.resolved_value = funtype

    def analyze_container_type(self, conttype):
        for ref in conttype.typerefs:
            self.analyze_entity(ref)
        conttype.inferred_type = tccore.KindType
        conttype.resolved_value = conttype

    def analyze_exprlist(self, exprlist):
        for expr in exprlist.children:
            self.analyze_entity(expr)
        exprlist.inferred_type = exprlist.children[-1].inferred_type

    def analyze_assignment(self, assignment):
        self.analyze_entity(assignment.expr)
        assert assignment.expr.inferred_type
        parent = self.resolvers[-1]
        assert parent.isany(Abs)
        if assignment.is_temporary:
            parent.symbol_table.register(assignment.target.name, assignment.expr.inferred_type)
        self.analyze_entity(assignment.target)
        # Ensure that target's type matches source expr's type
        self.ensure_types(assignment.target.inferred_type, assignment.expr.inferred_type)
        assignment.inferred_type = assignment.expr.inferred_type


    def analyze_index(self, index):
        if index.key == "statusCode": 
            set_trace()
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
