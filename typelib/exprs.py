
import ipdb
from itertools import izip
from enum import Enum
from typelib import errors
from typelib.utils import FieldPath
from typelib import core as tlcore
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier

class Expression(object):
    """
    Parent of all expressions.  All expressions must have a value.  Expressions only appear in functions.
    """
    def __init__(self):
        self._evaluated_typeexpr = None
        self.resolver = None
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

    @property
    def resolved_value(self):
        if self._resolved_value is None:
            if self.resolver is None:
                ipdb.set_trace()
            assert self.resolver is not None
            self._resolved_value = self.resolve()
            assert self._resolved_value is not None, "Invalid resolved value for expression: '%s'" % repr(self)
        return self._resolved_value

    def resolve(self):
        """Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        assert False, "Not Implemented"
        return None

    def resolve_bindings_and_types(self, parent_function):
        """Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        pass

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        # Forbid changing of resolvers for now
        assert self.resolver is None
        self.resolver = resolver

    def resolve_type_name(self, name):
        return self.resolver.resolve_type_name(name)

    def resolve_name(self, name):
        return None if not self.resolver else self.resolver.resolve_name(name)

class Statement(Expression):
    def __init__(self, expressions, target_variable, is_temporary = False):
        Expression.__init__(self)
        self.expressions = expressions
        self.target_variable = target_variable
        self.target_variable.is_temporary = is_temporary or target_variable.field_path.get(0) == '_'
        self.is_implicit = False
        if self.target_variable.is_temporary:
            assert target_variable.field_path.length == 1, "A temporary variable cannot have nested field paths"

    @property
    def is_temporary(self):
        return self.target_variable and self.target_variable.is_temporary

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        # Forbid changing of resolvers for now
        Expression.set_resolver(self, resolver)
        for expr in self.expressions:
            expr.set_resolver(resolver)

    def resolve_bindings_and_types(self, parent_function):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve the target variable's binding.  This does'nt necessarily have
        # to evaluate types.
        # This will help us with type inference going backwards
        if not self.is_temporary:
            self.target_variable.resolve_bindings_and_types(parent_function)

        # Resolve all types in child expressions.  
        # Apart from just evaluating all child expressions, also make sure
        # Resolve field paths that should come from source type
        for expr in self.expressions:
            expr.resolve_bindings_and_types(parent_function)

        last_expr = self.expressions[-1]
        if self.target_variable.is_temporary:
            varname = str(self.target_variable.field_path)
            if varname == "_":
                self.target_variable = None
            else:
                # Resolve field paths that should come from dest type
                self.target_variable.evaluated_typeexpr = last_expr.evaluated_typeexpr
                parent_function.register_temp_var(varname, last_expr.evaluated_typeexpr)

class VariableExpression(Expression):
    def __init__(self, field_path):
        super(VariableExpression, self).__init__()
        # Whether we are a temporary local var
        self.is_temporary = False
        # Whether a resolved value is a function
        self.is_function = False
        self.field_path = field_path
        self.root_value = None
        assert type(field_path) is FieldPath and field_path.length > 0

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.field_path))

    def set_evaluated_typeexpr(self, typeexpr):
        if self.is_temporary:
            self._evaluated_typeexpr = typeexpr
        else:
            assert False, "cannot set evaluted type of a non local var: %s" % self.field_path

    def resolve_bindings_and_types(self, parent_function):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        assert self._evaluated_typeexpr == None, "Type has already been resolved, should not have been called twice."

        first, field_path_tail = self.field_path.pop()
        self.is_temporary = self.is_temporary or first == "_" or parent_function.is_temp_variable(first)
        if self.is_temporary: # We have a local var declaration
            # So add to function's temp var list if not a duplicate
            if first == "_":
                self._evaluated_typeexpr = tlcore.VoidType
            else:
                # get type from function
                self._evaluated_typeexpr = parent_function.temp_var_type(self.field_path)
        else:
            # See which of the params we should bind to
            var_typearg = None
            for src_typearg in parent_function.source_typeargs:
                if src_typearg.name == first:
                    var_typearg = src_typearg
                    break

            if not var_typearg:
                if parent_function.dest_varname == first:
                    var_typearg = parent_function.dest_typearg

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

class Function(Expression, tlcore.Annotatable):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, name, func_type, parent, annotations = None, docs = ""):
        Expression.__init__(self)
        tlcore.Annotatable.__init__(self, annotations, docs)
        self.parent = parent
        self.name = name
        self.func_type = func_type
        self.is_external = False
        self.dest_varname = "dest" if func_type else None

        self.temp_variables = {}
        # explicit transformer rules
        self._explicit_statements = []

        # Keeps track of the counts of each type of auto-generated variable.
        self._vartable = {}

    def set_resolver(self, resolver):
        """ Before we can do any bindings.  Each expression (and entity) needs resolvers to know 
        how to bind/resolve names the expression itself refers.  This step recursively assigns
        a resolver to every entity, expression that needs a resolver.  What the resolver should 
        be and what it should do depends on the child.
        """
        Expression.set_resolver(self, resolver)
        self.func_type.set_resolver(self)
        for statement in self.all_statements:
            statement.set_resolver(self)

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

    @property
    def source_typeargs(self):
        return self.func_type.args[:-1]

    @property
    def dest_typearg(self):
        out = self.func_type.args[-1]
        if out.type_expr.resolved_value == tlcore.VoidType:
            return None
        return out

    @property
    def returns_void(self):
        dest_typearg = self.func_type.args[-1]
        return dest_typearg is None or dest_typearg.type_expr.resolved_value == tlcore.VoidType

    def add_statement(self, stmt):
        if not isinstance(stmt, Statement):
            raise TLException("Transformer rule must be a let statement or a statement, Found: %s" % str(type(stmt)))
        # Check types and variables in the statements
        self._explicit_statements.append(stmt)

    @property
    def all_statements(self):
        return self._explicit_statements

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

    def resolve_bindings_and_types(self, parent_function):
        """
        The main resolver method.  This should take care of the following:

            1. Ensure field paths are correct
            2. All expressions have their evaluated types set
        """
        # Now resolve all field paths appropriately
        for index,statement in enumerate(self.all_statements):
            statement.resolve_bindings_and_types(self)

class FunctionCall(Expression):
    """
    An expression for denoting a function call.  Function calls can only be at the start of a expression stream, eg;

    f(x,y,z) => H => I => J

    but the following is invalid:

    H => f(x,y,z) -> J

    because f(x,y,z) must return an observable and observable returns are not supported (yet).
    """
    def __init__(self, func_expr, func_args = None):
        super(FunctionCall, self).__init__()
        self.func_expr = func_expr
        self.func_args = func_args

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

    def resolve_bindings_and_types(self, parent_function):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # First resolve the expression to get the source function
        self.func_expr.resolve_bindings_and_types(parent_function)

        func_type = self.func_expr.root_value.func_type
        if not func_type:
            raise errors.TLException("Function '%s' is undefined" % self.func_ref.name)

        # Each of the function arguments is either a variable or a value.  
        # If it is a variable expression then it needs to be resolved starting from the
        # parent function that holds this statement (along with any other locals and upvals)
        for arg in self.func_args:
            arg.resolve_bindings_and_types(parent_function)

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

    @property
    def evaluated_typeexpr(self):
        if self._evaluated_typeexpr is None:
            self._evaluated_typeexpr = self.func_expr.root_value.dest_typearg.typeexpr
        return self._evaluated_typeexpr
