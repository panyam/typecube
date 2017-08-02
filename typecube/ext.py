
from ipdb import set_trace
from typecube import core as tlcore
from typecube.core import Expr, Var
from typecube.annotations import Annotatable

BooleanType = tlcore.make_atomic_type("boolean")
ByteType = tlcore.make_atomic_type("byte")
IntType = tlcore.make_atomic_type("int")
LongType = tlcore.make_atomic_type("long")
FloatType = tlcore.make_atomic_type("float")
DoubleType = tlcore.make_atomic_type("double")
StringType = tlcore.make_atomic_type("string")
MapType = tlcore.make_type_op("map", ["K", "V"], None)
ListType = tlcore.make_type_op("list", ["V"], None)

class Macro(Expr):
    """ Macros are expressions that combine other expressions to create
    new syntactic forms.  This is no more powerful than plain Abstractions
    and Applications but let us extend other constructs (like loops, 
    switch cases, conditionals, pattern matching and so on).
    """
    def __init__(self):
        Expr.__init__(self)

    def infer_type(self):
        """ Called to infer the type of this expression based on its
        child expression structure. """
        pass

class MatchExp(Expr):
    def __init__(self, patterns, expr):
        self.patterns = patterns
        self.expr = expr

class NewExpr(Expr):
    """ An expression used to create instead of a type.  It can be passed values for its child arguments.
    This is just another shortcut for a function appication of a specific kind.
    """
    def __init__(self, objtype, **arg_values):
        self.objtype = objtype
        self.arg_values = arg_values or {}

    def _reduce(self):
        resolved_objtype = self.objtype.resolve()
        resolved_args = {key: value.resolve() for key,value in self.arg_values.iteritems()}
        return self

class Index(Expr):
    """ A projection of either an index or a key into an expression. """
    def __init__(self, expr, key):
        Expr.__init__(self)
        self.expr = expr
        self.key = key

    @property
    def clone(self):
        return Index(self.expr.clone(), self.key)

    def _reduce(self):
        return Index(self.expr.resolve(), self.key)

    def beta_reduce(self, bindings):
        return Index(self.expr.beta_reduce(bindings), self.key)

class Assignment(Expr):
    def __init__(self, target, expr, is_temporary):
        Expr.__init__(self)
        self.expr = expr
        self.target = target

    def beta_reduce(self, bindings):
        return Assignment(self.target.clone(), self.expr.beta_reduce(bindings))

    def _reduce(self):
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

    def beta_reduce(self, bindings):
        return ExprList([c.beta_reduce(bindings) for c in self.children])

    def add(self, expr):
        if not issubclass(expr.__class__, Expr):
            ipdb.set_trace()
            assert issubclass(expr.__class__, Expr), "Cannot add non Expr instances to an ExprList"
        self.children.append(expr)

    def extend(self, another):
        if type(another) is ExprList:
            self.children.extend(another.children)
        else:
            self.add(another)

    def _reduce(self):
        resolved_exprs = [expr.resolve() for expr in self.children]
        if any(x != y for x,y in zip(self.children, resolved_exprs)):
            return ExprList(resolved_exprs)
        return self

class DictExpr(Expr):
    def __init__(self, keys, values):
        super(DictExpr, self).__init__()
        self.keys = keys
        self.values = values
        assert len(keys) == len(values)

    def beta_reduce(self, bindings):
        return DictExpr([k.beta_reduce(bindings) for k in self.keys], [v.beta_reduce(bindings) for v in self.values])

    def _reduce(self):
        for key,value in izip(self.keys, self.values):
            key.resolve()
            value.resolve()

        # TODO - Unify the types of child exprs and find the tightest type here Damn It!!!
        return self

class ListExpr(Expr):
    def __init__(self, values):
        super(ListExpr, self).__init__()
        self.values = values

    def beta_reduce(self, bindings):
        return ListExpr([v.beta_reduce(bindings) for v in self.values])

    def _reduce(self):
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

    def beta_reduce(self, bindings):
        return ListExpr([v.beta_reduce(bindings) for v in self.values])

    def _reduce(self):
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

    def __repr__(self):
        return "<IfExp - ID: 0x%x>" % (id(self))

    def set_evaluated_typeexpr(self, vartype):
        assert False, "cannot set evaluated type of an If expr (yet)"

    def _reduce(self):
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

class Module(Expr):
    def __init__(self, fqn):
        Expr.__init__(self)
        self.fqn = fqn
        self.entity_map = {}
        self.child_entities = []
        self.aliases = {}

    @property
    def name(self):
        return self.fqn.split(".")[-1]

    def set_alias(self, name, fqn):
        """Sets the alias of a particular name to an FQN."""
        self.aliases[name] = Var(fqn)
        return self

    def resolve_name(self, name):
        return self.get(name)

    def add(self, name, entity):
        """ Adds a new child entity. """
        assert name and name not in self.entity_map, "Child entity '%s' already exists" % name
        # Take ownership of the entity
        self.entity_map[name] = entity
        self.child_entities.append(entity)

    def get(self, fqn_or_parts):
        """ Given a list of key path parts, tries to resolve the descendant entity that matchies this part prefix. """
        parts = fqn_or_parts
        if type(fqn_or_parts) in (unicode, str):
            parts = fqn_or_parts.split(".")
        curr = self
        for part in parts:
            if part in self.aliases:
                curr = self.aliases.get(part)
            elif part in curr.entity_map:
                curr = curr.entity_map[part]
            else:
                return None
        return curr

    def ensure_module(self, fqn):
        """ Ensures that the module given by FQN exists from this module and is a Module object. """
        parts = fqn.split(".")
        curr = self
        total = None
        for part in parts:
            if not total: total = part
            else: total = total + "." + part
            if part not in curr.entity_map:
                curr.add(part, Module(total))
            curr = curr.get(part)
            assert type(curr) is Module
        return curr

    def debug_show(self, level = 0):
        print ("  " * (level)) + "Module:"
        print ("  " * (level + 1)) + "Children:"
        for key,value in self.entity_map.iteritems():
            print ("  " * (level + 2)) + ("%s: %s" % (key, value))
        print ("  " * (level + 1)) + "Aliases:"
        for key,value in self.aliases.iteritems():
            print ("  " * (level + 2)) + ("%s: %s" % (key, value))
