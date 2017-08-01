
from enum import Enum
from ipdb import set_trace
from collections import defaultdict
from itertools import izip
from typecube import errors
from typecube.annotations import Annotatable

class Expr(Annotatable):
    """
    Parent of all exprs.  All exprs must have a value.  Exprs only appear in functions.
    """
    def __init__(self):
        Annotatable.__init__(self)
        self._free_variables = None

    def reduce(self):
        tmp = None
        curr, reduced = self.reduce_once()
        success = reduced
        while reduced:
            tmp = curr
            curr, reduced = curr.reduce_once()
            success = success or reduced
        return curr,success

    def reduce_once(self):
        return self, False

    @property
    def free_variables(self):
        if self._free_variables is None:
            self._free_variables = self.eval_free_variables()
        return self._free_variables

    def eval_free_variables(self):
        set_trace()
        assert False, "Not implemented"

    def isany(self, cls):
        return isinstance(self, cls)

    def isa(self, cls):
        return type(self) == cls

class Var(Expr):
    """ An occurence of a name that can be bound to a value, a field or a type. """
    def __init__(self, name):
        Expr.__init__(self)
        if type(name) not in (str, unicode): set_trace()
        assert type(name) in (str, unicode)
        self.name = name
        # The depth (or static depth or the de bruijn index) is the distance 
        # between the use of the variable and where it is defined.  
        # eg a static depth of 1 => definition within the immediate parent
        # -1 => undefined and needs to be calculated
        # 0/MAXINT => free variable
        self.depth = -1

        # The offset is the variable # within the parent where it is defined. 
        # This is only valid if the depth == 1
        self.offset = -1

    def substitute(self, bindings):
        res = bindings.get(self.name, None)
        if res:
            if type(res) in (str, unicode): return Var(res), True
            return res.clone(), True
        return Var(self.name), False

    def eval_free_variables(self):
        return {self.name}

    def clone(self):
        return Var(self.name)

    def __repr__(self):
        return "<Var - ID: 0x%x, Value: %s>" % (id(self), self.name)

class Type(Expr):
    """ Base Type interface. """
    def __init__(self, fqn):
        Expr.__init__(self)
        self.fqn = fqn

    @property
    def name(self):
        return self.fqn.split(".")[-1]

class Abs(Expr):
    """ Base of all abstractions/function expressions. """
    def __init__(self, params, expr, fqn = None, fun_type = None):
        Expr.__init__(self)
        self.fqn = fqn
        if type(expr) in (str, unicode): expr = Var(expr)
        self.expr = expr
        if type(params) in (str, unicode): params = [params]
        self.params = params
        self.return_param = "dest"
        self.fun_type = fun_type
        self.temp_variables = {}

    def __repr__(self):
        return "<%s(0x%x) Params(%s), Expr = %s>" % (self.__class__.__name__, id(self), ",".join(self.params), repr(self.expr))


    def clone(self):
        new_expr = None if not self.expr else self.expr.clone()
        fun_type = None if not self.fun_type else self.fun_type.clone()
        return self.copy_with(new_expr, fun_type)

    def generate_names(self, starting_name):
        for i in xrange(1000000):
            yield "%s_%d" % (starting_name, i)

    def rename_params(self, **param_bindings):
        """ Renames bound parameters in this Abstraction based on the mappings given in the "param_bindings" map. """
        if not param_bindings:
            return self
        new_expr,reduced = self.expr.substitute(param_bindings)
        out = self.copy_with(new_expr, self.fun_type)
        for i,p in enumerate(out.params):
            if p in param_bindings:
                out.params[i] = param_bindings[p]
        out.return_param = param_bindings.get(out.return_param, out.return_param)
        for k,v in param_bindings.iteritems():
            if k in out.temp_variables:
                value = out.temp_variables[k]
                del out.temp_variables[k]
                out.temp_variables[v] = value
        return out

    def bound_params(self):
        return set(self.params).union([self.return_param]).union(self.temp_variables.keys())

    def is_bound(self, param):
        return param in self.params or param == self.return_param or param in self.temp_variables

    def apply(self, args):
        assert self.expr is not None
        args = [Var(a) if type(a) in (str, unicode) else a for a in args]

        # Calculate all free vars in the arguments
        arg_free_vars = set()
        for arg in args:
            arg_free_vars = arg_free_vars.union(arg.free_variables)

        param_bindings = self.eval_param_renames(arg_free_vars)
        this = self.rename_params(**param_bindings)
        bindings = dict(zip(this.params, args))

        out, reduced = this.expr.substitute(bindings)

        left_params = []
        source_types = []
        for index,param in enumerate(this.params):
            if param not in bindings:
                if this.fun_type:
                    source_types.append(this.fun_type.source_types[index])
                left_params.append(param)
        if left_params:
            # Since not all params have been applied, we do function currying!
            new_fun_type = None
            if this.fun_type:
                new_fun_type = FunType(this.fun_type.fqn, source_types, this.fun_type.return_type)
            out = this.__class__(left_params, out, this.fqn, None, new_fun_type)
        return out

    def substitute(self, bindings):
        # No bindings - nothing to be done
        new_fun_type,fun_reduced = None,False
        if self.fun_type:
            new_fun_type,fun_reduced = self.fun_type.substitute(bindings)

        bindings = {k:v for k,v in bindings.iteritems() if k not in self.params}
        if not bindings or not self.expr:
            out = self.copy_with(self.expr, new_fun_type)
            return out, out != self

        new_expr,expr_reduced = self.expr.substitute(bindings)
        return self.copy_with(new_expr, new_fun_type), True

    def copy_with(self, expr, fun_type = None):
        if expr == self.expr and fun_type == self.fun_type: return self
        out = self.__class__(self.params, expr, self.fqn)
        out.temp_variables = self.temp_variables.copy()
        out.return_param = self.return_param
        out.fun_type = fun_type
        return out

    def eval_param_renames(self, freevars):
        """ Return parameter renamings required for a capture free substitution.
        
        Given a bunch of free variables, returns any renamings required off this
        abstraction's bound variables such that the renamed values do not fall in the set of free variables of this expression or the free variables provided.
        """
        our_free_vars = self.free_variables
        param_bindings = {}
        for y in self.bound_params():
            if y in freevars:
                for nextname in self.generate_names(y):
                    if nextname not in freevars and nextname not in our_free_vars:
                        param_bindings[y] = nextname
                        break
                assert param_bindings[y], "Param '%s' could not be renamed" % y
        return param_bindings

    def eval_free_variables(self):
        out = self.expr.free_variables
        for param in self.params:
            if param in out:
                out.remove(param)
        if self.return_param in out:
            out.remove(return_param)
        for param in self.temp_variables:
            if param in out:
                out.remove(param)
        return out

    @property
    def name(self):
        return None if not self.fqn else self.fqn.split(".")[-1]

    @property
    def is_external(self): return self.expr is None

    def reduce_once(self):
        expr, reduced = self.expr.reduce()
        fun_type, fun_reduced = None, False,
        if self.fun_type:
            fun_type, fun_reduced  = self.fun_type.reduce()
        if reduced or fun_reduced:
            return self.copy_with(expr, fun_type), True
        else:
            return self, False

    def _resolve_name(self, name, condition = None):
        """ Try to resolve a name to a local, source or destination variable. """
        # Check source types
        for index,param in enumerate(self.params):
            if param == name:
                typeexpr = self.fun_type.source_types
                if condition is None or condition(typeexpr):
                    if typeexpr == KindType:
                        # TODO: *something?*, perhaps return param name as a type?
                        # return make_atomic_type(arg.name)
                        # set_trace()
                        pass
                    return self,typeexpr

        if param == self.return_param:
            # Check if this is the "output" arg
            return fun_type.return_type

        if self.is_temp_variable(name):
            # Check local variables
            return self,self.temp_var_type(name)

    def is_temp_variable(self, varname):
        return varname in self.temp_variables

    def temp_var_type(self, varname):
        return self.temp_variables[str(varname)]

    def register_temp_var(self, varname, vartype = None):
        assert type(varname) in (str, unicode)
        if varname in self.params:
            raise TLException("Duplicate temporary variable '%s'.  Same as function arguments." % varname)
        elif varname == self.return_param:
            raise TLException("Duplicate temporary variable '%s'.  Same as function return argument name." % varname)
        elif self.is_temp_variable(varname) and self.temp_variables[varname] is not None:
            raise TLException("Duplicate temporary variable declared: '%s'" % varname)
        self.temp_variables[varname] = vartype

class Fun(Abs):
    """ An abstraction over expressions.  """
    def _reduce(self):
        new_fun_type = self.fun_type.resolve()
        resolved_expr = None if not self.expr else self.expr.resolve()
        if new_fun_type == self.fun_type and resolved_expr == self.expr:
            return self
        out = Fun(self.params, resolved_expr, self.fqn, new_fun_type)
        return out

class Quant(Abs):
    """ A quantification or a generic function.
    
    Unlike normal functions (abstractions), which take terms/expressions as arguments, a Quantification takes types arguments
    and returns an expression with the arguments substituted with the types.
    """
    def __init__(self, params, expr, fqn = None):
        fun_type = make_fun_type(None, [KindType] * len(params), KindType, self)
        Abs.__init__(self, params, expr, fqn, fun_type)

    def _reduce(self):
        resolved_expr = None if not self.expr else self.expr.resolve()
        if resolved_expr == self.expr:
            return self
        out = Quant(self.params, resolved_expr, self.fqn, self.fun_type)
        return out

class TypeOp(Abs):
    """ Type operators are "functions" over types.  
    They take proper types as arguments and return new types.  
    Type operators are NOT types, but just expressions (abstractions) that return types. """
    def __init__(self, params, expr, fqn = None):
        fun_type = make_fun_type(None, [KindType] * len(params), KindType)
        Abs.__init__(self, params, expr, fqn, fun_type)
        assert not expr or expr.isany(Type)

    def _reduce(self):
        resolved_expr = None if not self.expr else self.expr.resolve()
        if resolved_expr == self.expr:
            return self
        out = Quant(self.params, resolved_expr, self.fqn, self.fun_type)
        return out

class App(Expr):
    """ Base of all application expressions. """
    def __init__(self, expr, args):
        Expr.__init__(self)
        if type(expr) in (str, unicode): expr = Var(expr)
        self.expr = expr

        if args and type(args) is not list: args = [args]
        for i,arg in enumerate(args):
            if type(arg) in (str, unicode): arg = Var(arg)
            if not isinstance(arg, Expr): set_trace()
        self.args = args

    def eval_free_variables(self):
        out = set(self.expr.free_variables)
        for arg in self.args:
            out = out.union(arg.free_variables)
        return out

    def __repr__(self):
        return "<%s(0x%x) Expr = %s, Args = (%s)>" % (self.__class__.__name__, id(self), repr(self.expr), ", ".join(map(repr, self.args)))

    def clone(self):
        return self.__class__(self.expr.clone(), [arg.clone() for arg in self.args])

    def reduce_once(self):
        fun, fun_reduced = self.expr.reduce()
        args,args_reduced = map(list, zip(*[a.reduce() for a in self.args]))
        if fun.isany(Abs) and not fun.is_external:
            # we are good, we can apply
            return fun.apply(args), True
        elif any([fun_reduced] + args_reduced):
            # Atleast one of fun or an arg was reducible so mark as progress
            return self.__class__(fun, args), True
        else:
            # Nothing could be reduced so return ourselves
            return self, False

    def substitute(self, bindings):
        fun,fun_reduced = self.expr.substitute(bindings)
        args,args_reduced = map(list, zip(*[arg.substitute(bindings) for arg in self.args]))
        reduced = fun_reduced or any(args_reduced)
        return self.__class__(fun, args), reduced

class FunApp(App):
    pass

class QuantApp(App):
    """ Application of a quantification to type expressions. """
    def resolve_function(self):
        fun, args = App.resolve_function(self)
        if not fun.isa(Quant):
            raise errors.TLException("'%s' is not a type operator" % typefun)
        return fun,args

class TypeApp(Type, App):
    """ Application of a type operator. 
    Unlike quantifications or functions, this returns a type when types are 
    passed as arguments.
    """
    def __init__(self, expr, args):
        if type(expr) in (str, unicode):
            expr = make_ref(expr)
        App.__init__(self, expr, args)
        Type.__init__(self, None)
        assert(all(t.isany(Type) for t in args)), "All type args in a TypeApp must be Type sub classes"

    def resolve_function(self):
        fun, args = App.resolve_function(self)
        if not fun.isa(TypeOp):
            raise errors.TLException("'%s' is not a type operator" % typefun)
        return fun,args

class AtomicType(Type):
    def substitute(self, bindings):
        return self

    def clone(self):
        return AtomicType(self.fqn, None, self.annotations, self.docs)

class AliasType(Type):
    def __init__(self, fqn, target_type):
        Type.__init__(self, fqn)
        self.target_type = target_type
        assert self.target_type.isany(Type)

    def clone(self):
        return make_alias(self.fqn, self.target_type, None, self.annotations, self.docs)

class AnnotatedExpr(Annotatable):
    def __init__(self, expr, name = None, is_optional = False, default_value = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.default_value = default_value
        self.is_optional = is_optional
        self.expr = expr
        self.name = name

class ContainerType(Type):
    def __init__(self, fqn, typeargs):
        Type.__init__(self, fqn)
        assert all([type(t) == AnnotatedExpr for t in typeargs])
        self.typeargs = typeargs
        self.is_labelled = False
        self.params = []
        if typeargs and typeargs[0].name:
            self.is_labelled = True
            self.params = [t.name for t in typeargs]
        self.param_indices = dict([(v,i) for i,v in enumerate(self.params)])

    def type_for_param(self, param):
        return self.typeargs[self.param_indices[param]]

    def substitute(self, bindings):
        typeargs = [typeexpr.substitute(bindings) for texpr in self.typeargs]
        return self.__class__(self.tag, self.fqn, typeargs)

class ProductType(ContainerType):
    def __init__(self, tag, fqn, typeargs):
        ContainerType.__init__(self, fqn, typeargs)
        self.tag = tag

class SumType(ContainerType):
    def __init__(self, tag, fqn, typeargs):
        ContainerType.__init__(self, fqn, typeargs)
        self.tag = tag

class FunType(Type):
    """ Represents function types.
    Note that function types do not reference the "names" of the function parameters.
    """
    def __init__(self, fqn, source_types, return_type):
        Type.__init__(self, fqn)
        self.return_type = return_type
        self.source_types = source_types

    def substitute(self, bindings):
        new_source_types = [st.substitute(bindings) for st in self.source_types]
        new_return_type = None if not self.return_type else self.return_type.substitute(bindings)
        return FunType(self.fqn, new_source_types, new_return_type, None)

class TypeRef(Type):
    def substitute(self, bindings):
        if self.name in bindings:
            return bindings[self.fqn].clone()
        return self.clone()

    @property
    def final_type(self):
        curr = self
        while curr and curr.isa(TypeRef):
            curr = curr.resolve()
        return curr

    def clone(self):
        return make_ref(self.fqn, None, self.annotations, self.docs)

    def _reduce(self):
        return self.resolve_name(self.fqn)

def make_atomic_type(fqn):
    return AtomicType(fqn)

def make_product_type(tag, fqn, typeargs):
    return ProductType(tag, fqn, typeargs)

def make_sum_type(tag, fqn, typeargs):
    return SumType(tag, fqn, typeargs)

def make_fun_type(fqn, source_types, return_type):
    return FunType(fqn, source_types, return_type)

def make_alias(fqn, target_type):
    return AliasType(fqn, target_type)

def make_type_op(fqn, type_params, expr):
    return TypeOp(type_params, expr, fqn = fqn)

def make_ref(target_fqn):
    return TypeRef(target_fqn)

def make_type_app(expr, typeargs):
    return TypeApp(expr, typeargs)

def make_enum_type(fqn, symbols):
    typeargs = []
    for name,value,sym_annotations,sym_docs in symbols:
        ta = TypeArg(name, VoidType, False, value)
        ta.set_annotations(sym_annotations).set_docs(sym_docs)
        typeargs.append(ta)
    out = SumType("enum", fqn, typeargs)
    for ta in typeargs:
        ta.expr = out
    return out

KindType = make_atomic_type("Type")
AnyType = make_atomic_type("any")
VoidType = make_atomic_type("void")

def equiv(expr1, expr2, mapping12 = None, mapping21 = None):
    """ Checks if two exprs are equivalent. """
    if expr1 == expr2: return True
    if type(expr1) != type(expr2): return False
    if mapping12 is None: mapping12 = {}
    if mapping21 is None: mapping21 = {}

    if type(expr1) is Var:
        if expr1.name in mapping12 and expr2.name in mapping21:
            return expr2.name == mapping12[expr1.name] and mapping21[expr2.name] == expr1.name
        elif expr1.name not in mapping12 and expr2.name not in mapping21:
            mapping12[expr1.name] = expr2.name
            mapping21[expr2.name] = expr1.name
            return True
        else:
            return False
    elif isinstance(expr1, Abs):
        if expr1.fqn != expr2.fqn: return False
        return equiv(expr1.fun_type, expr2.fun_type, mapping12, mapping21) and \
                equiv(expr1.expr, expr2.expr, mapping12, mapping21)
    elif isinstance(expr1, App):
        return equiv(expr1.expr, expr2.expr, mapping12, mapping21) and \
                all(equiv(t1, t2, mapping12, mapping21) for t1,t2 in izip(expr1.args, expr2.args))
    assert False, "Unknown type"

def eprint(expr, level = 0):
    if expr.isa(Var):
        return expr.name
    elif expr.isa(App):
        return "%s(%s)" % (eprint(expr.expr), ", ".join(map(eprint, expr.args)))
    elif expr.isa(Abs):
        return "\(%s) { %s }" % (", ".join(expr.params), eprint(expr.expr))
    assert False

