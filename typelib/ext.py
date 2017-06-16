
import ipdb
from enum import Enum
from typelib import core as tlcore
from typelib.core import Expression
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

class Assignment(Expression):
    def __init__(self, parent_function, target_variable, expression):
        Expression.__init__(self)
        self.parent_function = parent_function
        self.target_variable = target_variable
        self.expression = expression

    def _evaltype(self, resolver_stack):
        resolved_expr = self.expression.resolve(resolver_stack)
        return resolved_expr.evaltype(resolver_stack)

    def _resolve(self, resolver_stack):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve the target variable's binding.  This does'nt necessarily have
        # to evaluate types.
        # This will help us with type inference going backwards
        resolved_var = self.target_variable.resolve(resolver_stack)

        # Resolve all types in child expressions.  
        # Apart from just evaluating all child expressions, also make sure
        # Resolve field paths that should come from source type
        resolved_expr = self.expression.resolve(resolver_stack)
        return self

class ExpressionList(Expression):
    """ A list of statements. """
    def __init__(self, children = None):
        Expression.__init__(self)
        self.children = children or []

    def add(self, expr):
        self.children.append(expr)

    def _evaltype(self, resolver_stack):
        resolved = self.resolve(resolver_stack)
        return resolved.children[-1].evaltype(resolver_stack)

    def _resolve(self, resolver_stack):
        resolved_exprs = [expr.resolve(resolver_stack) for expr in self.children]
        if any(x != y for x,y in zip(self.children, resolved_exprs)):
            return ExpressionList(resolved_exprs)
        return self

class DictExpression(Expression):
    def __init__(self, values):
        super(DictExpression, self).__init__()
        self.values = values

    def _resolve(self, resolver_stack):
        ipdb.set_trace()
        for key,value in self.values.iteritems():
            key.resolve(resolver_stack)
            value.resolve(resolver_stack)

        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        return self

class ListExpression(Expression):
    def __init__(self, values):
        super(ListExpression, self).__init__()
        self.values = values

    def _evaltype(self, resolver_stack):
        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        return ListType.apply(tlcore.AnyType)

    def _resolve(self, resolver_stack):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        resolved_exprs = [expr.resolve(resolver_stack) for expr in self.values]
        if any(x != y for x,y in zip(self.values, resolved_exprs)):
            return ListExpression(resolved_exprs)
        return self

class TupleExpression(Expression):
    def __init__(self, values):
        super(TupleExpression, self).__init__()
        self.values = values or []

    def _evaltype(self, resolver_stack):
        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        return ListType.apply(tlcore.AnyType)

    def _resolve(self, resolver_stack):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        resolved_exprs = [expr.resolve(resolver_stack) for expr in self.values]
        if any(x != y for x,y in zip(self.values, resolved_exprs)):
            return TupleExpression(resolved_exprs)
        return self

class IfExpression(Expression):
    """ Conditional expressions are used to represent if-else expressions. """
    def __init__(self, cases, default_expression):
        super(IfExpression, self).__init__()
        self.cases = cases or []
        self.default_expression = default_expression or []

    def __repr__(self):
        return "<CondExp - ID: 0x%x>" % (id(self))

    def set_evaluated_typeexpr(self, vartype):
        assert False, "cannot set evaluated type of an If expression (yet)"

    def _resolve(self, resolver_stack):
        """ Resolves bindings and types in all child expressions. """
        ipdb.set_trace()
        assert self._evaluated_typeexpr == None, "Type has already been resolved, should not have been called twice."

        for condition, expr in self.cases:
            condition.resolve()
            expr.resolve()

        if self.default_expression: self.default_expression.resolve()

        # TODO: Return a union type instead
        self._evaluated_typeexpr = tlcore.VoidType
        return self
