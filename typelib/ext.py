
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
MapType = tlcore.make_wrapper_type("map", ["K", "V"])
ArrayType = tlcore.make_wrapper_type("array", ["V"])

class Assignment(Expression):
    def __init__(self, parent_function, target_variable, expression, is_temporary = False):
        Expression.__init__(self)
        self.parent_function = parent_function
        self.target_variable = target_variable
        self.target_variable.is_temporary = is_temporary or target_variable.field_path.get(0) == '_'
        self.expression = expression
        if self.target_variable.is_temporary:
            assert target_variable.field_path.length == 1, "A temporary variable cannot have nested field paths"

    @property
    def is_temporary(self):
        return self.target_variable and self.target_variable.is_temporary

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        # Forbid changing of resolvers for now
        Expression.set_resolver(self, resolver)
        self.target_variable.set_resolver(resolver)
        self.expression.set_resolver(resolver)

    def resolve(self):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve the target variable's binding.  This does'nt necessarily have
        # to evaluate types.
        # This will help us with type inference going backwards
        if not self.is_temporary:
            self.target_variable.resolve()

        # Resolve all types in child expressions.  
        # Apart from just evaluating all child expressions, also make sure
        # Resolve field paths that should come from source type
        self.expression.resolve()

        if self.target_variable.is_temporary:
            varname = str(self.target_variable.field_path)
            if varname == "_":
                self.target_variable = None
            else:
                # Resolve field paths that should come from dest type
                self.target_variable.evaluated_typeexpr = self.expression.evaluated_typeexpr
                self.parent_function.register_temp_var(varname, self.expression.evaluated_typeexpr)
        self._evaluated_typeexpr = self.expression.evaluated_typeexpr
        return self

class ExpressionList(Expression):
    """ A list of statements. """
    def __init__(self, children = None):
        Expression.__init__(self)
        self.children = children or []

    def add(self, expr):
        self.children.append(expr)

    def set_resolver(self, resolver):
        Expression.set_resolver(self, resolver)
        for expr in self.children:
            expr.set_resolver(resolver)

    def resolve(self):
        for expr in self.children: expr.resolve()
        if self.children:
            self._evaluated_typeexpr = self.children[-1].evaluated_typeexpr
        else:
            self._evaluated_typeexpr = tlcore.VoidType
        return self

class LiteralExpression(Expression):
    """
    An expression that contains a literal value like a number, string, boolean, array, or map.
    """
    def __init__(self, value, value_type = None):
        super(LiteralExpression, self).__init__()
        self._resolved_value = self.value = value
        self.value_type = value_type
        self._evaluated_typeexpr = self.value_type

    def resolve(self): return self

    def __repr__(self):
        return "<Literal - ID: 0x%x, Value: %s>" % (id(self), str(self.value))

class DictExpression(Expression):
    def __init__(self, values):
        super(DictExpression, self).__init__()
        self.values = values

    def set_resolver(self, resolver):
        Expression.set_resolver(resolver)
        for key,value in self.values.iteritems():
            key.set_resolver(resolver)
            value.set_resolver(resolver)

    def resolve(self):
        for key,value in self.values.iteritems():
            key.resolve()
            value.resolve()

        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        self._evaluated_typeexpr = tlcore.TypeInitializer(MapType, tlcore.AnyType, tlcore.AnyType)
        self._evaluated_typeexpr.set_resolver(self.resolver)
        return self

class ListExpression(Expression):
    def __init__(self, values):
        super(ListExpression, self).__init__()
        self.values = values

    def set_resolver(self, resolver):
        Expression.set_resolver(self, resolver)
        for value in self.values:
            value.set_resolver(resolver)

    def resolve(self):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        for expr in self.values: expr.resolve()

        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        self._evaluated_typeexpr = tlcore.TypeInitializer(ArrayType, tlcore.AnyType)
        self._evaluated_typeexpr._resolver = self.resolver
        return self

class TupleExpression(Expression):
    def __init__(self, values):
        super(TupleExpression, self).__init__()
        self.values = values or []

    def set_resolver(self, resolver):
        Expression.set_resolver(resolver)
        for value in self.values:
            value.set_resolver(resolver)

    def resolve(self):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        for expr in self.values: expr.resolve()

        # TODO - Unify the types of child expressions and find the tightest type here Damn It!!!
        self._evaluated_typeexpr = tlcore.TypeInitializer(TupleType, tlcore.AnyType)
        self._evaluated_typeexpr._resolver = self.resolver
        return self

class IfExpression(Expression):
    """ Conditional expressions are used to represent if-else expressions. """
    def __init__(self, cases, default_expression):
        super(IfExpression, self).__init__()
        self.cases = cases or []
        self.default_expression = default_expression or []

    def set_resolver(self, resolver):
        Expression.set_resolver(self, resolver)
        if self.default_expression:
            self.default_expression.set_resolver(resolver)

        for condition, stmt_block in self.cases:
            condition.set_resolver(resolver)
            stmt_block.set_resolver(resolver)

    def __repr__(self):
        return "<CondExp - ID: 0x%x>" % (id(self))

    def set_evaluated_typeexpr(self, vartype):
        assert False, "cannot set evaluated type of an If expression (yet)"

    def resolve(self):
        """ Resolves bindings and types in all child expressions. """
        assert self._evaluated_typeexpr == None, "Type has already been resolved, should not have been called twice."

        for condition, expr in self.cases:
            condition.resolve()
            expr.resolve()

        if self.default_expression: self.default_expression.resolve()

        # TODO: Return a union type instead
        self._evaluated_typeexpr = tlcore.VoidType
        return self
