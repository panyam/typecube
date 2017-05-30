
import ipdb
from collections import defaultdict
from itertools import izip
from typelib import errors
from typelib.utils import FieldPath
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier

class Expression(object):
    """
    Parent of all expressions.  All expressions must have a value.  Expressions only appear in functions.
    """
    def __init__(self):
        self._evaluated_typeexpr = None
        self.resolver = None
        self.parent_function = None
        self._resolved_value = None

    @property
    def evaluated_typeexpr(self):
        """ Every expressions must evaluate a type expression that will result in the expression's type. """
        if not self._evaluated_typeexpr:
            raise errors.TLException("Type checking failed for '%s'" % repr(self))
        return self._evaluated_typeexpr

    @evaluated_typeexpr.setter
    def evaluated_typeexpr(self, typeexpr):
        self.set_evaluated_typeexpr(typeexpr)

    def set_resolver(self, resolver, parent_function):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        if self.resolver:
            ipdb.set_trace()
            assert False, "Resolver has been set.  Cannot be set again."
        self.resolver = resolver
        self.parent_function = parent_function

    @property
    def resolved_value(self):
        if self._resolved_value is None:
            if self.resolver is None:
                ipdb.set_trace()
            assert self.resolver is not None
            self._resolved_value = self.resolve()
            self.resolution_finished()
        return self._resolved_value

    def resolve(self):
        """ This method resolves a type expression to a type object. """
        assert False, "Not Implemented"
        return self

    def resolve_type_name(self, name):
        return self.resolver.resolve_type_name(name)

    def resolve_name(self, name):
        return None if not self.resolver else self.resolver.resolve_name(name)

class Variable(Expression):
    """ An occurence of a name that can be bound to a value, a field or a type. """
    def __init__(self, field_path):
        super(Variable, self).__init__()
        # Whether we are a temporary local var
        self.is_temporary = False
        # Whether a resolved value is a function
        self.is_function = False
        if type(field_path) in (str, unicode):
            field_path = FieldPath(field_path)
        self.field_path = field_path
        self.root_value = None
        if type(field_path) is not FieldPath or field_path.length == 0:
            ipdb.set_trace()
        assert type(field_path) is FieldPath and field_path.length > 0

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.field_path))

    def set_evaluated_typeexpr(self, typeexpr):
        if self.is_temporary:
            self._evaluated_typeexpr = typeexpr
        else:
            assert False, "cannot set evaluted type of a non local var: %s" % self.field_path

    def resolve(self):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        first, field_path_tail = self.field_path.pop()
        self.is_temporary = self.is_temporary or first == "_"
        if first == "_":
            self.is_temporary = True
            self._evaluated_typeexpr = VoidType
        else:
            # See which of the params we should bind to
            var_typearg = self.resolver.resolve_name(first)

            if var_typearg:
                self.root_value = var_typearg
                self._evaluated_typeexpr = var_typearg.type_expr
                if field_path_tail.length > 0:
                    curr_typearg = var_typearg
                    for i in xrange(field_path_tail.length):
                        part = field_path_tail.get(i)
                        next_typearg = curr_typearg.type_expr.resolved_value.args.withname(part)
                        curr_typearg = next_typearg
                    resolved_value = curr_typearg
                    self._evaluated_typeexpr = resolved_value.type_expr
            else:
                # Check if this is actually referring to a function and not a member
                if self.field_path.length != 1:
                    ipdb.set_trace()
                assert self.field_path.length == 1
                fname = self.field_path.get(0)
                self.is_function = True
                self.root_value = resolved_value = self.resolver.resolve_name(fname)
                if type(resolved_value) is not Function:
                    ipdb.set_trace()
                self._evaluated_typeexpr = resolved_value.func_type
        return self

class Function(Expression, Annotatable):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, name, func_type, parent, annotations = None, docs = ""):
        Expression.__init__(self)
        Annotatable.__init__(self, annotations, docs)
        self.parent = parent
        self.name = name
        self.func_type = func_type
        self.expression = None
        self.is_external = False
        self.dest_varname = "dest" if func_type else None
        self.temp_variables = {}

    def set_resolver(self, resolver, parent_function):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        Expression.set_resolver(self, resolver, self)
        self.func_type.set_resolver(self, self)
        if self.expression:
            self.expression.set_resolver(self, self)

    @property
    def fqn(self):
        out = self.name
        if self.parent and self.parent.fqn:
            if out is None:
                ipdb.set_trace()
            out = self.parent.fqn + "." + out
        return out or ""

    def __repr__(self):
        return "<Function(0x%x) %s>" % (id(self), self.name)

    def resolve_name(self, name):
        """ Try to resolve a name to a local, source or destination variable. """
        # Check source types
        for src_typearg in self.source_typeargs:
            if src_typearg.name == name:
                return src_typearg

        # Check dest type
        if self.dest_varname == name:
            return self.dest_typearg

        # Check local variables
        if self.is_temp_variable(name):
            return self.temp_var_type(name)

        return None

    @property
    def source_typeargs(self):
        return self.func_type.args[:-1]

    @property
    def dest_typearg(self):
        out = self.func_type.args[-1]
        if out.type_expr.resolved_value == VoidType:
            return None
        return out

    @property
    def returns_void(self):
        dest_typearg = self.func_type.args[-1]
        return dest_typearg is None or dest_typearg.type_expr.resolved_value == VoidType

    def matches_input(self, input_typeexprs):
        """Tells if the input types can be accepted as argument for this transformer."""
        assert type(input_typeexprs) is list
        if len(input_typeexprs) != len(self.source_typeargs):
            return False
        return all(tlunifier.can_substitute(st.type_expr, it) for (st,it) in izip(self.source_typeargs, input_typeexprs))

    def matches_output(self, output_typeexpr):
        return tlunifier.can_substitute(output_typeexpr, self.dest_typearg.type_expr)

    def is_temp_variable(self, varname):
        return varname in self.temp_variables

    def temp_var_type(self, varname):
        return self.temp_variables[str(varname)]

    def register_temp_var(self, varname, vartype):
        assert type(varname) in (str, unicode)
        if varname in (x.name for x in self.func_type.args):
            raise TLException("Duplicate temporary variable '%s'.  Same as source." % varname)
        elif varname == self.dest_varname:
            raise TLException("Duplicate temporary variable '%s'.  Same as target." % varname)
        elif self.is_temp_variable(varname) and self.temp_variables[varname] is not None:
            raise TLException("Duplicate temporary variable declared: '%s'" % varname)
        self.temp_variables[varname] = vartype

    def resolve(self):
        """
        The main resolver method.  This should take care of the following:

            1. Ensure field paths are correct
            2. All expressions have their evaluated types set
        """
        # Now resolve all field paths appropriately
        self.expression.resolve()
        return self

class FunctionCall(Expression):
    """
    An expression for denoting a function call.  Function calls can only be at the start of a expression stream, eg;

    f(x,y,z) => H => I => J

    but the following is invalid:

    H => f(x,y,z) -> J

    because f(x,y,z) must return an observable and observable returns are not supported (yet).
    """
    def __init__(self, func_expr, func_param_exprs = None, func_args = None):
        super(FunctionCall, self).__init__()
        self.func_expr = func_expr
        self.func_params = func_param_exprs
        self.func_args = func_args

    def set_resolver(self, resolver, parent_function):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        Expression.set_resolver(self, resolver, parent_function)
        self.func_expr.set_resolver(resolver, parent_function)
        for arg in self.func_args:
            arg.set_resolver(resolver, parent_function)
        for param in self.func_params:
            param.set_resolver(resolver, parent_function)

    def resolve(self):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # First resolve the expression to get the source function
        self.func_expr.resolve()

        func_type = self.func_expr.root_value.func_type
        if not func_type:
            raise errors.TLException("Function '%s' is undefined" % self.func_ref.name)

        # Each func param is a type expression
        for arg in self.func_params:
            arg.resolved_value

        # Each of the function arguments is either a variable or a value.  
        # If it is a variable expression then it needs to be resolved starting from the
        # parent function that holds this statement (along with any other locals and upvals)
        for arg in self.func_args:
            arg.resolve()

        if len(self.func_args) != func_type.args.count - 1:
            ipdb.set_trace()
            raise errors.TLException("Function '%s' takes %d arguments, but encountered %d" %
                                            (parent_function.fqn, func_type.args.count - 1, len(self.func_args)))

        for i in xrange(0, len(self.func_args)):
            arg = self.func_args[i]
            peg_type = arg.evaluated_typeexpr.resolved_value
            hole_type = func_type.args.atindex(i).type_expr.resolved_value
            if not tlunifier.can_substitute(peg_type, hole_type):
                ipdb.set_trace()
                raise errors.TLException("Argument at index %d expected (hole) type (%s), found (peg) type (%s)" % (i, hole_type, peg_type))
        self._evaluated_typeexpr = func_type.args[-1].type_expr
        return self

    @property
    def evaluated_typeexpr(self):
        if self._evaluated_typeexpr is None:
            self._evaluated_typeexpr = self.func_expr.root_value.dest_typearg.typeexpr
        return self._evaluated_typeexpr

def istypeexpr(expr):
    return expr is not None and (issubclass(expr.__class__, TypeExpression) or type(expr) is Variable)

class TypeExpression(Expression):
    """ An expressions which results in a type or a type expression. 
    This is the window to all types that are either available or must be lazily evaluated.
    """
    def __init__(self):
        # The symbol resolver is responsible for resolving names that an expression refers to.
        # Note that this does not prohibit any form of late binding as the assumption is that 
        # the scope where an expression exists, usually refers to some environment that should
        # have interface declarations (via the resolver) of types it refers to.
        Expression.__init__(self)

    def signature(self, visited = None):
        assert False, "Not Implemented"

    def resolution_finished(self):
        if self._resolved_value is None or not type(self._resolved_value) in (TypeParam, TypeFunction):
            ipdb.set_trace()
            assert False, "Invalid resolved value type: '%s'" % repr(self._resolved_value)

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

class TypeVariable(TypeExpression):
    """ A type variable used in a type expression. """
    def __init__(self, fqn):
        TypeExpression.__init__(self)
        self.fqn = fqn

    def __repr__(self):
        return "<TypeVar(%d) - %s>" % (id(self), self.fqn)

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
            raise errors.TLException("constructor must be a string")

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

    def set_resolver(self, resolver, parent_function):
        """ Resolver for children with this function.  This will give them a chance
        to resolve to parameters before globals are searched.
        """
        TypeExpression.set_resolver(self, resolver, parent_function)
        for arg in self.args:
            arg.type_expr.set_resolver(self, parent_function)

    def resolve(self):
        # A TypeFunction resolves to itself
        if not self.type_params and self.name == "map":
            ipdb.set_trace()
        for index,arg in enumerate(self.args):
            arg.type_expr.resolved_value
        return self

    def apply(self, substitutions, ignore = None):
        """ Applies the type expressions to the parameters to reify this type function. """
        # All substitutions to be applied to the params in this type function
        if type(substitutions) is list:
            substitutions = {name:expr for name,expr in zip(self.type_params, substitutions) if expr}
        new_type_args = []
        new_type_params = self.type_params[:]
        for index in xrange(len(new_type_params) - 1, -1, -1):
            if new_type_params[index] not in substitutions:
                del new_type_params[index]

        # If children have param names that match those in this func's param list 
        # then those should be skipped from conversion as those params would have
        # their own bindings.
        if ignore is None:
            ignore = defaultdict(int)

        for index,arg in enumerate(self.args):
            resolved_value = arg.type_expr.resolved_value
            newarg = arg
            if type(resolved_value) is TypeParam:
                # if this is a param bound to this function then we are good to go
                # we can make this substitution
                if ignore[resolved_value.name] == 0:
                    # Make the substitution
                    expr = substitutions.get(resolved_value.name, arg.type_expr)
                    # if arg.name and arg.name in subst: expr = substitutions[arg.name]
                    # elif not arg.name and type_exprs[index] is not None: expr = type_exprs[index]
                    newarg = TypeArg(arg.name, expr, arg.is_optional, arg.default_value, arg.annotations, arg.docs)
            else:
                assert type(resolved_value) is TypeFunction
                for tp in resolved_value.type_params: ignore[tp.name] += 1
                new_tf = resolved_value.apply(substitutions, ignore)
                for tp in resolved_value.type_params: ignore[tp.name] -= 1
                newarg = TypeArg(arg.name, new_tf, arg.is_optional, arg.default_value, arg.annotations, arg.docs)
            new_type_args.append(newarg)

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
        out = self.type_function.apply(self.type_exprs)
        out.resolver = self.type_function.resolver
        return out

    def set_resolver(self, resolver, parent_function):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        TypeExpression.set_resolver(self, resolver, parent_function)
        for expr in self.type_exprs:
            if expr:
                expr.set_resolver(resolver, parent_function)

class TypeArg(Annotatable):
    """ A type argument is a child of a given type.  Akin to a member/field of a type.
    These are either names of a type (yet to be bound) or another TypeFunction that 
    must be evaluated to create the type of this argument, or a TypeInitializer
    """
    def __init__(self, name, type_expr, is_optional = False, default_value = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        assert istypeexpr(type_expr), "TypeExpr type = '%s'" % repr(type_expr)
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
            raise errors.TLException("Argument must be a TypeArg. Found: '%s'" % type(arg))

        if arg.name:
            index = self.index_for(arg.name)
            if index >= 0:
                raise errors.TLException("Child type by the given name '%s' already exists" % arg.name)
        self._type_args.append(arg)

def make_type(constructor, name, type_params, type_args, parent = None, annotations = None, docs = ""):
    return TypeFunction(constructor, name, type_params = type_params, type_args = type_args,
                        parent = parent, annotations = annotations, docs = docs)

def make_literal_type(name, parent = None, annotations = None, docs = ""):
    return make_type("literal", name, type_params = None, type_args = None,
                     parent = parent, annotations = annotations, docs = docs)

def make_wrapper_type(name, type_params, parent = None, annotations = None, docs = ""):
    type_args = [TypeParam(param, None) for param in type_params]
    out = TypeFunction("extern", name, type_params = type_params, type_args = type_args,
                        parent = parent, annotations = annotations, docs = docs)
    for ta in type_args: ta.parent = out
    return out

def make_func_type(name, type_params, type_args, output_arg, parent = None, annotations = None, docs = ""):
    return TypeFunction("function", name, type_params = type_params, type_args = type_args + [output_arg],
                        parent = parent, annotations = annotations, docs = docs)

def make_typeref(name, type_params, type_expr, parent = None, annotations = None, docs = ""):
    return make_type("typeref", name, type_params = type_params, type_args = [type_expr],
                     parent = parent, annotations = annotations, docs = docs)

AnyType = make_literal_type("any")
VoidType = make_literal_type("void")
