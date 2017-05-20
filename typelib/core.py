
from collections import defaultdict
import ipdb
from utils import ensure_types
from typelib import errors as tlerrors
from typelib.annotations import Annotatable

def istypeexpr(expr):
    return issubclass(expr.__class__, TypeExpression)

class TypeExpression(object):
    """ An expressions which results in a type or a type expression. 
    This is the window to all types that are either available or must be lazily evaluated.
    """
    def __init__(self):
        # The symbol resolver is responsible for resolving names that an expression refers to.
        # Note that this does not prohibit any form of late binding as the assumption is that 
        # the scope where an expression exists, usually refers to some environment that should
        # have interface declarations (via the resolver) of types it refers to.
        self.resolver = None

    @property
    def signature(self, visited = None):
        assert False, "Not Implemented"

    def resolve(self, sym_resolver):
        """ This method resolves a type expression to a type object. """
        assert False, "Not Implemented"

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        assert self.resolver is None
        self.resolver = resolver

class TypeVariable(TypeExpression):
    """ A type variable used in a type expression. """
    def __init__(self, fqn):
        TypeExpression.__init__(self)
        self.fqn = fqn

    @property
    def signature(self, visited = None):
        return self.fqn

    def resolve(self, sym_resolver):
        """ This method resolves a type expression to a type object. """
        assert False, "Not Implemented"
        value = sym_resolver.find(self.fqn)
        assert istypeexpr(value)
        while not value.is_resolved:
            value = value.resolve(sym_resolver)
        return value

class TypeFunction(TypeExpression, Annotatable):
    def __init__(self, constructor, name, type_params, type_args, parent, annotations = None, docs = ""):
        """
        Creates a new type function.  Type functions are responsible for creating concrete type instances
        or other (curried) type functions.

        Params:
            constructor     The type's constructor, eg "record", "int" etc.  This is not the name 
                            of the type itself but a name that indicates a class of this type.
            name            Name of the type.
            type_params     Parameters for the type.  This is of type array<TypeParam>.
            type_args       Type arguments are fields/children of a given type and are themselves expressions
                            over either type_params or unbound variables or other type expressions.
            parent          A reference to the parent container entity of this type.
            annotations     Annotations applied to the type.
            docs            Documentation string for the type.
        """
        Annotatable.__init__(self, annotations = annotations, docs = docs)
        TypeExpression.__init__(self)

        if type(constructor) not in (str, unicode):
            raise tlerrors.TLException("constructor must be a string")

        self.constructor = constructor
        self.parent = parent
        self.name = name
        self._type_params = type_params
        self.args = TypeArgList(type_args)
        self._signature = None

    def set_resolver(self, resolver):
        """ Resolver for children with this function.  This will give them a chance
        to resolve to parameters before globals are searched.
        """
        TypeExpression.set_resolver(self, resolver)
        for arg in self.args:
            arg.type_expr.set_resolver(self)

    def resolve(self, sym_resolver):
        """ This method resolves a type expression to a type object. """
        assert False, "Not Implemented"
        value = sym_resolver.find(self.fqn)
        assert istypeexpr(value)
        while not value.is_resolved:
            value = value.resolve(sym_resolver)
        return value

    @property
    def signature(self, visited = None):
        if not self._signature:
            if visited is None: visited = set()
            self._signature = self.constructor
            if self.name: self._signature += ":" + self.name
            if self._type_args:
                self._signature += "(" + ", ".join([t.type_expr.signature for t in self._type_args]) + ")"
        return self._signature

    @property
    def type_params(self): return self._type_params

    def __json__(self, **kwargs):
        out = {}
        if self.name:
            out["name"] = self.name
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if not kwargs.get("no_cons", False):
            out["type"] = self.constructor
        if self.args:
            out["args"] = [arg.json(**kwargs) for arg in self.args]
        return out
    
class TypeInitializer(TypeExpression):
    def __init__(self, type_func_name, *type_exprs):
        # The name of the type function which will initialize the new type, eg the "map" in map<int, string>
        # This name may be pointing to an unresolved type so this will have to be resolved before
        # a type function is determined
        TypeExpression.__init__(self)
        self.type_func_name = type_func_name
        self.type_function = None

        # Each type expression should (eventually) resolve to a Type and will be bound to the respective type.
        self.type_exprs = type_exprs
        self._signature = None

    @property
    def signature(self, visited = None):
        if not self._signature:
            if visited is None: visited = set()
            self._signature = self.type_func_name
            if self.type_exprs:
                self._signature += "<" + ', '.join(t.signature(visited) for t in self.type_exprs) + ">"
        return self._signature

    def resolve(self, sym_resolver):
        """ Resolves all argument expressions and then substitutes the resolved argument into args of the type function. """
        self.type_function = sym_resolver.find_type_function(self.type_func_name)
        for expr in self.type_exprs:
            if expr:
                expr.resolve(sym_resolver)
                assert resolved_type is not None

class TypeRef(Annotatable):
    def __init__(self, name, type_params, type_expr, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.name = name
        self.type_params = type_params

class TypeArg(Annotatable):
    """ A type argument is a child of a given type.  Akin to a member/field of a type.
    These are either names of a type (yet to be bound) or another TypeFunction that 
    must be evaluated to create the type of this argument, or a TypeInitializer
    """
    def __init__(self, name, type_expr, is_optional = False, default_value = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        assert istypeexpr(type_expr), "TypeExpr type = '%s'" % str(type(type_expr))
        self.name = name
        self.type_expr = type_expr
        self.is_optional = is_optional
        self.default_value = default_value or None

class TypeArgList(object):
    """ A list of type args for a particular type container. """
    def __init__(self, type_args):
        self._type_args = []
        for type_arg in type_args or []:
            self.add(type_arg)

    def __getitem__(self, slice):
        return self._type_args.__getitem__(slice)

    def __iter__(self): return iter(self._type_args)

    def __len__(self): return len(self._type_args)

    @property
    def count(self): return len(self._type_args)

    def index_for(self, name):
        for i,arg in enumerate(self._type_args):
            if arg.name == name:
                return i
        return -1

    def arg_for(self, name):
        return self.arg_at(self.index_for(name))

    def arg_at(self, index):
        return None if index < 0 else self._type_args[index]

    def contains(self, name):
        return self.index_for(name) >= 0

    def add(self, arg):
        """
        Add an argument type.
        """
        if istypeexpr(arg):
            arg = TypeArg(None, arg)
        elif not isinstance(arg, TypeArg):
            raise tlerrors.TLException("Argument must be a TypeArg. Found: '%s'" % type(arg))

        if arg.name:
            index = self.index_for(arg.name)
            if index >= 0:
                raise tlerrors.TLException("Child type by the given name '%s' already exists" % arg.name)
        self._type_args.append(arg)

def make_type(constructor, name, type_params, type_args, parent = None, annotations = None, docs = ""):
    return TypeFunction(constructor, name, type_params = type_params, type_args = type_args,
                        parent = parent, annotations = annotations, docs = docs)

def make_literal_type(name, parent = None, annotations = None, docs = ""):
    return make_type("literal", name, type_params = None, type_args = None,
                     parent = parent, annotations = annotations, docs = docs)

def make_wrapper_type(name, type_params, parent = None, annotations = None, docs = ""):
    type_args = [TypeArg(None, TypeVariable(param)) for param in type_params]
    return TypeFunction("extern", newtyperef.name, type_params = type_params, type_args = type_args,
                        parent = parent, annotations = annotations, docs = docs)

def make_func_type(name, type_params, type_args, output_arg, parent = None, annotations = None, docs = ""):
    return TypeFunction("function", name, type_params = type_params, type_args = type_args + [output_arg],
                        parent = parent, annotations = annotations, docs = docs)

AnyType = make_literal_type("any")
VoidType = make_literal_type("void")
