
import ipdb
from collections import defaultdict
from itertools import izip
from typelib import errors
from typelib.utils import FieldPath
from typelib.resolvers import Resolver, MapResolver, ResolverStack
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier

class Expr(object):
    """
    Parent of all exprs.  All exprs must have a value.  Exprs only appear in functions.
    """
    def __init__(self):
        pass

    #########

    def evaltype(self, resolver_stack):
        # Do caching of results here based on resolver!
        return self._evaltype(resolver_stack)

    def _evaltype(self, resolver_stack):
        ipdb.set_trace()
        assert False, "not implemented"
        return None

    def resolve(self, resolver):
        # Do caching of results here based on resolver!
        return self._resolve(resolver)

    def _resolve(self, resolver_stack):
        """ This method resolves a type expr to a type object. 
        The resolver is used to get bindings for names used in this expr.
        
        Returns a ResolvedValue object that contains the final expr value after resolution of this expr.
        """
        assert False, "Not Implemented"
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

class Variable(Expr):
    """ An occurence of a name that can be bound to a value, a field or a type. """
    def __init__(self, field_path):
        super(Variable, self).__init__()
        if type(field_path) in (str, unicode):
            field_path = FieldPath(field_path)
        self.field_path = field_path
        assert type(field_path) is FieldPath and field_path.length > 0

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.field_path))

    def _evaltype(self, resolver_stack):
        resolved = self.resolve(resolver_stack)
        if type(resolved) is Type:
            return resolved
        if type(resolved) is Fun:
            return resolved.func_type.resolve(resolver_stack)
        if issubclass(resolved.__class__, App):
            func = resolved.func_expr.resolve(resolver_stack)
            func_type = func.func_type.resolve(resolver_stack)
            return func_type.output_arg
        if type(resolved) is Literal:
            return resolved.evaltype(resolver_stack)
        ipdb.set_trace()
        assert False, "Unknown resolved value type"

    def _resolve(self, resolver_stack):
        """
        Returns the actual entry pointed to by the "first" part of the field path.
        """
        first = self.field_path.get(0)
        target = resolver_stack.resolve_name(first)
        if target is None:
            assert target is not None, "Could not resolve '%s'" % first
        return target

class Fun(Expr, Annotatable):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, name, func_type, expr, parent, annotations = None, docs = ""):
        Expr.__init__(self)
        Annotatable.__init__(self, annotations, docs)
        if type(func_type) is not Type:
            ipdb.set_trace()
        self._is_type_fun = all([a.type_expr == KindType for a in func_type.args])
        self.parent = parent
        self.name = name
        self.func_type = func_type
        self.expr = expr
        self.temp_variables = {}
        self._default_resolver_stack = None

    @property
    def default_resolver_stack(self):
        if self._default_resolver_stack is None:
            self._default_resolver_stack = ResolverStack(self.parent, None).push(self)
        return self._default_resolver_stack

    def __json__(self, **kwargs):
        out = {}
        if self.name:
            out["name"] = self.name
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if self.func_type:
            out["type"] = self.func_type.json(**kwargs)
        return out

    @property
    def is_external(self): return self.expr is None

    def resolve_name(self, name):
        """ Try to resolve a name to a local, source or destination variable. """
        function = self
        # Check source types
        out_typearg = None
        for typearg in function.func_type.args:
            if typearg.name == name:
                out_typearg = typearg
                break
        else:
            if function.func_type.output_arg and function.func_type.output_arg.name == name:
                out_typearg = function.func_type.output_arg
            elif function.is_temp_variable(name):
                # Check local variables
                out_typearg = TypeArg(name, function.temp_var_type(name))

        if out_typearg:
            if out_typearg.type_expr == KindType:
                # TODO: *something?*
                pass
        return out_typearg

    def apply(self, args, resolver_stack):
        """ Apply this function's expr to a bunch of arguments and return a resultant expr. """
        assert len(args) <= len(self.source_typeargs), "Too many arguments provided."

        argnames = [arg.name for arg in self.source_typeargs]
        bindings = dict(zip(argnames, args))

        if len(args) < len(self.source_typeargs):
            # Create a curried function since we have less arguments
            assert False, "Currying not yet implemented"
            ipdb.set_trace()

            new_func_type = self.func_type
            new_expr = FunApp(self, args + [Variable(arg.name) for arg in new_func_type.source_typeargs])
            out = Fun(self.name, new_func_type, new_expr, self.parent, self.annotations, self.docs)
            return out
        else:
            if self.is_external:
                # Nothing we can do so just return ourself
                ipdb.set_trace()
                return self
            else:
                # Create a curried function
                resolver_stack = resolver_stack.push(MapResolver(bindings))
                out = self.expr.resolve(resolver_stack)
                return out

    def _resolve(self, resolver_stack):
        """
        The main resolver method.  This should take care of the following:

            1. Ensure field paths are correct
            2. All exprs have their evaluated types set
        """
        if resolver_stack == None:
            resolver_stack = ResolverStack(self.parent, None)
        resolver_stack = resolver_stack.push(self)
        new_func_type = self.func_type.resolve(resolver_stack)
        resolved_expr = None if not self.expr else self.expr.resolve(resolver_stack)
        if new_func_type == self.func_type and resolved_expr == self.expr:
            return self
        out = Fun(self.name, new_func_type, resolved_expr, self.parent, self.annotations, self.docs)
        return out

    def _evaltype(self, resolver_stack):
        return self.resolve(resolver_stack).func_type

    @property
    def is_type_fun(self): return self._is_type_fun

    @property
    def fqn(self):
        out = self.name
        if self.parent and self.parent.fqn:
            out = self.parent.fqn + "." + out
        return out or ""

    def __repr__(self):
        return "<%s(0x%x) %s>" % (self.__class__.__name__, id(self), self.name)

    @property
    def source_typeargs(self):
        return self.func_type.args

    @property
    def dest_typearg(self):
        return self.func_type.output_arg

    @property
    def returns_void(self):
        return self.func_type.output_arg is None or self.func_type.output_arg.type_expr == VoidType

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

class App(Expr):
    """ Super class of all applications """
    def __init__(self, func_expr, func_args = None):
        super(App, self).__init__()
        self.func_expr = func_expr
        if func_args and type(func_args) is not list:
            func_args = [func_args]
        self.func_args = func_args

    @property
    def is_type_app(self): return self._is_type_app

    def _evaltype(self, resolver_stack):
        resolved = self.resolve(resolver_stack)
        if issubclass(resolved.__class__, App):
            resolved.func_expr.evaltype(resolver_stack)
        elif isinstance(resolved, Type):
            return resolved
        else:
            ipdb.set_trace()
            assert False, "What now?"

    def resolve_function(self, resolver_stack):
        function = self.func_expr.resolve(resolver_stack)
        if not function:
            raise errors.TLException("Fun '%s' is undefined" % (self.func_expr))
        while type(function) is Type and function.constructor == "typeref":
            assert len(function.args) == 1, "Typeref cannot have more than one child argument"
            function = function.args[0].type_expr.resolve(function.default_resolver_stack)

        if type(function) is not Fun:
            raise errors.TLException("Fun '%s' is not a function" % (self.func_expr))
        return function

class TypeApp(App):
    """ An application of type functions instead of normal functions. """
    def __init__(self, func_expr, func_args = None):
        super(TypeApp, self).__init__(func_expr, func_args)
        self._is_type_app = True

    def __repr__(self):
        return "<TypeApp(0x%x) Expr = %s, Args = (%s)>" % (id(self), repr(self.func_expr), ", ".join(map(repr, self.func_args)))

    def _resolve(self, resolver_stack):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # First resolve the expr to get the source function
        # Here we need to decide if the function needs to be "duplicated" for each different type
        # This is where type re-ification is important - both at buildtime and runtime
        function = self.resolve_function(resolver_stack)

        assert self.is_type_app
        arg_values = [arg.resolve(resolver_stack) for arg in self.func_args]
        return function.apply(arg_values, resolver_stack)

class FunApp(App):
    """ An expr for denoting a function application.  """
    def __init__(self, func_expr, func_args = None):
        super(FunApp, self).__init__(func_expr, func_args)
        self._is_type_app = False

    def __repr__(self):
        return "<FunApp(0x%x) Expr = %s, Args = (%s)>" % (id(self), repr(self.func_expr), ", ".join(map(repr, self.func_args)))

    def _resolve(self, resolver_stack):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # First resolve the expr to get the source function
        # Here we need to decide if the function needs to be "duplicated" for each different type
        # This is where type re-ification is important - both at buildtime and runtime
        function = self.resolve_function(resolver_stack)

        arg_values = [arg.resolve(resolver_stack) for arg in self.func_args]
        # Wont do currying for now
        if len(arg_values) != len(function.source_typeargs):
            raise errors.TLException("Fun '%s' takes %d arguments, but encountered %d.  Currying or var args NOT YET supported." %
                                            (function.name, len(function.source_typeargs), len(self.func_args)))

        # TODO - check arg types match
        # Only return a new expr if any thing has changed
        if function != self.func_expr or any(x != y for x,y in zip(arg_values, self.func_args)):
            return FunApp(function, arg_values)
        return self

def TypeFun(name, type_params, expr, parent, annotations = None, docs = ""):
    func_type = make_func_type(name, [TypeArg(tp,KindType) for tp in type_params], KindType)
    # The shell/wrapper function that will return a copy of the given expr bound to values in here.
    return Fun(name, func_type, expr, parent, annotations = annotations, docs = docs)

class Type(Expr, Annotatable):
    def __init__(self, constructor, name, type_args, output_arg, parent, annotations = None, docs = ""):
        """
        Creates a new type function.  Type functions are responsible for creating concrete type instances
        or other (curried) type functions.

        Params:
            constructor     The type's constructor, eg "record", "int" etc.  This is not the name 
                            of the type itself but a name that indicates a class of this type.
            name            Name of the type.
            type_args       Type arguments are fields/children of a given type are themselves exprs 
                            (whose final type must be of Type).
            output_arg      Type arguments of the output if this is a Function type
            parent          A reference to the parent container entity of this type.
            annotations     Annotations applied to the type.
            docs            Documentation string for the type.
        """
        Annotatable.__init__(self, annotations = annotations, docs = docs)
        Expr.__init__(self)

        if type(constructor) not in (str, unicode):
            raise errors.TLException("constructor must be a string")

        self.constructor = constructor
        self.parent = parent
        self.name = name
        self.args = TypeArgList(type_args)
        self.output_arg = output_arg if output_arg is None else validate_typearg(output_arg)
        self._default_resolver_stack = None

    @property
    def default_resolver_stack(self):
        if self._default_resolver_stack is None:
            self._default_resolver_stack = ResolverStack(self.parent, None)
        return self._default_resolver_stack

    @property
    def fqn(self):
        out = self.name
        if self.parent and self.parent.fqn:
            out = self.parent.fqn + "." + out
        return out or ""

    def _evaltype(self, resolver_stack):
        """ Type of a "Type" is a KindType!!! """
        return KindType

    def _resolve(self, resolver_stack):
        # A Type resolves to itself
        new_type_args = [arg.resolve(resolver_stack) for arg in self.args]
        new_output_arg = None if not self.output_arg else self.output_arg.resolve(resolver_stack)
        if new_output_arg != self.output_arg or any(x != y for x,y in zip(new_type_args, self.args)):
            return Type(self.constructor, self.name, new_type_args, new_output_arg, self.parent, self.annotations, self.docs)
        return self

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

class TypeArg(Expr, Annotatable):
    """ A type argument is a child of a given type.  Akin to a member/field of a type.  """
    def __init__(self, name, type_expr, is_optional = False, default_value = None, annotations = None, docs = ""):
        Expr.__init__(self)
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

    def _evaltype(self, resolver_stack):
        """ Type of a "Type" is a KindType!!! """
        resolved = self.resolve(resolver_stack)
        return resolved.type_expr.resolve(resolver_stack)

    def _resolve(self, resolver_stack):
        out = self
        if self.type_expr is None:
            return self
        new_expr = self.type_expr.resolve(resolver_stack)
        if new_expr != self.type_expr:
            out =  TypeArg(self.name, new_expr, self.is_optional, self.docs, annotations = self.annotations, docs = self.docs)
        return out

    def unwrap_with_field_path(self, full_field_path, resolver_stack):
        starting_var, field_path = full_field_path.pop()
        curr_typearg = self
        curr_path = curr_field_name = starting_var
        yield curr_field_name, curr_path, curr_typearg
        while field_path.length > 0:
            next_field_name, tail_path = field_path.pop()
            next_path = curr_path + "/" + next_field_name
            if curr_typearg is None:
                ipdb.set_trace()
            next_typearg = curr_typearg.type_expr.resolve(resolver_stack).args.withname(next_field_name)
            curr_field_name, curr_path, field_path = next_field_name, next_path, tail_path
            yield curr_field_name, curr_path, curr_typearg

def validate_typearg(arg):
    if isinstance(arg, TypeArg):
        return arg
    elif issubclass(arg.__class__, Expr):
        return TypeArg(None, arg)
    elif type(arg) in (str, unicode):
        return TypeArg(None, Variable(arg))
    else:
        raise errors.TLException("Argument must be a TypeArg, Expr or a string. Found: '%s'" % type(arg))

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

    def __repr__(self):
        return repr(self._type_args)

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
        arg = validate_typearg(arg)
        if arg.name:
            index = self.index_for(arg.name)
            if index >= 0:
                raise errors.TLException("Child type by the given name '%s' already exists" % arg.name)
        self._type_args.append(arg)

def make_type(constructor, name, type_args, output_arg, parent = None, annotations = None, docs = ""):
    return Type(constructor, name, type_args = type_args, output_arg = output_arg,
                 parent = parent, annotations = annotations, docs = docs)

def make_literal_type(name, parent = None, annotations = None, docs = ""):
    return make_type("literal", name, type_args = None, output_arg = None,
                     parent = parent, annotations = annotations, docs = docs)

def make_func_type(name, type_args, output_arg, parent = None, annotations = None, docs = ""):
    return make_type("function", name, type_args, output_arg,
                     parent = parent, annotations = annotations, docs = docs)

def make_typeref(name, type_expr, parent = None, annotations = None, docs = ""):
    return make_type("typeref", name, type_args = [type_expr], output_arg = None,
                     parent = parent, annotations = annotations, docs = docs)

def make_extern_type(name, type_args, parent = None, annotations = None, docs = ""):
    return make_type("extern", name, type_args = type_args, output_arg = None,
                     parent = parent, annotations = annotations, docs = docs)

KindType = make_literal_type("Type")
AnyType = make_literal_type("any")
VoidType = make_literal_type("void")
