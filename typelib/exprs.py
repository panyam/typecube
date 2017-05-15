
import ipdb
from enum import Enum
from onering import errors
from onering.utils.misc import ResolutionStatus
from onering.core.utils import FieldPath
from typelib import core as tlcore
from typelib.annotations import Annotatable
from typelib import unifier as tlunifier

class Statement(object):
    def __init__(self, expressions, target_variable, is_temporary = False):
        self.expressions = expressions
        self.target_variable = target_variable
        self.target_variable.is_temporary = is_temporary or target_variable.field_path.get(0) == '_'
        self.is_implicit = False
        if self.target_variable.is_temporary:
            assert target_variable.field_path.length == 1, "A temporary variable cannot have nested field paths"

    @property
    def is_temporary(self):
        return self.target_variable and self.target_variable.is_temporary

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        # Resolve the target variable's binding.  This does'nt necessarily have
        # to evaluate types.
        # This will help us with type inference going backwards
        if not self.is_temporary:
            self.target_variable.resolve_bindings_and_types(function, context)

        # Resolve all types in child expressions.  
        # Apart from just evaluating all child expressions, also make sure
        # Resolve field paths that should come from source type
        for expr in self.expressions:
            expr.resolve_bindings_and_types(function, context)

        last_expr = self.expressions[-1]
        if self.target_variable.is_temporary:
            varname = str(self.target_variable.field_path)
            if varname == "_":
                self.target_variable = None
            else:
                # Resolve field paths that should come from dest type
                self.target_variable.evaluated_typeexpr = last_expr.evaluated_typeexpr
                function.register_temp_var(varname, last_expr.evaluated_typeexpr)

class Expression(object):
    """
    Parent of all expressions.  All expressions must have a value.  Expressions only appear in functions.
    """
    def __init__(self):
        self._evaluated_typeexpr = None

    @property
    def evaluated_typeexpr(self):
        """ Every expressions must evaluate a type expression that will result in the expression's type. """
        if not self._evaluated_typeexpr:
            raise errors.OneringException("Type checking failed for '%s'" % repr(self))
        return self._evaluated_typeexpr

    @evaluated_typeexpr.setter
    def evaluated_typeexpr(self, typeexpr):
        self.set_evaluated_typeexpr(typeexpr)

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        pass

class VariableExpression(Expression):
    def __init__(self, field_path):
        super(VariableExpression, self).__init__()
        self.is_temporary = False
        self.field_path = field_path
        assert type(field_path) is FieldPath and field_path.length > 0

    def __repr__(self):
        return "<VarExp - ID: 0x%x, Value: %s>" % (id(self), str(self.field_path))

    def set_evaluated_typeexpr(self, typeexpr):
        if self.is_temporary:
            self._evaluated_typeexpr = typeexpr
        else:
            assert False, "cannot set evaluted type of a non local var: %s" % self.field_path

    def resolve_bindings_and_types(self, function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        assert self._evaluated_typeexpr == None, "Type has already been resolved, should not have been called twice."
        from onering.core.resolvers import resolve_path_from_record

        first, field_path_tail = self.field_path.pop()
        self.is_temporary = self.is_temporary or first == "_" or function.is_temp_variable(first)
        if self.is_temporary: # We have a local var declaration
            # So add to function's temp var list if not a duplicate
            if first == "_":
                self._evaluated_typeexpr = function.resolve_binding(tlcore.SymbolRef("void"))
            else:
                # get type from function
                self._evaluated_typeexpr = function.temp_var_type(self.field_path)
        else:
            # See which of the params we should bind to
            self.field_resolution_result = None

            for src_varname, src_typeref in function.source_variables:
                if src_varname == first:
                    if field_path_tail.length > 0:
                        self.field_resolution_result = resolve_path_from_record(src_typeref, field_path_tail, context, None)
                    else:
                        self._evaluated_typeexpr = src_typeref
                    break
            else:
                if function.dest_typeref and function.dest_varname == first:
                    # If we are dealing with an output variable, we dont want to directly reference the var
                    # because the output value could be created (via a constructor) at the end.  Instead
                    # save to other newly created temp vars and finally collect them and do bulk setters 
                    # on the output var or a constructor on the output var or both.
                    self.field_resolution_result = resolve_path_from_record(function.dest_typeref, field_path_tail, context, None)

            if not self._evaluated_typeexpr:
                if not self.field_resolution_result or not self.field_resolution_result.is_valid:
                    ipdb.set_trace()
                    raise errors.OneringException("Invalid field path '%s'" % self.field_path)
                self._evaluated_typeexpr = self.field_resolution_result.resolved_typeref

class Function(Expression, tlcore.Annotatable):
    """
    Defines a function binding along with the mappings to each of the 
    specific backends.
    """
    def __init__(self, name, func_type, annotations = None, docs = ""):
        Expression.__init__(self)
        tlcore.Annotatable.__init__(self, annotations, docs)
        self.name = name
        self.func_type = func_type
        self.statements = []
        self.resolution = ResolutionStatus()
        self.dest_varname = "dest" if func_type else None
        self.is_external = False

        self.temp_variables = {}
        # explicit transformer rules
        self._explicit_statements = []

        # Keeps track of the counts of each type of auto-generated variable.
        self._vartable = {}

    def __repr__(self):
        return "<Function(0x%x) %s (%s -> %s)>" % (id(self), self.fqn, ",".join(self.src_fqns), self.dest_fqn)

    @property
    def src_fqns(self):
        return [x.typeref.fqn for x in self.func_type.args]

    @property
    def source_variables(self):
        return [(x.name, x.typeref) for x in self.func_type.args]

    @property
    def src_typerefs(self):
        return [x.typeref for x in self.func_type.args]

    @property
    def dest_typeref(self):
        return self.func_type.output_typeref

    @property
    def dest_fqn(self):
        if self.func_type.output_typeref:
            return self.func_type.output_typeref.fqn
        else:
            return "None"

    def add_statement(self, stmt):
        if not isinstance(stmt, tlexprs.Statement):
            raise TLException("Transformer rule must be a let statement or a statement, Found: %s" % str(type(stmt)))
        # Check types and variables in the statements
        self._explicit_statements.append(stmt)

    @property
    def all_statements(self):
        return self._explicit_statements

    def local_variables(self, yield_src = True, yield_dest = True, yield_locals = True):
        if yield_src:
            for src_varname, src_typeref in self.source_variables:
                yield src_varname, src_typeref, False
        if yield_dest:
            yield self.dest_varname, self.dest_typeref, False
        if yield_locals:
            for vname, vtype in self.temp_variables.iteritems():
                yield vname, vtype, True

    def matches_input(self, context, input_typerefs):
        """Tells if the input types can be accepted as argument for this transformer."""
        if type(input_typerefs) is not list:
            input_types = [input_typerefs]
        if len(input_typerefs) != len(self.src_fqns):
            return False
        source_types = [x.final_entity for x in self.src_typerefs]
        ipdb.set_trace()
        input_types = [x.final_entity for x in input_typerefs]
        return all(tlunifier.can_substitute(st, it) for (st,it) in izip(source_types, input_types))

    def matches_output(self, context, output_type):
        dest_type = self.dest_typeref.final_entity
        return tlunifier.can_substitute(output_type, dest_type)

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
            ipdb.set_trace()
            raise TLException("Duplicate temporary variable declared: '%s'" % varname)
        self.temp_variables[varname] = vartype

    def resolve(self, context):
        """
        Kicks of resolutions of all dependencies.
        """
        def resolver_method():
            self._resolve(context)
        self.resolution.perform_once(resolver_method)


    def _resolve(self, context):
        """
        The main resolver method.  This should take care of the following:

            1. Ensure field paths are correct
            2. All expressions have their evaluated types set
        """
        # Now resolve all field paths appropriately
        for index,statement in enumerate(self.all_statements):
            statement.resolve_bindings_and_types(self, context)

class FunctionCall(Expression):
    """
    An expression for denoting a function call.  Function calls can only be at the start of a expression stream, eg;

    f(x,y,z) => H => I => J

    but the following is invalid:

    H => f(x,y,z) -> J

    because f(x,y,z) must return an observable and observable returns are not supported (yet).
    """
    def __init__(self, func_ref, func_args = None):
        super(FunctionCall, self).__init__()
        self.func_ref = func_ref
        self.func_args = func_args

    def resolve_bindings_and_types(self, parent_function, context):
        """
        Processes an expressions and resolves name bindings and creating new local vars 
        in the process if required.
        """
        try:
            parent_function.resolve_binding(self.func_ref)
        except Exception,exc:
            ipdb.set_trace()
            raise errors.OneringException("Function '%s' not found" % self.func_fqn)

        func_type = self.func_ref.final_entity
        if not func_type:
            raise errors.OneringException("Function '%s' is undefined" % self.func_ref.name)

        # Each of the function arguments is either a variable or a value.  
        # If it is a variable expression then it needs to be resolved starting from the
        # parent function that holds this statement (along with any other locals and upvals)
        for arg in self.func_args:
            arg.resolve_bindings_and_types(parent_function, context)

        if len(self.func_args) != func_type.argcount:
            ipdb.set_trace()
            raise errors.OneringException("Function '%s' takes %d arguments, but encountered %d" %
                                            (function.fqn, func_type.argcount, len(self.func_args)))

        for i in xrange(0, len(self.func_args)):
            arg = self.func_args[i]
            peg_typeref = arg.evaluated_typeexpr
            hole_typeref = func_type.arg_at(i).typeref
            if not tlunifier.can_substitute(peg_typeref.final_entity, hole_typeref.final_entity):
                ipdb.set_trace()
                raise errors.OneringException("Argument at index %d expected (hole) type (%s), found (peg) type (%s)" % (i, hole_typeref, peg_typeref))

        self._evaluated_typeexpr = func_type.output_typeref

    @property
    def evaluated_typeexpr(self):
        """
        if not self.function.output_known:
            output_typeref = self.function.final_type.output_typeref
            if not output_typeref or output_typeref.is_unresolved:
                raise errors.OneringException("Output type of function '%s' not known as type inference is requested" % self.func_fqn)
        """
        if self._evaluated_typeexpr is None:
            self._evaluated_typeexpr = self.func_ref.final_entity.output_typeref
        return self._evaluated_typeexpr
