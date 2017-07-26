
import ipdb
from typecube import core as tlcore
from typecube.core import Expr
from typecube.annotations import Annotatable
from typecube import unifier as tlunifier
from typecube.utils import FieldPath

BooleanType = tlcore.make_atomic_type("boolean")
ByteType = tlcore.make_atomic_type("byte")
IntType = tlcore.make_atomic_type("int")
LongType = tlcore.make_atomic_type("long")
FloatType = tlcore.make_atomic_type("float")
DoubleType = tlcore.make_atomic_type("double")
StringType = tlcore.make_atomic_type("string")
MapType = tlcore.make_type_op("map", ["K", "V"], None, None)
ListType = tlcore.make_type_op("list", ["V"], None, None)


class NewExpr(Expr):
    """ An expression used to create instead of a type.  It can be passed values for its child arguments.
    This is just another shortcut for a function appication of a specific kind.
    """
    def __init__(self, objtype, **arg_values):
        self.objtype = objtype
        self.arg_values = arg_values or {}
        for expr in arg_values.iteritems(): expr.parent = self

    def _resolve(self):
        resolved_objtype = self.objtype.resolve()
        resolved_args = {key: value.resolve() for key,value in self.arg_values.iteritems()}
        return self

class Index(Expr):
    """ A projection of either an index or a key into an expression. """
    def __init__(self, expr, key):
        Expr.__init__(self)
        self.expr = expr
        self.key = key
        self.expr.parent = self

    @property
    def deepcopy(self):
        return Index(self.expr.deepcopy, self.key)

    def _resolve(self):
        return Index(self.expr.resolve(), self.key)

    def beta_reduce(self, bindings):
        return Index(self.expr.beta_reduce(bindings), self.key)

class Assignment(Expr):
    def __init__(self, target_variable, expr):
        Expr.__init__(self)
        self.target_variable = target_variable
        self.expr = expr
        self.target_variable.parent = self
        self.expr.parent = self

    def beta_reduce(self, bindings):
        return Assignment(self.target_variable.deepcopy, self.expr.beta_reduce(bindings))

    def _resolve(self):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve the target variable's binding.  This does'nt necessarily have
        # to evaluate types.
        # This will help us with type inference going backwards
        resolved_var = self.target_variable.resolve()

        # Resolve all types in child exprs.  
        # Apart from just evaluating all child exprs, also make sure
        # Resolve field paths that should come from source type
        resolved_expr = self.expr.resolve()
        return self

class Literal(Expr):
    """
    An expr that contains a literal value like a number, string, boolean, list, or map.
    """
    def __init__(self, value, value_type):
        Expr.__init__(self)
        self.value = value
        self.value_type = value_type

    def beta_reduce(self, bindings):
        return Literal(self, value, self.value_type)

    def resolve(self, resolver):
        return self

    def __repr__(self):
        return "<Literal(0x%x), Value: %s>" % (id(self), str(self.value))

class ExprList(Expr):
    """ A list of statements. """
    def __init__(self, children = None):
        Expr.__init__(self)
        self.children = children or []
        for expr in self.children: expr.parent = self

    def beta_reduce(self, bindings):
        return ExprList([c.beta_reduce(bindings) for c in self.children])

    def add(self, expr):
        if not issubclass(expr.__class__, Expr):
            ipdb.set_trace()
            assert issubclass(expr.__class__, Expr), "Cannot add non Expr instances to an ExprList"
        self.children.append(expr)
        expr.parent = self

    def extend(self, another):
        if type(another) is ExprList:
            self.children.extend(another.children)
            for expr in children: expr.parent = self
        else:
            self.add(another)

    def _resolve(self):
        resolved_exprs = [expr.resolve() for expr in self.children]
        if any(x != y for x,y in zip(self.children, resolved_exprs)):
            return ExprList(resolved_exprs)
        return self

class DictExpr(Expr):
    def __init__(self, keys, values):
        super(DictExpr, self).__init__()
        self.keys = keys
        self.values = values
        for expr in keys: expr.parent = self
        for expr in values: expr.parent = self
        assert len(keys) == len(values)

    def beta_reduce(self, bindings):
        return DictExpr([k.beta_reduce(bindings) for k in self.keys], [v.beta_reduce(bindings) for v in self.values])

    def _resolve(self):
        for key,value in izip(self.keys, self.values):
            key.resolve()
            value.resolve()

        # TODO - Unify the types of child exprs and find the tightest type here Damn It!!!
        return self

class ListExpr(Expr):
    def __init__(self, values):
        super(ListExpr, self).__init__()
        self.values = values
        for expr in values: expr.parent = self

    def beta_reduce(self, bindings):
        return ListExpr([v.beta_reduce(bindings) for v in self.values])

    def _resolve(self):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        resolved_exprs = [expr.resolve() for expr in self.values]
        if any(x != y for x,y in zip(self.values, resolved_exprs)):
            return ListExpr(resolved_exprs)
        return self

class TupleExpr(Expr):
    def __init__(self, values):
        super(TupleExpr, self).__init__()
        self.values = values or []
        for expr in values: expr.parent = self

    def beta_reduce(self, bindings):
        return ListExpr([v.beta_reduce(bindings) for v in self.values])

    def _resolve(self):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        resolved_exprs = [expr.resolve() for expr in self.values]
        if any(x != y for x,y in zip(self.values, resolved_exprs)):
            return TupleExpr(resolved_exprs)
        return self

class IfExpr(Expr):
    """ Conditional exprs are used to represent if-else exprs. """
    def __init__(self, cases, default_expr):
        super(IfExpr, self).__init__()
        self.cases = cases or []
        self.default_expr = default_expr or []
        for condition, expr in self.cases:
            condition.parent = self
            expr.parent = self
        if default_expr: default_expr.parent = self

    def __repr__(self):
        return "<IfExp - ID: 0x%x>" % (id(self))

    def set_evaluated_typeexpr(self, vartype):
        assert False, "cannot set evaluated type of an If expr (yet)"

    def _resolve(self):
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
