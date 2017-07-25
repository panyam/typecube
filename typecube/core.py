
from enum import Enum
from ipdb import set_trace
from collections import defaultdict
from itertools import izip
from typecube import errors
from typecube.utils import FieldPath
from typecube.annotations import Annotatable

def istype(t): return issubclass(t.__class__, Type)

class NameResolver(object):
    def resolve_name(self, name, condition = None):
        """ Tries to resolve a name in this expression. """
        value = self._resolve_name(name, condition)
        if value and (condition is None or condition(value)):
            return value
        if self.parent:     # Try the parent expression
            return self.parent.resolve_name(name, condition)
        raise errors.TLException("Unable to resolve name: %s" % name)

class Expr(NameResolver):
    """
    Parent of all exprs.  All exprs must have a value.  Exprs only appear in functions.
    """
    def __init__(self, parent = None):
        self._parent = parent

    def isany(self, cls):
        return isinstance(self, cls)

    def isa(self, cls):
        return type(self) == cls

    def clear_parent(self):
        """ Clears the parent of an expression.
        This is an explicit method instead of a "force" option in set_parent
        so that the caller is cognizant of doing this.
        """
        if self.parent:
            oldvalue = self._parent
            self._parent = None
            self.parent_changed(oldvalue)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self.set_parent(value)

    def set_parent(self, value):
        if self.validate_parent(value):
            oldvalue = self._parent
            self._parent = value
            self.parent_changed(oldvalue)

    def validate_parent(self, value):
        if self._parent is not None and value != self._parent:
            set_trace()
        return True

    def parent_changed(self, oldvalue):
        pass

    #########
    def ensure_parents(self):
        """ Ensures that all children have the parents setup correctly.  
        Assumes that the parent of this expression is set corrected before this is called.
        """
        assert self.parent is not None
        pass

    def resolve_name(self, name, condition = None):
        if self.parent is None:
            set_trace()
            assert self.parent is not None, "Parent of %s is None" % type(self)
        return NameResolver.resolve_name(self, name, condition)

    def _resolve_name(self, name, condition = None):
        return None

    def resolve(self):
        # Do caching of results here based on resolver!
        return self._resolve()

    def _resolve(self):
        """ This method resolves a type expr to a type object. 
        The resolver is used to get bindings for names used in this expr.
        
        Returns a ResolvedValue object that contains the final expr value after resolution of this expr.
        """
        set_trace()
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

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.field_path))

    def _resolve(self):
        """
        Returns the actual entry pointed to by the "first" part of the field path.
        """
        first = self.field_path.get(0)
        target = self.resolve_name(first)
        if target is None:
            assert target is not None, "Could not resolve '%s'" % first
        return target

class Abs(Expr):
    """ Base of all abstractions/function expressions. """
    def __init__(self, fqn, expr, parent, fun_type):
        Expr.__init__(self, parent)
        self.fqn = fqn
        self._expr = None
        self.expr = expr
        self.fun_type = fun_type
        if self.fun_type:
            self.fun_type.parent = self

    @property
    def expr(self):
        return self._expr

    @expr.setter
    def expr(self, value):
        if self._expr:
            # Set old expr's parent to None
            # TODO - This has to be forced
            self._expr.parent = None
        self._expr = value
        if value:
            value.parent = self

    @property
    def name(self):
        return self.fqn.split(".")[-1]

    @property
    def is_external(self): return self.expr is None

    def apply(self, args):
        assert self.expr is not None
        bindings = dict(zip(self.params, args))
        return self.expr.reduce_with_bindings(bindings, self.parent)

    def _resolve_name(self, name, condition = None):
        """ Try to resolve a name to a local, source or destination variable. """
        # Check source types
        fun_type = self.fun_type
        for arg in self.fun_type.source_typeargs:
            if arg.name == name:
                if condition is None or condition(arg.expr):
                    if arg.expr == KindType:
                        # TODO: *something?*, perhaps return param name as a type?
                        # return make_atomic_type(arg.name)
                        # set_trace()
                        pass
                    return arg.expr

        # Check if this is the "output" arg
        if fun_type.return_typearg and fun_type.return_typearg.name == name:
            return fun_type.return_typearg.expr

class App(Expr):
    """ Base of all application expressions. """
    def __init__(self, expr, args):
        Expr.__init__(self)
        self.expr = expr
        self.args = args
        self.expr = expr
        if args and type(args) is not list:
            args = [args]
        self.args = args
        self.expr.parent = self
        for arg in self.args:
            arg.parent = self

    def __repr__(self):
        return "<%s(0x%x) Expr = %s, Args = (%s)>" % (self.__class__.name, id(self), repr(self.expr), ", ".join(map(repr, self.args)))

    def resolve_function(self):
        function = self.expr.resolve()
        if not function:
            raise errors.TLException("Fun '%s' is undefined" % (self.expr))
        while function.isany(Type) and type.is_alias:
            assert len(function.args) == 1, "Typeref cannot have more than one child argument"
            function = function.args[0].expr.resolve()
        if not function.isany(Abs):
            set_trace()
            raise errors.TLException("'%s' is not an Abstraction" % (self.expr))
        arg_values = [arg.resolve() for arg in self.args]

        # Wont do currying for now
        if len(arg_values) != len(function.fun_type.source_typeargs):
            raise errors.TLException("Fun '%s' takes %d arguments, but encountered %d.  Currying or var args NOT YET supported." %
                                            (function.name, len(function.source_typeargs), len(self.args)))
        return function, arg_values

    def reduce_with_bindings(self, bindings, parent):
        newfun = self.expr.reduce_with_bindings(None, bindings)
        newargs = [arg.reduce_with_bindings(None, bindings) for arg in self.args]
        return make_type_app(new_typefun, new_typeargs, parent, self.annotations, self.docs)

    def _resolve(self):
        """ Resolves a type application. 
        This will apply the arguments to the function expression.

        TODO: Discuss variable capture
        """
        fun,args = self.resolve_function()
        if fun.is_external:
            # Cannot apply for external types so just return ourselves 
            # as no further application is possible
            return self
        return fun.apply(args)

class Fun(Abs, Annotatable):
    """ An abstraction over expressions.  """
    def __init__(self, fqn, expr, fun_type, parent, annotations = None, docs = ""):
        Abs.__init__(self, fqn, expr, parent, fun_type)
        Annotatable.__init__(self, annotations, docs)
        self.temp_variables = {}

    @property
    def params(self): return [ta.name for ta in self.fun_type.source_typeargs]

    def _resolve_name(self, name, condition = None):
        value = Abs._resolve_name(self, name, condition)
        if value: return value
        elif self.is_temp_variable(name):
            # Check local variables
            return self.temp_var_type(name)

    def _resolve(self):
        """
        The main resolver method.  This should take care of the following:

            1. Ensure field paths are correct
            2. All exprs have their evaluated types set
        """
        new_fun_type = self.fun_type.resolve()
        resolved_expr = None if not self.expr else self.expr.resolve()
        if new_fun_type == self.fun_type and resolved_expr == self.expr:
            return self
        out = Fun(self.fqn, resolved_expr, new_fun_type, self.parent, self.annotations, self.docs)
        return out

    def is_temp_variable(self, varname):
        return varname in self.temp_variables

    def temp_var_type(self, varname):
        return self.temp_variables[str(varname)]

    def register_temp_var(self, varname, vartype = None):
        assert type(varname) in (str, unicode)
        if varname in (x.name for x in self.fun_type.source_typeargs):
            raise TLException("Duplicate temporary variable '%s'.  Same as function arguments." % varname)
        elif self.fun_type.return_typearg and varname == self.fun_type.return_typearg.name:
            raise TLException("Duplicate temporary variable '%s'.  Same as function return argument name." % varname)
        elif self.is_temp_variable(varname) and self.temp_variables[varname] is not None:
            raise TLException("Duplicate temporary variable declared: '%s'" % varname)
        self.temp_variables[varname] = vartype

class FunApp(App):
    """ Super class of all applications """
    def __init__(self, expr, args = None):
        App.__init__(self, expr, args)
        self.args = args

    def __repr__(self):
        return "<FunApp(0x%x) Expr = %s, Args = (%s)>" % (id(self), repr(self.expr), ", ".join(map(repr, self.args)))

    def _resolve(self):
        """
        Processes an exprs and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # First resolve the expr to get the source function
        # Here we need to decide if the function needs to be "duplicated" for each different type
        # This is where type re-ification is important - both at buildtime and runtime
        fun, args = self.resolve_function()

        # TODO - check arg types match
        if fun != self.expr or any(x != y for x,y in zip(args, self.args)):
            # Only return a new expr if any thing has changed
            return FunApp(fun, args)
        return self

class Type(Expr, Annotatable):
    def __init__(self, fqn, parent, annotations = None, docs = ""):
        """
        Creates a new type function.  Type functions are responsible for creating concrete type instances
        or other (curried) type functions.

        Params:
            fqn             FQN of the type.
            parent          A reference to the parent container entity of this type.
            annotations     Annotations applied to the type.
            docs            Documentation string for the type.
        """
        Expr.__init__(self, parent)
        Annotatable.__init__(self, annotations = annotations, docs = docs)

        # tag can indicate a further specialization of the type - eg "record", "enum" etc
        self.tag = None
        self.fqn = fqn

    @property
    def name(self):
        return self.fqn.split(".")[-1]

class AtomicType(Type):
    def reduce_with_bindings(self, bindings, parent = None):
        return self

    def deepcopy(self, newparent):
        return AtomicType(self.fqn, newparent, self.annotations, self.docs)

    def validate_parent(self, value):
        """ With atomic types once the parent is set, we dont want them changed. """
        return self.parent is None

class AliasType(Type):
    def __init__(self, fqn, target_type, parent, annotations = None, docs = ""):
        Type.__init__(self, fqn, parent, annotations, docs)
        self.target_type = target_type
        assert istype(self.target_type)

    def deepcopy(self, newparent):
        return make_alias(self.fqn, self.target_type, newparent, self.annotations, self.docs)

class ContainerType(Type):
    def __init__(self, fqn, typeargs, parent, annotations = None, docs = ""):
        Type.__init__(self, fqn, parent, annotations, docs)
        self.args = typeargs
        for arg in self.args:
            arg.parent = self

    def reduce_with_bindings(self, bindings, parent = None):
        typeargs = [TypeArg(ta.name, ta.expr.reduce_with_bindings(bindings),
                            ta.is_optional, ta.default_value, ta.annotations, ta.docs) for ta in self.args]
        return self.__class__(self.tag, self.fqn, typeargs, parent, self.annotations, self.docs)


class ProductType(ContainerType):
    def __init__(self, tag, fqn, typeargs, parent, annotations = None, docs = ""):
        ContainerType.__init__(self, fqn, typeargs, parent, annotations, docs)
        self.tag = tag

    def deepcopy(self, newparent):
        return ProductType(self.tag, self.fqn, [ta.deepcopy(None) for ta in self.args], newparent, self.annotations, self.docs)

class SumType(ContainerType):
    def __init__(self, tag, fqn, typeargs, parent, annotations = None, docs = ""):
        ContainerType.__init__(self, fqn, typeargs, parent, annotations, docs)
        self.tag = tag

    def deepcopy(self, newparent):
        return SumType(self.tag, self.fqn, [ta.deepcopy(None) for ta in self.args], newparent, self.annotations, self.docs)

class FunType(Type):
    """ Represents function types.
    Note that function types do not reference the "names" of the function parameters.
    """
    def __init__(self, fqn, source_typeargs, return_typearg, parent, annotations = None, docs = ""):
        Type.__init__(self, fqn, parent, annotations, docs)
        self.return_typearg = return_typearg
        self.source_typeargs = source_typeargs
        for arg in self.source_typeargs:
            if not arg.parent:
                arg.parent = self
        if self.return_typearg and not self.return_typearg.parent:
            self.return_typearg.parent = self

    def reduce_with_bindings(self, bindings, parent = None):
        new_source_typeargs = [st.reduce_with_bindings(bindings) for st in self.source_typeargs]
        new_return_typearg = None if not self.return_typearg else self.return_typearg.reduce_with_bindings(bindings)
        return FunType(fqn, new_source_typeargs, new_return_typearg, parent, self.annotations, self.docs)

class TypeRef(Type):
    def reduce_with_bindings(self, bindings, parent):
        if self.fqn in bindings:
            return bindings[self.fqn].deepcopy(parent)
        return self.deepcopy(parent)

    @property
    def final_type(self):
        curr = self
        while curr and curr.isa(TypeRef):
            curr = curr.resolve()
        return curr

    def deepcopy(self, newparent):
        return make_ref(self.fqn, newparent, self.annotations, self.docs)

    def _resolve(self):
        return self.resolve_name(self.fqn)

class Quant(Fun):
    """ A quantification or a generic function.
    
    Unlike normal functions (abstractions), which take terms/expressions as arguments, a Quantification takes types arguments
    and returns an expression with the arguments substituted with the types.
    """
    def __init__(self, fqn, params, expr, parent, annotations = None, docs = ""):
        fun_type = make_fun_type(None, [TypeArg(p, KindType) for p in params], TypeArg(None, KindType), self)
        Fun.__init__(self, fqn, expr, fun_type, parent, annotations, docs)

class QuantApp(App):
    """ Application of a quantification to type expressions. """
    def __init__(self, expr, args = None):
        App.__init__(self, expr, args)
        self.args = args

    def resolve_function(self):
        fun, args = App.resolve_function(self)
        if not fun.isa(Quant):
            raise errors.TLException("'%s' is not a type operator" % typefun)
        return fun,args

class TypeOp(Fun):
    """ Type operators are "functions" over types.  They take proper types as arguments and return new types.  
    Type operators are NOT types, but just expressions (abstractions) that return types. """
    def __init__(self, fqn, params, expr, parent, annotations = None, docs = ""):
        fun_type = make_fun_type(None, [TypeArg(p, KindType) for p in params], TypeArg(None, KindType), self)
        Fun.__init__(self, fqn, expr, fun_type, parent, annotations, docs)
        assert not expr or expr.isany(Type)

class TypeApp(Type, App):
    """ Application of a type operator. Unlike quantifications or functions, 
    this returns a type when types are passed as arguments. """
    def __init__(self, expr, args, parent, annotations = None, docs = ""):
        if type(expr) in (str, unicode):
            expr = make_ref(expr)
        App.__init__(self, expr, args)
        Type.__init__(self, None, parent, annotations = None, docs = "")
        assert(all(istype(t) for t in args)), "All type args in a TypeApp must be Type sub classes"

    def resolve_function(self):
        fun, args = App.resolve_function(self)
        if not fun.isa(TypeOp):
            raise errors.TLException("'%s' is not a type operator" % typefun)
        return fun,args

class TypeArg(Expr, Annotatable):
    """ A type argument is a child of a given type.  Akin to a member/field of a type.  """
    def __init__(self, name, expr, is_optional = False, default_value = None, annotations = None, docs = ""):
        Expr.__init__(self, None)
        Annotatable.__init__(self, annotations, docs)
        self.name = name
        self.is_optional = is_optional
        self.default_value = default_value or None
        assert expr.isany(Type)
        self.expr = expr
        if not self.expr.parent:
            self.expr.parent = self

    def deepcopy(self, newparent):
        return TypeArg(self.name, self.expr.deepcopy(newparent), self.is_optional, self.default_value, self.annotations, self.docs)

    def _resolve(self):
        out = self
        if self.expr is None:
            return self
        new_expr = self.expr.resolve()
        if new_expr != self.expr:
            out =  TypeArg(self.name, new_expr, self.is_optional, self.docs, annotations = self.annotations, docs = self.docs)
        return out

    def unwrap_with_field_path(self, full_field_path):
        starting_var, field_path = full_field_path.pop()
        curr_typearg = self
        curr_path = curr_field_name = starting_var
        yield curr_field_name, curr_path, curr_typearg
        while field_path.length > 0:
            next_field_name, tail_path = field_path.pop()
            next_path = curr_path + "/" + next_field_name
            next_typearg = curr_typearg.expr.resolve().args.withname(next_field_name)
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
    def __init__(self, typeargs):
        self._typeargs = []
        for typearg in typeargs or []:
            self.add(typearg)

    def equals(self, another):
        return len(self._typeargs) == len(self._typeargs) and all(x.equals(y) for x,y in izip(self._typeargs, another._typeargs))

    def __getitem__(self, slice):
        return self._typeargs.__getitem__(slice)

    def __iter__(self): return iter(self._typeargs)

    def __len__(self): return len(self._typeargs)

    def __repr__(self):
        return repr(self._typeargs)

    @property
    def count(self): return len(self._typeargs)

    def index_for(self, name):
        for i,arg in enumerate(self._typeargs):
            if arg.name == name:
                return i
        return -1

    def withname(self, name):
        return self.atindex(self.index_for(name))

    def atindex(self, index):
        return None if index < 0 else self._typeargs[index]

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
        self._typeargs.append(arg)

def make_atomic_type(fqn, parent = None, annotations = None, docs = ""):
    return AtomicType(fqn, parent, annotations, docs)

def make_product_type(tag, fqn, typeargs, parent = None, annotations = None, docs = ""):
    return ProductType(tag, fqn, typeargs, parent, annotations = None, docs = "")

def make_sum_type(tag, fqn, typeargs, parent = None, annotations = None, docs = ""):
    return SumType(tag, fqn, typeargs, parent, annotations = None, docs = "")

def make_fun_type(fqn, source_typeargs, return_typearg, parent = None, annotations = None, docs = ""):
    return FunType(fqn, source_typeargs, return_typearg, parent, annotations, docs)

def make_alias(fqn, target_type, parent = None, annotations = None, docs = ""):
    return AliasType(fqn, target_type, parent, annotations, docs)

def make_type_op(fqn, type_params, expr, parent, annotations = None, docs = ""):
    return TypeOp(fqn, type_params, expr, parent, annotations = None, docs = "")

def make_ref(target_fqn, parent = None, annotations = None, docs = None):
    return TypeRef(target_fqn, parent, annotations = annotations, docs = docs)

def make_type_app(expr, typeargs, parent = None, annotations = None, docs = ""):
    return TypeApp(expr, typeargs, parent, annotations, docs)

def make_enum_type(fqn, symbols, parent = None, annotations = None, docs = None):
    typeargs = []
    for name,value,sym_annotations,sym_docs in symbols:
        typeargs.append(TypeArg(name, VoidType, False, value, sym_annotations, sym_docs))
    out = SumType("enum", fqn, typeargs, parent, annotations = annotations, docs = docs)
    for ta in typeargs:
        ta.expr = out
    return out

KindType = make_atomic_type("Type")
AnyType = make_atomic_type("any")
VoidType = make_atomic_type("void")
