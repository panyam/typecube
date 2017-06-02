
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
        self._resolver = None
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

    def substitute_with(self, bindings):
        """ This substitutes a given variable with the expression in the bindings map and returns a
        copy of this expression.  The current expression itself can be returned if necessary (for 
        example if no substitutions were found) """
        return self

    #########

    @property
    def resolver(self):
        if not self._resolver:
            ipdb.set_trace()
        return self._resolver

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        if self._resolver and self._resolver != resolver and self._resolved_value is None:
            ipdb.set_trace()
            assert False, "Resolver has been set.  Cannot be set again."
        self._resolver = resolver

    @property
    def resolved_value(self):
        if self._resolved_value is None:
            if self.resolver is None:
                ipdb.set_trace()
            assert self.resolver is not None
            self._resolved_value = self.resolve()
            self.on_resolution_finished()
        return self._resolved_value

    def on_resolution_finished(self): pass

    def resolve(self):
        """ This method resolves a type expression to a type object. """
        ipdb.set_trace()
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
        self.is_type = False
        self.is_function = False
        if type(field_path) in (str, unicode):
            field_path = FieldPath(field_path)
        self.field_path = field_path
        self.root_value = None
        assert type(field_path) is FieldPath and field_path.length > 0

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.field_path))

    def substitute_with(self, bindings):
        """ This substitutes a given variable with the expression in the bindings map and returns a
        copy of this expression.  The current expression itself can be returned if necessary (for 
        example if no substitutions were found) """
        first = self.field_path.get(0)
        if first not in bindings: return self

        # Here if we have a field path that is A/B/C, then we can do the substitution only for A 
        # and then see if the resultant expression has B/C.
        # This is too much work, so just prevent a substitution if field path has more than one
        if self.field_path.length != 1: return self
        return bindings[first]

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
            target = self.resolver.resolve_name(first)
            if target is None:
                ipdb.set_trace()
                assert target is not None, "Could not result '%s'" % first

            if type(target) is TypeArg:
                if type(target) is not TypeArg:
                    ipdb.set_trace()
                    assert False
                var_typearg = target
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
            elif type(target) is Type:
                self.is_type = True
                self.root_value = target
                self._evaluated_typeexpr = target
            elif type(target) is Fun:
                # Check if this is actually referring to a function and not a member
                if self.field_path.length != 1:
                    ipdb.set_trace()
                assert self.field_path.length == 1
                fname = self.field_path.get(0)
                self.is_function = True
                self.root_value = resolved_value = self.resolver.resolve_name(fname)
                if type(resolved_value) is not Fun:
                    ipdb.set_trace()
                self._evaluated_typeexpr = resolved_value.func_type
            else:
                ipdb.set_trace()
                assert False
        return self.root_value

class Fun(Expression, Annotatable):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, name, func_type, parent, annotations = None, docs = ""):
        Expression.__init__(self)
        Annotatable.__init__(self, annotations, docs)
        if type(func_type) is not Type:
            ipdb.set_trace()
        self._is_type_fun = all([a.type_expr == KindType for a in func_type.args])
        self.parent = parent
        self.name = name
        self.func_type = func_type
        self.expression = None
        self.is_external = False
        self.temp_variables = {}

    def apply(self, args):
        """ Apply this function's expression to a bunch of arguments and return a resultant expression. """
        assert len(args) <= len(self.source_typeargs), "Too many arguments provided."

        argnames = (arg.name for arg in self.source_typeargs)
        bindings = dict(zip(argnames, args))
        if len(args) < len(self.source_typeargs):
            # Create a curried function since we have less arguments
            assert False, "Currying not yet implemented"
            ipdb.set_trace()
            new_func_type = self.func_type
            out = Fun(self.name, new_func_type, self.parent, self.annotations, self.docs)
            out.expression = FunApp(self, args + [Variable(arg.name) for arg in new_func_type.source_typeargs])
            return out
        else:
            if self.is_external:
                # Nothing we can do so just return ourself
                return self
            else:
                # Create a curried function
                out = self.expression.substitute_with(bindings)
                return out

    def substitute_with(self, bindings):
        """ Returns a copy of this expression with the variables substituted by those found in the bindings map. """
        new_bindings = {}
        for name,expr in bindings.iter_items():
            if self.is_temp_variable(name): continue
            if name in (arg.name for arg in self.func_type.args): continue
            new_bindings[name] = expr

        # No bindings so nothing to replace and copy with
        if not new_bindings: return self

        new_func_type = self.func_type.substitute_with(substitutions)
        out = Function(self.name, new_func_type, self.parent, annotations, docs)
        out.expression = self.expression.substitute_with(substitutions)
        out.is_external = self.is_external
        return out

    @property
    def is_type_fun(self): return self._is_type_fun

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        Expression.set_resolver(self, resolver)
        self.func_type.set_resolver(self)
        if self.expression:
            self.expression.set_resolver(self)

    @property
    def fqn(self):
        out = self.name
        if self.parent and self.parent.fqn:
            if out is None:
                ipdb.set_trace()
            out = self.parent.fqn + "." + out
        return out or ""

    def __repr__(self):
        return "<%s(0x%x) %s>" % (self.__class__.__name__, id(self), self.name)

    def resolve_name(self, name):
        """ Try to resolve a name to a local, source or destination variable. """
        # Check source types
        for typearg in self.func_type.args:
            if typearg.name == name:
                return typearg

        # Check local variables
        if self.is_temp_variable(name):
            return TypeArg(name, self.temp_var_type(name))
        return self.resolver.resolve_name(name)

    @property
    def source_typeargs(self):
        return self.func_type.args[:-1]

    @property
    def dest_typearg(self):
        return self.func_type.args[-1]

    @property
    def returns_void(self):
        return self.func_type.args[-1] == VoidType

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

    def register_temp_var(self, varname, vartype = None):
        assert type(varname) in (str, unicode)
        if varname in (x.name for x in self.func_type.args):
            raise TLException("Duplicate temporary variable '%s'.  Same as function arguments." % varname)
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

class FunApp(Expression):
    """
    An expression for denoting a function call.  Fun calls can only be at the start of a expression stream, eg;

    f(x,y,z) => H => I => J

    but the following is invalid:

    H => f(x,y,z) -> J

    because f(x,y,z) must return an observable and observable returns are not supported (yet).
    """
    def __init__(self, func_expr, func_args = None, is_type_app = False):
        super(FunApp, self).__init__()
        self._is_type_app = is_type_app 
        self.func_expr = func_expr
        if func_args and type(func_args) is not list:
            func_args = [func_args]
        self.func_args = func_args

    def substitute_with(self, bindings):
        """ This substitutes a given function application with the expression in the bindings map 
        and returns a copy of this expression.  The current expression itself can be returned if 
        necessary (for example if no substitutions were found) """

        new_func_args = [arg.substitute_with(bindings) for arg in self.func_args]
        out = FunApp(func_expr.substitute_with(bindings), new_func_args, self.is_type_app)
        return out

    @property
    def is_type_app(self): return self._is_type_app

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        Expression.set_resolver(self, resolver)
        self.func_expr.set_resolver(resolver)
        for arg in self.func_args:
            arg.set_resolver(resolver)

    def resolve(self):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # First resolve the expression to get the source function
        # Here we need to decide if the function needs to be "duplicated" for each different type
        # This is where type re-ification is important - both at buildtime and runtime
        self.func_expr.resolve()
        if not self.func_expr.resolved_value:
            raise errors.TLException("Fun '%s' is undefined" % (self.func_expr))
        if type(self.func_expr.resolved_value) is not Fun:
            raise errors.TLException("Fun '%s' is not a function" % (self.func_expr))

        # Each of the function arguments is either a variable or a value.  
        # If it is a variable expression then it needs to be resolved starting from the
        # function that holds this statement (along with any other locals and upvals)
        for arg in self.func_args:
            arg.resolve()

        function = self.func_expr.resolved_value
        if len(self.func_args) != len(function.source_typeargs):
            raise errors.TLException("Fun '%s' takes %d arguments, but encountered %d" %
                                            (str(func_type), len(function.source_typeargs), len(self.func_args)))

        if function.is_type_fun:
            if not self.is_type_app:
                ipdb.set_trace()
            assert self.is_type_app
            ipdb.set_trace()
            out = function.apply(self.func_args)
            out.set_resolver(self.resolver)
            return out
        else:
            for i,arg in enumerate(self.func_args):
                peg_type = arg.evaluated_typeexpr.resolved_value
                hole_type = function.source_typeargs[i].type_expr.resolved_value
                if not tlunifier.can_substitute(peg_type, hole_type):
                    ipdb.set_trace()
                    raise errors.TLException("Argument at index %d expected (hole) type (%s), found (peg) type (%s)" % (i, hole_type, peg_type))
            self._evaluated_typeexpr = function.dest_typearg.type_expr
            if function.is_type_fun:
                assert self.is_type_app
                ipdb.set_trace()
                # TODO: reify this type?
            return self

    @property
    def evaluated_typeexpr(self):
        if self._evaluated_typeexpr is None:
            self._evaluated_typeexpr = self.func_expr.root_value.dest_typearg.typeexpr
        return self._evaluated_typeexpr

def TypeFun(name, type_params, expression, parent, annotations = None, docs = ""):
    func_type = make_func_type(name, [TypeArg(tp,KindType) for tp in type_params], KindType)
    # The shell/wrapper function that will return a copy of the given expression bound to values in here.
    out = Fun(name, func_type, parent = parent, annotations = annotations, docs = docs)
    out.expression = expression
    return out

class Type(Expression, Annotatable):
    def __init__(self, constructor, name, type_args, parent, annotations = None, docs = ""):
        """
        Creates a new type function.  Type functions are responsible for creating concrete type instances
        or other (curried) type functions.

        Params:
            constructor     The type's constructor, eg "record", "int" etc.  This is not the name 
                            of the type itself but a name that indicates a class of this type.
            name            Name of the type.
            type_args       Type arguments are fields/children of a given type are themselves expressions 
                            (whose final type must be of Type).
            parent          A reference to the parent container entity of this type.
            annotations     Annotations applied to the type.
            docs            Documentation string for the type.
        """
        Annotatable.__init__(self, annotations = annotations, docs = docs)
        Expression.__init__(self)

        if type(constructor) not in (str, unicode):
            raise errors.TLException("constructor must be a string")

        self._resolved_value = self
        self.constructor = constructor
        self.parent = parent
        self.name = name
        self.args = TypeArgList(type_args)
        self._signature = None

    def substitute_with(self, bindings):
        new_args = [arg.substitute_with(bindings) for arg in self.args]
        return Type(self.constructor, self.name, new_args, self.parent, self.annotations, self.docs)

    def set_resolver(self, resolver):
        """ Resolver for children with this function.  This will give them a chance
        to resolve to parameters before globals are searched.
        """
        Expression.set_resolver(self, resolver)
        for arg in self.args:
            arg.type_expr.set_resolver(self)

    def resolve(self):
        # A Type resolves to itself
        for index,arg in enumerate(self.args):
            arg.type_expr.resolved_value
        return self

    def signature(self, visited = None):
        if not self._signature:
            if visited is None: visited = set()
            self._signature = self.constructor
            if self.name: self._signature += ":" + self.name
            if self.args:
                self._signature += "(" + ", ".join([t.type_expr.signature(visited) for t in self.args]) + ")"
        return self._signature

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

class TypeArg(Annotatable):
    """ A type argument is a child of a given type.  Akin to a member/field of a type.  """
    def __init__(self, name, type_expr, is_optional = False, default_value = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.name = name
        self.type_expr = type_expr
        self.is_optional = is_optional
        self.default_value = default_value or None

    def __json__(self, **kwargs):
        out = {}
        if self.name:
            out["name"] = self.name
        return out

    def substitute_with(self, bindings):
        new_expr = self.type_expr.substitute_with(bindings)
        return TypeArg(self.name, new_expr, self.is_optional, self.default_value, self.annotations, self.docs)

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
        if type(arg) in (str, unicode):
            arg = Variable(arg)
        if issubclass(arg.__class__, Expression):
            arg = TypeArg(None, arg)
        elif not isinstance(arg, TypeArg):
            raise errors.TLException("Argument must be a TypeArg. Found: '%s'" % type(arg))

        if arg.name:
            index = self.index_for(arg.name)
            if index >= 0:
                raise errors.TLException("Child type by the given name '%s' already exists" % arg.name)
        self._type_args.append(arg)

def make_type(constructor, name, type_args, parent = None, annotations = None, docs = ""):
    return Type(constructor, name, type_args = type_args,
                 parent = parent, annotations = annotations, docs = docs)

def make_literal_type(name, parent = None, annotations = None, docs = ""):
    return make_type("literal", name, type_args = None, parent = parent, annotations = annotations, docs = docs)

def make_func_type(name, type_args, output_arg, parent = None, annotations = None, docs = ""):
    return make_type("function", name, type_args + [output_arg],
                     parent = parent, annotations = annotations, docs = docs)

def make_typeref(name, type_expr, parent = None, annotations = None, docs = ""):
    return make_type("typeref", name, type_args = [type_expr],
                     parent = parent, annotations = annotations, docs = docs)

def make_extern_type(name, type_args, parent = None, annotations = None, docs = ""):
    return make_type("extern", name, type_args = type_args,
                     parent = parent, annotations = annotations, docs = docs)

KindType = make_literal_type("Type")
AnyType = make_literal_type("any")
VoidType = make_literal_type("void")
