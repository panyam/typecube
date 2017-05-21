
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
        self._resolved_value = None

    @property
    def resolved_value(self):
        if self._resolved_value is None:
            if self.resolver is None:
                ipdb.set_trace()
            assert self.resolver is not None
            self._resolved_value = self.resolve()
            if not self._resolved_value or not type(self._resolved_value) in (TypeParam, TypeFunction):
                ipdb.set_trace()
                assert False, "Invalid resolved value type: '%s'" % repr(self._resolved_value)
        return self._resolved_value

    def signature(self, visited = None):
        assert False, "Not Implemented"

    def resolve(self):
        """ This method resolves a type expression to a type object. """
        assert False, "Not Implemented"
        return None

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        if self.resolver:
            ipdb.set_trace()
        assert self.resolver is None
        self.resolver = resolver

class TypeParam(TypeExpression):
    def __init__(self, name, parent):
        TypeExpression.__init__(self)
        self.name = name
        self.parent = parent

    def __repr__(self):
        return "<TypeParam(%d) - %s>" % (id(self), self.name)

    def signature(self, visited = None):
        return self.name

    def resolve(self):
        # A type parameter can only resolve to itself - and only be replaced upon a substitution
        return self

class TypeName(TypeExpression):
    """ A type variable used in a type expression. """
    def __init__(self, fqn):
        TypeExpression.__init__(self)
        self.fqn = fqn

    def __repr__(self):
        return "<TypeName(%d) - %s>" % (id(self), self.fqn)

    def signature(self, visited = None):
        return self.fqn

    def resolve(self):
        """ This method resolves a type expression to a type object. """
        value = self.resolver.resolve_type_name(self.fqn)
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
        self._type_params = type_params or []
        assert all(type(x) in (str, unicode) for x in self._type_params)
        self.args = TypeArgList(type_args)
        self._signature = None

    # def __repr__(self): return "<TypeFunc(%d) - %s/%s<%s>, Args: %s>" % (id(self), self.constructor, self.name, ",".join(self.type_params), map(repr, self.args))

    @property
    def is_concrete(self):
        return len(self._type_params) == 0 and all(self.args)

    def resolve_type_name(self, name):
        if name in self.type_params:
            return TypeParam(name, self)

        # if we cannot bind to a var then send to parent
        # This may change if we allow inner types (but is that really a "child" type or 
        # just something lexically scoped but semnatically stored somewhere else?)
        return self.resolver.resolve_type_name(name)

    def set_resolver(self, resolver):
        """ Resolver for children with this function.  This will give them a chance
        to resolve to parameters before globals are searched.
        """
        TypeExpression.set_resolver(self, resolver)
        for arg in self.args:
            arg.type_expr.set_resolver(self)

    def resolve(self):
        # A TypeFunction resolves to itself
        for index,arg in enumerate(self.args):
            arg.type_expr.resolved_value
        return self

    def apply(self, type_exprs, ignore = None):
        """ Applies the type expressions to the parameters to reify this type function. """
        assert len(self.type_params) == len(type_exprs), "TypeFunction '%s<%s>' expects %d parameters, but found %d" % (self.name,
                ", ".join(self.type_params), len(self.type_params), len(type_exprs))

        # All substitutions to be applied to the params in this type function
        subst = {}
        new_type_args = []
        new_type_params = []
        for name,expr in zip(self.type_params, type_exprs):
            if expr:
                subst[name] = expr
            else:
                # This param still remains
                new_type_params.append(name)

        # If children have param names that match those in this func's param list 
        # then those should be skipped from conversion as those params would have
        # their own bindings.
        if ignore is None:
            ignore = defaultdict(int)
        for index,arg in enumerate(self.args):
            resolved_value = arg.type_expr.resolved_value
            if type(resolved_value) is TypeParam:
                # if this is a param bound to this function then we are good to go
                # we can make this substitution
                newarg = arg
                if resolved_value.name not in ignore:
                    # Make the substitution
                    expr = arg.type_expr
                    if arg.name:
                        if arg.name in subst:
                            expr = subst[arg.name]
                    else:
                        if type_exprs[index] is not None:
                            expr = type_exprs[index]
                    newarg = TypeArg(arg.name, expr, arg.is_optional, arg.default_value, arg.annotations, arg.docs)
                new_type_args.append(newarg)
            elif type(resolved_value) is TypeFunction:
                ipdb.set_trace()
                b = 0
            else:
                ipdb.set_trace()
                c = 0
        return TypeFunction(self.constructor, self.name, new_type_params, new_type_args, self.parent, self.annotations, self.docs)

    def signature(self, visited = None):
        if not self._signature:
            if visited is None: visited = set()
            self._signature = self.constructor
            if self.name: self._signature += ":" + self.name
            if self.args:
                self._signature += "(" + ", ".join([t.type_expr.signature(visited) for t in self.args]) + ")"
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
    def __init__(self, type_func_or_name, type_exprs):
        # The name of the type function which will initialize the new type, eg the "map" in map<int, string>
        # This name may be pointing to an unresolved type so this will have to be resolved before
        # a type function is determined
        TypeExpression.__init__(self)
        if type(type_func_or_name) is TypeFunction:
            self.type_func_name = type_func_or_name.name
            self.type_function = type_func_or_name
        else:
            self.type_func_name = type_func_or_name
            self.type_function = None

        # Each type expression should (eventually) resolve to a Type and will be bound to the respective type.
        if type(type_exprs) is not list:
            type_exprs = [type_exprs]
        self.type_exprs = type_exprs
        self._signature = None

    def __repr__(self):
        return "<TypeInit(%d) - Func: %s, Exprs: [%s]>" % (id(self), self.type_func_name, ", ".join(map(repr, self.type_exprs)))

    @property
    def signature(self, visited = None):
        if not self._signature:
            if visited is None: visited = set()
            self._signature = self.type_func_name
            if self.type_exprs:
                self._signature += "<" + ', '.join(t.signature(visited) for t in self.type_exprs) + ">"
        return self._signature

    def resolve(self):
        """ Resolves all argument expressions and then substitutes the resolved argument into args of the type function. """
        if self.type_function is None:
            self.type_function = self.resolver.resolve_type_name(self.type_func_name)
        assert self.type_function is not None, "Could not resolve type: '%s'" % self.type_func_name
        assert self.type_function.resolved_value is not None
        for expr in self.type_exprs:
            if expr:
                assert expr.resolved_value is not None
        return self.type_function.apply(self.type_exprs)

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        TypeExpression.set_resolver(self, resolver)
        for expr in self.type_exprs:
            if expr:
                expr.set_resolver(resolver)

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

    def __json__(self, **kwargs):
        out = {}
        if self.name:
            out["name"] = self.name
        return out
        
    # def __repr__(self): return "<TypeArg(%d) - Name: %s>" % (id(self), self.name)

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

    def withname(self, name):
        return self.atindex(self.index_for(name))

    def atindex(self, index):
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
    type_args = [TypeName(param) for param in type_params]
    return TypeFunction("extern", name, type_params = type_params, type_args = type_args,
                        parent = parent, annotations = annotations, docs = docs)

def make_func_type(name, type_params, type_args, output_arg, parent = None, annotations = None, docs = ""):
    return TypeFunction("function", name, type_params = type_params, type_args = type_args + [output_arg],
                        parent = parent, annotations = annotations, docs = docs)

def make_typeref(name, type_params, type_expr, parent = None, annotations = None, docs = ""):
    return make_type("typeref", name, type_params = type_params, type_args = [type_expr],
                     parent = parent, annotations = annotations, docs = docs)

AnyType = make_literal_type("any")
VoidType = make_literal_type("void")
