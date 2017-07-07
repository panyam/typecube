
from enum import Enum
from ipdb import set_trace
from collections import defaultdict
from itertools import izip
from typelib import errors
from typelib.utils import FieldPath
from typelib.resolvers import Resolver, MapResolver, ResolverStack
from typelib.annotations import Annotatable

class Expr(object):
    """
    Parent of all exprs.  All exprs must have a value.  Exprs only appear in functions.
    """
    def __init__(self):
        pass

    #########

    def equals(self, another):
        return isinstance(another, self.__class__) and self._equals(another)

    def _equals(self, another):
        assert False, "Not Implemented"

    def evaltype(self, resolver_stack):
        # Do caching of results here based on resolver!
        return self._evaltype(resolver_stack)

    def _evaltype(self, resolver_stack):
        set_trace()
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

class Var(Expr):
    """ An occurence of a name that can be bound to a value, a field or a type. """
    def __init__(self, field_path):
        super(Var, self).__init__()
        if type(field_path) in (str, unicode):
            field_path = FieldPath(field_path)
        self.field_path = field_path
        assert type(field_path) is FieldPath and field_path.length > 0

    def _equals(self, another):
        return self.field_path.parts == another.field_path.parts

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.field_path))

    def _evaltype(self, resolver_stack):
        resolved = self.resolve(resolver_stack)
        if type(resolved) is Type:
            return resolved
        if type(resolved) is Fun:
            return resolved.fun_type.resolve(resolver_stack)
        if issubclass(resolved.__class__, FunApp):
            func = resolved.func_expr.resolve(resolver_stack)
            fun_type = func.fun_type.resolve(resolver_stack)
            return fun_type.output_typearg
        if issubclass(resolved.__class__, Expr):
            return resolved.evaltype(resolver_stack)
        set_trace()
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
    def __init__(self, fqn, fun_type, expr, parent, annotations = None, docs = ""):
        Expr.__init__(self)
        Annotatable.__init__(self, annotations, docs)
        if type(fun_type) is not Type:
            set_trace()
        self._is_type_fun = all([a.type_expr == KindType for a in fun_type.args])
        self.parent = parent
        self.fqn = fqn
        self.fun_type = fun_type
        self.expr = expr
        self.temp_variables = {}
        self._default_resolver_stack = None

    def _equals(self, another):
        return self.fqn == another.fqn and \
                self.fun_type.equals(another.fun_type) and \
                self.expr.equals(another.expr)

    @property
    def default_resolver_stack(self):
        if self._default_resolver_stack is None:
            self._default_resolver_stack = ResolverStack(self.parent, None).push(self)
        return self._default_resolver_stack

    def __json__(self, **kwargs):
        out = {}
        if self.fqn:
            out["fqn"] = self.fqn
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if self.fun_type:
            out["type"] = self.fun_type.json(**kwargs)
        return out

    @property
    def is_external(self): return self.expr is None

    def debug_show(self, level = 0):
        function = self
        print ("  " * (level)) + "SourceArgs:"
        for typearg in function.fun_type.args:
            print ("  " * (level + 1)) + ("%s: %s" % (typearg.name,typearg))

        print ("  " * (level)) + "OutputArg:"
        if function.fun_type.output_arg:
            print ("  " * (level + 1)) + "%s" % function.fun_type.output_arg

        print ("  " * (level)) + "Locals:"
        for key,value in self.temp_variables.iteritems():
            print ("  " * (level + 1)) + ("%s: %s" % (key, value))

    def resolve_name(self, name):
        """ Try to resolve a name to a local, source or destination variable. """
        function = self
        # Check source types
        out_typearg = None
        for typearg in function.fun_type.args:
            if typearg.name == name:
                out_typearg = typearg
                break
        else:
            if function.fun_type.output_arg and function.fun_type.output_arg.name == name:
                out_typearg = function.fun_type.output_arg
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

            new_fun_type = self.fun_type
            new_expr = FunApp(self, args + [Var(arg.name) for arg in new_fun_type.source_typeargs])
            out = Fun(self.name, new_fun_type, new_expr, self.parent, self.annotations, self.docs)
            return out
        elif not self.is_external:
            # Create a curried function
            resolver_stack = resolver_stack.push(MapResolver(bindings))
            out = self.expr.resolve(resolver_stack)
            return out
        # Cannot do anything for external functions
        return None

    def _resolve(self, resolver_stack):
        """
        The main resolver method.  This should take care of the following:

            1. Ensure field paths are correct
            2. All exprs have their evaluated types set
        """
        if resolver_stack == None:
            resolver_stack = ResolverStack(self.parent, None)
        resolver_stack = resolver_stack.push(self)
        new_fun_type = self.fun_type.resolve(resolver_stack)
        resolved_expr = None if not self.expr else self.expr.resolve(resolver_stack)
        if new_fun_type == self.fun_type and resolved_expr == self.expr:
            return self
        out = Fun(self.name, new_fun_type, resolved_expr, self.parent, self.annotations, self.docs)
        return out

    def _evaltype(self, resolver_stack):
        return self.resolve(resolver_stack).fun_type

    @property
    def is_type_fun(self): return self._is_type_fun

    def __repr__(self):
        return "<%s(0x%x) %s>" % (self.__class__.__name__, id(self), self.fqn)

    @property
    def source_typeargs(self):
        return self.fun_type.args

    @property
    def dest_typearg(self):
        return self.fun_type.output_arg

    @property
    def returns_void(self):
        return self.fun_type.output_arg is None or self.fun_type.output_arg.type_expr == VoidType

    def matches_input(self, input_typeexprs):
        """Tells if the input types can be accepted as argument for this transformer."""
        from typelib import unifier as tlunifier
        assert type(input_typeexprs) is list
        if len(input_typeexprs) != len(self.source_typeargs):
            return False
        return all(tlunifier.can_substitute(st.type_expr, it) for (st,it) in izip(self.source_typeargs, input_typeexprs))

    def matches_output(self, output_typeexpr):
        from typelib import unifier as tlunifier
        return tlunifier.can_substitute(output_typeexpr, self.dest_typearg.type_expr)

    def is_temp_variable(self, varname):
        return varname in self.temp_variables

    def temp_var_type(self, varname):
        return self.temp_variables[str(varname)]

    def register_temp_var(self, varname, vartype = None):
        assert type(varname) in (str, unicode)
        if varname in (x.name for x in self.fun_type.args):
            raise TLException("Duplicate temporary variable '%s'.  Same as function arguments." % varname)
        elif self.is_temp_variable(varname) and self.temp_variables[varname] is not None:
            raise TLException("Duplicate temporary variable declared: '%s'" % varname)
        self.temp_variables[varname] = vartype

class FunApp(Expr):
    """ Super class of all applications """
    def __init__(self, func_expr, func_args = None):
        super(FunApp, self).__init__()
        self.func_expr = func_expr
        if func_args and type(func_args) is not list:
            func_args = [func_args]
        self.func_args = func_args

    def _equals(self, another):
        return self.func_expr.equals(another.func_expr) and \
                self.func_args.equals(another.func_args)

    def _evaltype(self, resolver_stack):
        resolved = self.resolve(resolver_stack)
        if issubclass(resolved.__class__, App):
            resolved.func_expr.evaltype(resolver_stack)
        elif isinstance(resolved, Type):
            return resolved
        else:
            set_trace()
            assert False, "What now?"

    def resolve_function(self, resolver_stack):
        function = self.func_expr.resolve(resolver_stack)
        if not function:
            raise errors.TLException("Fun '%s' is undefined" % (self.func_expr))
        while type(function) is Type and function.category == "typeref":
            assert len(function.args) == 1, "Typeref cannot have more than one child argument"
            function = function.args[0].type_expr.resolve(function.default_resolver_stack)

        if type(function) is not Fun:
            raise errors.TLException("Fun '%s' is not a function" % (self.func_expr))
        return function

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
        if function != self.func_expr or any(x != y for x,y in zip(arg_values, self.func_args)):
            # Only return a new expr if any thing has changed
            return FunApp(function, arg_values)
        return self

class TypeCategory(Enum):
    # Named basic types
    LITERAL_TYPE        = 0

    # t1 x t2 x ... x tN
    PRODUCT_TYPE        = 1

    # t1 + t2 + ... + tN
    # eg records, tuples
    SUM_TYPE            = 2

    # t1 -> t2 -> ... -> tN
    FUNCTION_TYPE       = 3

    # forall(t1,t2,...,tN) -> tN(t1...tN-1)
    UNIVERSAL_TYPE      = 4

    # exists(t1,t2,...,tN) -> tN(t1...tN-1)
    EXISTENTIAL_TYPE    = 5

    # \(t1,t2,...,tN) -> tN(t1...tN-1)
    ABSTRACTION         = 6

    # t1(t2...tN)
    # Instantiation of a generic type
    APPLICATION         = 7

    # Reference to another type by name (that will be resolved later)
    TYPEREF             = 8

    # Alias type
    ALIAS_TYPE          = 9

class Type(Expr, Annotatable):
    def __init__(self, category, fqn, type_args, parent, annotations = None, docs = ""):
        """
        Creates a new type function.  Type functions are responsible for creating concrete type instances
        or other (curried) type functions.

        Params:
            category        The type's category, eg "record", "literal" etc.  This is not the name 
                            of the type itself but a name that indicates a class of this type.
            fqn             FQN of the type.
            type_args       Type arguments are fields/children of a given type are themselves exprs 
                            (whose final type must be of Type).  The meanign of the type arguments
                            depends on the category this type is representing.  See the TypeCategory
                            for more details.
            parent          A reference to the parent container entity of this type.
            annotations     Annotations applied to the type.
            docs            Documentation string for the type.
        """
        Annotatable.__init__(self, annotations = annotations, docs = docs)
        Expr.__init__(self)

        if type(category) is not TypeCategory:
            raise errors.TLException("category must be a TypeCategory")

        self.is_extern = False
        self.category = category
        self.parent = parent
        self.fqn = fqn
        self.args = TypeArgList(type_args)
        # self.output_arg = output_arg if output_arg is None else validate_typearg(output_arg)
        self._default_resolver_stack = None

    def _equals(self, another):
        return self.fqn == another.fqn and \
               self.category == another.category and \
               self.parent == another.parent and \
               (self.output_arg == another.output_arg or self.output_arg.equals(another.output_arg)) and \
               self.args.equals(another.args)

    @property
    def default_resolver_stack(self):
        if self._default_resolver_stack is None:
            self._default_resolver_stack = ResolverStack(self.parent, None)
        return self._default_resolver_stack

    def _evaltype(self, resolver_stack):
        """ Type of a "Type" is a KindType!!! """
        return KindType

    def _resolve(self, resolver_stack):
        """ Default resolver for just resolving all child argument types. """
        new_type_args = [arg.resolve(resolver_stack) for arg in self.args]
        new_output_arg = None if not self.output_arg else self.output_arg.resolve(resolver_stack)
        if new_output_arg != self.output_arg or any(x != y for x,y in zip(new_type_args, self.args)):
            return Type(self.category, self.fqn, new_type_args, new_output_arg, self.parent, self.annotations, self.docs)
        return self

    @property
    def is_type_function(self):
        return False

    def __json__(self, **kwargs):
        out = {'category': self.category}
        if self.fqn:
            out["fqn"] = self.fqn
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if self.args:
            out["args"] = [arg.json(**kwargs) for arg in self.args]
        return out

class TypeRef(Type):
    def __init__(self, fqn, target_fqn, parent, annotations = None, docs = ""):
        type_args = [TypeArg(None, make_literal_type(target_fqn))]
        Type.__init__(self, TypeCategory.TYPEREF, fqn, type_args, parent, annotations = None, docs = "")

    def _resolve(self, resolver_stack):
        set_trace()

class TypeFun(Type):
    def __init__(self, fqn, type_params, type_expr, parent, annotations = None, docs = ""):
        type_args = [TypeArg(tp,KindType) for tp in type_params] + [TypeArg(None, type_expr if type_expr else KindType)]
        Type.__init__(self, TypeCategory.ABSTRACTION, fqn, type_args, parent, annotations = None, docs = "")
        self.is_extern = type_expr is None

    @property
    def is_type_function(self):
        return True

    @property
    def output_typearg(self):
        return self.args[-1]

class TypeApp(Type):
    def __init__(self, type_func, type_args, parent, annotations = None, docs = ""):
        type_args = [TypeArg(None, type_func)] + type_args
        Type.__init__(self, TypeCategory.APPLICATION, None, type_args, parent, annotations = None, docs = "")

    def _typeapp_resolver(self, resolver_stack):
        """ Resolves a type application. """
        new_type_args = [arg.resolve(resolver_stack) for arg in self.args]

        # Ensure that the first value is a type function
        assert new_type_args[0].type_expr.is_type_function
        new_output_arg = None if not self.output_arg else self.output_arg.resolve(resolver_stack)
        if new_output_arg != self.output_arg or any(x != y for x,y in zip(new_type_args, self.args)):
            return Type(self.category, self.fqn, new_type_args, new_output_arg, self.parent, self.annotations, self.docs)
        return self

    def resolve_typefunction(self, resolver_stack):
        func_expr = self.args[0]
        func_args = self.args[1:]

        typefun = func_expr.resolve(resolver_stack)
        if not typefun:
            raise errors.TLException("Fun '%s' is undefined" % func_expr)
        while typefun.category == "typeref":
            assert len(typefun.args) == 1, "Typeref cannot have more than one child argument"
            typefun = typefun.args[0].type_expr.resolve(typefun.default_resolver_stack)

        if not typefun.is_type_function:
            raise errors.TLException("Fun '%s' is not a function" % (self.func_expr))
        return typefun

class TypeArg(Expr, Annotatable):
    """ A type argument is a child of a given type.  Akin to a member/field of a type.  """
    def __init__(self, name, type_expr, is_optional = False, default_value = None, annotations = None, docs = ""):
        Expr.__init__(self)
        Annotatable.__init__(self, annotations, docs)
        self.name = name
        self.type_expr = type_expr
        self.is_optional = is_optional
        self.default_value = default_value or None

    def _equals(self, another):
        return self.name == another.name and \
                self.is_optional == another.is_optional and \
                (self.default_value == another.default_value or self.default_value.equals(another.default_value)) and \
                self.type_expr.equals(another.type_expr)

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
                set_trace()
            next_typearg = curr_typearg.type_expr.resolve(resolver_stack).args.withname(next_field_name)
            curr_field_name, curr_path, field_path = next_field_name, next_path, tail_path
            yield curr_field_name, curr_path, curr_typearg

def validate_typearg(arg):
    if isinstance(arg, TypeArg):
        return arg
    elif issubclass(arg.__class__, Expr):
        return TypeArg(None, arg)
    elif type(arg) in (str, unicode):
        return TypeArg(None, Var(arg))
    else:
        raise errors.TLException("Argument must be a TypeArg, Expr or a string. Found: '%s'" % type(arg))

class TypeArgList(object):
    """ A list of type args for a particular type container. """
    def __init__(self, type_args):
        self._type_args = []
        for type_arg in type_args or []:
            self.add(type_arg)

    def equals(self, another):
        return len(self._type_args) == len(self._type_args) and all(x.equals(y) for x,y in izip(self._type_args, another._type_args))

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

def make_type(category, fqn, type_args, parent = None, annotations = None, docs = ""):
    return Type(category, fqn, type_args = type_args, parent = parent, annotations = annotations, docs = docs)

def make_literal_type(fqn, parent = None, annotations = None, docs = ""):
    return make_type(TypeCategory.LITERAL_TYPE, fqn, type_args = None, parent = parent, annotations = annotations, docs = docs)

def make_fun_type(fqn, type_args, output_arg, parent = None, annotations = None, docs = ""):
    if output_arg is None:
        output_arg = VoidType
    args = type_args + [output_arg]
    return make_type(TypeCategory.FUNCTION_TYPE, fqn, args,
                     parent = parent, annotations = annotations, docs = docs)

def make_alias(fqn, type_expr, parent = None, annotations = None, docs = ""):
    return make_type(TypeCategory.ALIAS_TYPE, fqn, type_args = [type_expr], 
                     parent = parent, annotations = annotations, docs = docs)

def make_type_fun(fqn, type_params, expr, parent, annotations = None, docs = ""):
    return TypeFun(fqn, type_params, expr, parent, annotations = None, docs = "")

def make_ref(fqn, target_fqn, parent = None, annotations = None, docs = None):
    return TypeRef(fqn, target_fqn, parent, annotations = annotations, docs = docs)

def make_type_app(type_func_expr, type_args, parent = None, annotations = None, docs = ""):
    if type(type_func_expr) in (str, unicode):
        type_func_expr = make_ref(None, type_func_expr)
    return TypeApp(type_func_expr, type_args, parent, annotations, docs)

KindType = make_literal_type("Type")
AnyType = make_literal_type("any")
VoidType = make_literal_type("void")
