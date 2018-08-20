
from enum import Enum
from ipdb import set_trace
from collections import defaultdict
from typecube import errors
from typecube.annotations import Annotatable, Annotation

class Expr(Annotatable):
    """ Expression base class.  """
    def __init__(self):
        Annotatable.__init__(self)
        self._free_variables = None
        self.inferred_type = None
        self.resolved_value = None

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

    def isany(self, cls):
        return isinstance(self, cls)

    def isa(self, cls):
        return type(self) == cls

class Type(Expr):
    """ Base Type interface. """
    def __init__(self, fqn):
        Expr.__init__(self)
        if fqn:
            if type(fqn) is not str: set_trace()
            assert type(fqn) is str
        self.fqn = fqn

    @property
    def name(self):
        return self.fqn.split(".")[-1]

class Literal(Expr):
    """ An expr that contains a literal value like a number, string, boolean, list, or map.  """
    def __init__(self, value, value_type):
        Expr.__init__(self)
        self.value = value
        self.value_type = value_type
        self.inferred_type = value_type
        self.resolved_value = self

    def __repr__(self):
        return "<0x%x - Lit: '%s'>" % (id(self), self.value)

class Var(Expr):
    """ An occurence of a name that can be bound to a value, a field or a type. """
    def __init__(self, fqn, is_typevar = False):
        Expr.__init__(self)
        if fqn:
            assert type(fqn) is str
        self.fqn = fqn
        self.is_typevar = is_typevar
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
        res = bindings.get(self.fqn, None)
        if res:
            if type(res) is str: return Var(res), True
            return res.clone(), True
        return Var(self.fqn), False

    def clone(self):
        return Var(self.fqn)

    def __repr__(self):
        return "<0x%x - Var: '%s'>" % (id(self), self.fqn)

class ExprList(Expr):
    """ A list of expressions. """
    def __init__(self, children = None):
        Expr.__init__(self)
        self.children = children or []

    def reduce(self, bindings):
        return ExprList([c.reduce(bindings) for c in self.children])

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

class SymbolTable(object):
    """ A symbol table for a particular abstraction.
    Includes locals, param names and output param name also.  This will be
    populated and verified by the semantic analyzer.
    """
    def __init__(self, params = None, return_param = None, fun_type = None):
        self.variables = {}
        if params:
            # Initialize all variable types to None
            for p in params:
                self.variables[p] = None
            if return_param:
                self.variables[return_param] = None
            if fun_type:
                assert len(params) == len(fun_type.source_types)
                for param,st in zip(params, fun_type.source_types):
                    self.variables[param] = st
                if fun_type.return_type and return_param:
                    self.variables[return_param] = fun_type.return_type

    def __contains__(self, value):
        return value in self.variables

    def type_for(self, varname):
        out = self.variables[varname]
        if not out: set_trace()
        while out.isa(Ref):
            out = out.contents
        return out

    def copy(self):
        out = SymbolTable()
        out.variables = self.variables.copy()
        return out

    def bound_params(self):
        return self.variables.keys()

    def is_bound(self, param):
        return param in self.variables

    def rename(self, **param_bindings):
        """ Renames bound parameters in this symbol table based on the mappings given in the "param_bindings" map. """
        if not param_bindings: return self
        for k,v in param_bindings.iteritems():
            if k in out.param_types:
                value = out.param_types[k]
                del out.param_types[k]
                out.param_type[v] = value
        return out

class Abs(Expr):
    """ Base of all abstractions/function expressions. """
    def __init__(self, params, expr, fqn = None, fun_type = None):
        Expr.__init__(self)
        self.fqn = fqn
        if type(expr) is str: expr = Var(expr)
        self.expr = expr
        if type(params) is str: params = [params]
        self.params = params
        self.return_param = None
        self.fun_type = fun_type
        self._symtable = None

    @property
    def symtable(self):
        if self._symtable is None:
            self._symtable = SymbolTable(self.params, self.return_param, self.fun_type)
        return self._symtable

    @symtable.setter
    def symtable(self, value):
        self._symtable = value

    def __repr__(self):
        return "<0x%x - %s(%s) { %s }>" % (id(self), self.__class__.__name__, ",".join(self.params), repr(self.expr))

    def clone(self):
        new_expr = None if not self.expr else self.expr.clone()
        fun_type = None if not self.fun_type else self.fun_type.clone()
        return self.copy_with(new_expr, fun_type)

    def generate_names(self, starting_name):
        for i in xrange(1000000):
            yield "%s_%d" % (starting_name, i)

    def apply(self, args):
        assert self.expr is not None
        args = [Var(a) if type(a) is str else a for a in args]

        # Calculate all free vars in the arguments
        arg_free_vars = set()
        for arg in args:
            arg_free_vars = arg_free_vars.union(free_variables(arg))

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
        out.symtable = self.symtable.copy()
        out.return_param = self.return_param
        out.fun_type = fun_type
        return out

    def rename_params(self, **param_bindings):
        """ Renames bound parameters in this symbol table based on the mappings given in the "param_bindings" map. """
        if not param_bindings: return self
        new_expr,reduced = self.expr.substitute(param_bindings)
        out = self.copy_with(new_expr, self.fun_type)
        out.symtable = out.symtable.rename(**param_bindings)

        for i,p in enumerate(out.params):
            if p in param_bindings:
                out.params[i] = param_bindings[p]
        out.return_param = param_bindings.get(out.return_param, out.return_param)
        return out

    def eval_param_renames(self, freevars):
        """ Return parameter renamings required for a capture free substitution.
        
        Given a bunch of free variables, returns any renamings required off this
        abstraction's bound variables such that the renamed values do not fall in the set of free variables of this expression or the free variables provided.
        """
        our_free_vars = free_variables(self)
        param_bindings = {}
        for y in self.bound_params():
            if y in freevars:
                for nextname in self.generate_names(y):
                    if nextname not in freevars and nextname not in our_free_vars:
                        param_bindings[y] = nextname
                        break
                assert param_bindings[y], "Param '%s' could not be renamed" % y
        return param_bindings

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

    def resolve_name(self, name):
        if name in self.symtable:
            return self.symtable.type_for(name)

    def var_type(self, varname):
        return self.temp_variables[str(varname)]

    def register_temp_var(self, varname, vartype):
        assert type(varname) is str
        if varname in self.params:
            raise TCException("Duplicate temporary variable '%s'.  Same as function arguments." % varname)
        elif varname == self.return_param:
            raise TCException("Duplicate temporary variable '%s'.  Same as function return argument name." % varname)
        elif self.is_temp_variable(varname) and self.temp_variables[varname] is not None:
            raise TCException("Duplicate temporary variable declared: '%s'" % varname)
        self.temp_variables[varname] = vartype

class Fun(Abs):
    """ An abstraction over expressions.  """
    pass

class Quant(Abs):
    """ A quantification or a generic function.
    
    Unlike normal functions (abstractions), which take terms/expressions as arguments, a Quantification takes types arguments
    and returns an expression with the arguments substituted with the types.
    """
    def __init__(self, params, expr, fqn = None, fun_type = None):
        Abs.__init__(self, params, expr, fqn, fun_type)
        # Set the values of params in the symbol table as we know source types.
        # We just dont know the return type
        for param in self.params:
            self.symtable.variables[param] = Ref(KindType)
        self.cases = []

    def addcase(self, case):
        """ Adds a new specialization of this quanitifer.

        A case contains (type_values, expr) which indicates the values for the type params
        along with a function or a variable pointing to a function that handles this case.
        """
        type_values, expr = case
        assert self.expr is None, "Cannot specialize a quantifier that already has a body."
        assert len(type_values) == len(self.params), "Partial quantifer specialization not yet allowed."
        self.cases.append(case)

class TypeOp(Abs):
    """ Type operators are "functions" over types.  
    They take proper types as arguments and return new types.  
    Type operators are NOT types, but just expressions (abstractions) that return types. """
    def __init__(self, params, expr, fqn = None):
        fun_type = None
        if not expr:
            fun_type = make_fun_type(None, [KindType] * len(params), KindType)
        else:
            assert expr.isany(Type)
        Abs.__init__(self, params, expr, fqn, fun_type)
        if not fun_type:
            # Set the values of params in the symbol table as we know source types.
            # We just dont konw the return type
            for param in self.params:
                self.symtable.variables[param] = Ref(KindType)

class App(Expr):
    """ Base of all application expressions. """
    def __init__(self, expr, *args):
        Expr.__init__(self)
        if type(expr) is str: expr = Var(expr)
        self.expr = expr
        if not all([(type(arg) is str or isinstance(arg, Expr)) for arg in args]):
            set_trace()
            assert(all([(type(arg) is str or isinstance(arg, Expr)) for arg in args]))
        self.args = [Var(arg) if type(arg) is str else arg for arg in args]

    def __repr__(self):
        return "<0x%x - %s - %s (%s)>" % (id(self), self.__class__.__name__, repr(self.expr), repr(self.args))

    def clone(self):
        return self.__class__(self.expr.clone(), *[arg.clone() for arg in self.args])

    def reduce_once(self):
        fun, fun_reduced = self.expr.resolved_value, self.expr.resolved_value != self.expr
        assert fun and fun.isany(Abs)
        set_trace()
        args,args_reduced = map(list, zip(*[a.reduce() for a in self.args]))
        if fun.isany(Abs) and not fun.is_external:
            # we are good, we can apply
            return fun.apply(args), True
        elif any([fun_reduced] + args_reduced):
            # Atleast one of fun or an arg was reducible so mark as progress
            return self.__class__(fun, *args), True
        else:
            # Nothing could be reduced so return ourselves
            return self, False

    def substitute(self, bindings):
        fun,fun_reduced = self.expr.substitute(bindings)
        args,args_reduced = map(list, zip(*[arg.substitute(bindings) for arg in self.args]))
        reduced = fun_reduced or any(args_reduced)
        return self.__class__(fun, *args), reduced

class FunApp(App): pass

class QuantApp(App):
    """ Application of a quantification to type expressions. """
    pass

class TypeApp(Type, App):
    """ Application of a type operator. 
    Unlike quantifications or functions, this returns a type when types are 
    passed as arguments.
    """
    def __init__(self, expr, *args):
        if type(expr) is str:
            expr = make_type_var(expr)
        App.__init__(self, expr, *args)
        Type.__init__(self, None)
        assert(all(t.isany(Type) or t.isa(Var) for t in args)), "All type args in a TypeApp must be Type sub classes or Vars"

class AtomicType(Type):
    def __init__(self, fqn):
        Type.__init__(self, fqn)
        self.inferred_type = KindType

    def substitute(self, bindings):
        return self

    def __repr__(self):
        return "<0x%x - AtomicType: %s>" % (id(self), self.fqn)

    def clone(self):
        return AtomicType(self.fqn, None, self.annotations, self.docs)

class Ref(Expr):
    """ Reference expressions. """
    def __init__(self, expr, annotations = None, docs = ""):
        Expr.__init__(self)
        self.set_annotations(annotations).set_docs(docs)
        self.contents = expr

class ContainerType(Type):
    def __init__(self, fqn, typerefs, params = None):
        Type.__init__(self, fqn)
        assert all([type(t) == Ref for t in typerefs])
        self.typerefs = typerefs
        self.is_labelled = False
        self.params = []
        if params:
            self.is_labelled = True
            self.params = params
        self.param_indices = dict([(v,i) for i,v in enumerate(self.params)])

    def __repr__(self):
        return "<0x%x - %s(%s) - %s<%s>(%s)>" % (id(self), self.__class__.__name__, self.tag, self.fqn, ",".join(self.params or []), ", ".join(map(repr, self.typerefs)))

    def type_for_param(self, param):
        return self.typerefs[self.param_indices[param]]

    def type_at_index(self, index):
        return self.typerefs[index]

    def substitute(self, bindings):
        typerefs = [typeexpr.substitute(bindings) for texpr in self.typerefs]
        return self.__class__(self.tag, self.fqn, typerefs, self.params)

class ProductType(ContainerType):
    def __init__(self, tag, fqn, typerefs, params = None):
        ContainerType.__init__(self, fqn, typerefs, params)
        self.tag = tag

class SumType(ContainerType):
    def __init__(self, tag, fqn, typerefs, params = None):
        ContainerType.__init__(self, fqn, typerefs, params)
        self.tag = tag

class FunType(Type):
    """ Represents function types.
    Note that function types do not reference the "names" of the function parameters.
    """
    def __init__(self, fqn, source_types, return_type):
        Type.__init__(self, fqn)
        source_types = [Ref(t) if not t.isa(Ref) else t for t in source_types]
        if return_type and not return_type.isa(Ref): return_type = Ref(return_type)
        self.return_type = return_type
        self.source_types = source_types

    def substitute(self, bindings):
        new_source_types = [st.substitute(bindings) for st in self.source_types]
        new_return_type = None if not self.return_type else self.return_type.substitute(bindings)
        return FunType(self.fqn, new_source_types, new_return_type, None)

def make_atomic_type(fqn):
    return AtomicType(fqn)

def make_product_type(tag, fqn, typerefs, params):
    return ProductType(tag, fqn, typerefs, params)

def make_sum_type(tag, fqn, typerefs, params):
    return SumType(tag, fqn, typerefs, params)

def make_fun_type(fqn, source_types, return_type):
    return FunType(fqn, source_types, return_type)

def make_type_op(fqn, type_params, expr):
    return TypeOp(type_params, expr, fqn = fqn)

def make_type_var(target_fqn):
    return Var(target_fqn)

def make_type_app(expr, *typeargs):
    return TypeApp(expr, *typeargs)

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

KindType = Type("")
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
                all(equiv(t1, t2, mapping12, mapping21) for t1,t2 in zip(expr1.args, expr2.args))
    assert False, "Unknown type"

def eprint(expr, level = 0):
    if expr.isa(Var):
        return expr.name
    elif expr.isa(App):
        return "%s(%s)" % (eprint(expr.expr), ", ".join(map(eprint, expr.args)))
    elif expr.isa(Abs):
        return "\(%s) { %s }" % (", ".join(expr.params), eprint(expr.expr))
    assert False


def free_variables(expr):
    if expr._free_variables is None:
        if expr.isa(Var):
            if "." in expr.fqn:
                expr._free_variables = {expr.fqn.split(".")[0]}
            else:
                expr._free_variables = {expr.fqn}
        elif expr.isany(Abs):
            out = free_variables(expr.expr)
            for param in expr.params:
                if param in out:
                    out.remove(param)
            if expr.return_param in out:
                out.remove(return_param)
            for param in expr.param_types.keys():
                if param in out:
                    out.remove(param)
            expr._free_variables = out
        elif expr.isany(App):
            out = set(free_variables(expr.expr))
            for arg in expr.args:
                out = out.union(free_variables(arg))
            expr._free_variables = out
        else:
            assert False
    return expr._free_variables
