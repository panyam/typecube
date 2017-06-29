
import ipdb
from enum import Enum
from typelib import core as tlcore
from typelib.core import Expr
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier
from typelib.utils import FieldPath

BooleanType = tlcore.make_literal_type("boolean")
ByteType = tlcore.make_literal_type("byte")
IntType = tlcore.make_literal_type("int")
LongType = tlcore.make_literal_type("long")
FloatType = tlcore.make_literal_type("float")
DoubleType = tlcore.make_literal_type("double")
StringType = tlcore.make_literal_type("string")
MapType = tlcore.TypeFun("map", ["K", "V"], tlcore.make_extern_type("map", ["K", "V"]), None)
ListType = tlcore.TypeFun("list", ["V"], tlcore.make_extern_type("list", ["V"]), None)

class Assignment(Expr):
    def __init__(self, parent_function, target_variable, expr):
        Expr.__init__(self)
        self.parent_function = parent_function
        self.target_variable = target_variable
        self.expr = expr

    def _evaltype(self, resolver_stack):
        resolved_expr = self.expr.resolve(resolver_stack)
        return resolved_expr.evaltype(resolver_stack)

    def _resolve(self, resolver_stack):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve the target variable's binding.  This does'nt necessarily have
        # to evaluate types.
        # This will help us with type inference going backwards
        resolved_var = self.target_variable.resolve(resolver_stack)

        # Resolve all types in child exprs.  
        # Apart from just evaluating all child exprs, also make sure
        # Resolve field paths that should come from source type
        resolved_expr = self.expr.resolve(resolver_stack)
        return self

class Literal(Expr):
    """
    An expr that contains a literal value like a number, string, boolean, list, or map.
    """
    def __init__(self, value, value_type):
        Expr.__init__(self)
        self.value = value
        self.value_type = value_type

    def _evaltype(self, resolver_stack):
        return self.value_type

    def resolve(self, resolver):
        return self

    def __repr__(self):
        return "<Literal(0x%x), Value: %s>" % (id(self), str(self.value))

class ExprList(Expr):
    """ A list of statements. """
    def __init__(self, children = None):
        Expr.__init__(self)
        self.children = children or []

    def add(self, expr):
        self.children.append(expr)

    def _evaltype(self, resolver_stack):
        resolved = self.resolve(resolver_stack)
        return resolved.children[-1].evaltype(resolver_stack)

    def _resolve(self, resolver_stack):
        resolved_exprs = [expr.resolve(resolver_stack) for expr in self.children]
        if any(x != y for x,y in zip(self.children, resolved_exprs)):
            return ExprList(resolved_exprs)
        return self

class DictExpr(Expr):
    def __init__(self, values):
        super(DictExpr, self).__init__()
        self.values = values

    def _resolve(self, resolver_stack):
        ipdb.set_trace()
        for key,value in self.values.iteritems():
            key.resolve(resolver_stack)
            value.resolve(resolver_stack)

        # TODO - Unify the types of child exprs and find the tightest type here Damn It!!!
        return self

class ListExpr(Expr):
    def __init__(self, values):
        super(ListExpr, self).__init__()
        self.values = values

    def _evaltype(self, resolver_stack):
        # TODO - Unify the types of child exprs and find the tightest type here Damn It!!!
        return ListType.apply(tlcore.AnyType)

    def _resolve(self, resolver_stack):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        resolved_exprs = [expr.resolve(resolver_stack) for expr in self.values]
        if any(x != y for x,y in zip(self.values, resolved_exprs)):
            return ListExpr(resolved_exprs)
        return self

class TupleExpr(Expr):
    def __init__(self, values):
        super(TupleExpr, self).__init__()
        self.values = values or []

    def _evaltype(self, resolver_stack):
        # TODO - Unify the types of child exprs and find the tightest type here Damn It!!!
        return ListType.apply(tlcore.AnyType)

    def _resolve(self, resolver_stack):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        resolved_exprs = [expr.resolve(resolver_stack) for expr in self.values]
        if any(x != y for x,y in zip(self.values, resolved_exprs)):
            return TupleExpr(resolved_exprs)
        return self

class IfExpr(Expr):
    """ Conditional exprs are used to represent if-else exprs. """
    def __init__(self, cases, default_expr):
        super(IfExpr, self).__init__()
        self.cases = cases or []
        self.default_expr = default_expr or []

    def __repr__(self):
        return "<CondExp - ID: 0x%x>" % (id(self))

    def set_evaluated_typeexpr(self, vartype):
        assert False, "cannot set evaluated type of an If expr (yet)"

    def _resolve(self, resolver_stack):
        """ Resolves bindings and types in all child exprs. """
        ipdb.set_trace()
        assert self._evaluated_typeexpr == None, "Type has already been resolved, should not have been called twice."

        for condition, expr in self.cases:
            condition.resolve()
            expr.resolve()

        if self.default_expr: self.default_expr.resolve()

        # TODO: Return a union type instead
        self._evaluated_typeexpr = tlcore.VoidType
        return self
