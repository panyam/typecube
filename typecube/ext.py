
import ipdb
from typecube import core as tlcore
from typecube.core import Expr
from typecube.annotations import Annotatable

BooleanType = tlcore.make_atomic_type("boolean")
ByteType = tlcore.make_atomic_type("byte")
IntType = tlcore.make_atomic_type("int")
LongType = tlcore.make_atomic_type("long")
FloatType = tlcore.make_atomic_type("float")
DoubleType = tlcore.make_atomic_type("double")
StringType = tlcore.make_atomic_type("string")
MapType = tlcore.make_type_op("map", ["K", "V"], None, None)
ListType = tlcore.make_type_op("list", ["V"], None, None)

class MatchExp(Expr):
    def __init__(self, patterns, expr):
        self.patterns = patterns
        for pat in patterns: pat.parent = self
        self.expr = expr
        self.expr.parent = self

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
    def __init__(self, target, expr):
        Expr.__init__(self)
        self.expr = expr
        self.expr.parent = self
        self.target = target
        self.target.parent = self

    def beta_reduce(self, bindings):
        return Assignment(self.target.deepcopy, self.expr.beta_reduce(bindings))

    def _resolve(self):
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

class Module(Expr, Annotatable):
    def __init__(self, fqn, parent = None, annotations = None, docs = ""):
        Expr.__init__(self, parent)
        Annotatable.__init__(self, annotations, docs)
        self._fqn = fqn
        self._parent = parent 
        self.entity_map = {}
        self.child_entities = []
        self.aliases = {}

    @property
    def name(self):
        return self.fqn.split(".")[-1]

    def set_alias(self, name, fqn):
        """Sets the alias of a particular name to an FQN."""
        self.aliases[name] = fqn
        return self

    def find_fqn(self, fqn):
        """Looks for a FQN in either the aliases or child entities or recursively in the parent."""
        out = None
        curr = self
        while curr and not out:
            out = curr.aliases.get(fqn, None)
            if not out:
                out = curr.get(fqn)
            if not out:
                curr = curr.parent
        return out

    def _resolve_name(self, name, condition = None):
        # TODO - handle conditions here
        entry = self.find_fqn(name)
        while entry and type(entry) in (str, unicode):
            entry = self.find_fqn(entry)
        return entry

    def add(self, name, entity):
        """ Adds a new child entity. """
        assert name and name not in self.entity_map, "Child entity '%s' already exists" % name
        # Take ownership of the entity
        entity.parent = self
        self.entity_map[name] = entity
        self.child_entities.append(entity)

    def get(self, fqn_or_parts):
        """ Given a list of key path parts, tries to resolve the descendant entity that matchies this part prefix. """
        parts = fqn_or_parts
        if type(fqn_or_parts) in (unicode, str):
            parts = fqn_or_parts.split(".")
        curr = self
        for part in parts:
            if part not in curr.entity_map:
                return None
            curr = curr.entity_map[part]
        return curr

    @property
    def name(self): return self._name

    @property
    def parent(self): return self._parent

    def __json__(self, **kwargs):
        out = {}
        if self.fqn:
            out["fqn"] = self.fqn
        return out

    def ensure_module(self, fqn):
        """ Ensures that the module given by FQN exists from this module and is a Module object. """
        parts = fqn.split(".")
        curr = self
        total = None
        for part in parts:
            if not total: total = part
            else: total = total + "." + part
            if part not in curr.entity_map:
                curr.add(part, Module(total, curr))
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
