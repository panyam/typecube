
from collections import defaultdict
import ipdb
from utils import ensure_types
from typelib import errors as tlerrors
from typelib.annotations import Annotatable

class TypeExpression(object):
    """ An expressions which results in a type or a type expression. 
    This is the window to all types that are either available or must be lazily evaluated.
    """
    def __init__(self, source, *args):
        self.is_function = issubclass(source.__class__, TypeFunction)
        self.is_initializer = type(source) is TypeInitializer
        self.is_string = type(source) in (str, unicode)
        if self.is_function:
            self.type_function = source
        elif self.is_initializer:
            self.type_initializer = source
            self.type_args = args or []
        elif self.is_string:
            # TODO - can this be merged with type_initializer?
            self.fqn = source
            self.type_args = args or []
        else:
            assert False, "'source' can only be a TypeFunction or a TypeInitializer or a string."

class TypeRef(Annotatable):
    def __init__(self, name, type_params, type_expr, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.name = name
        self.type_params = type_params

class TypeArg(Annotatable):
    """ A type argument is a child of a given type.  Akin to a member/field of a type.
    These are either names of a type (yet to be bound) or another TypeFunction that 
    must be evaluated to create the type of this argument, or a TypeInitializer
    """
    def __init__(self, name, type_expr, is_optional = False, default_value = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        assert type(type_expr) is TypeExpression, "TypeExpr type = '%s'" % str(type(type_expr))
        self.name = name
        self.type_expr = type_expr
        self.is_optional = is_optional
        self.default_value = default_value or None

class TypeArgList(object):
    """ A list of type args for a particular type container. """
    def __init__(self, type_args):
        self._type_args = []
        for type_arg in type_args or []:
            self.add(type_arg)

    def __iter__(self): return iter(self._type_args)

    def __len__(self): return len(self._type_args)

    @property
    def count(self): return len(self._type_args)

    def index_for(self, name):
        for i,arg in enumerate(self._type_args):
            if arg.name == name:
                return i
        return -1

    def arg_for(self, name):
        return self.arg_at(self.index_for(name))

    def arg_at(self, index):
        return None if index < 0 else self._type_args[index]

    def contains(self, name):
        return self.index_for(name) >= 0

    def add(self, arg):
        """
        Add an argument type.
        """
        if type(arg) is TypeExpression:
            arg = TypeArg(None, arg)
        elif not isinstance(arg, TypeArg):
            raise tlerrors.TLException("Argument must be a TypeArg. Found: '%s'" % type(arg))

        if arg.name:
            index = self.index_for(arg.name)
            if index >= 0:
                raise tlerrors.TLException("Child type by the given name '%s' already exists" % arg.name)
        self._type_args.append(arg)

class TypeInitializer(object):
    def __init__(self, type_func_name, *type_exprs):
        # The name of the type function which will initialize the new type, eg the "map" in map<int, string>
        # This name may be pointing to an unresolved type so this will have to be resolved before
        # a type function is determined
        self.type_func_name = type_func_name
        self.type_function = None

        # Each type expression should (eventually) resolve to a Type and will be bound to the respective type.
        self.type_exprs = type_exprs

class TypeFunction(Annotatable):
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

        if type(constructor) not in (str, unicode):
            raise tlerrors.TLException("constructor must be a string")

        self.constructor = constructor
        self.parent = parent
        self.name = name
        self._type_params = type_params
        self._signature = None
        self.args = TypeArgList(type_args)

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

    @property
    def signature(self):
        if not self._signature:
            out = self.constructor or ""
            if self._type_args:
                out += "(" + ", ".join([t.typeref.final_entity.signature for t in self._type_args]) + ")"
            if self.output_typeref:
                out += " : " + self.output_typeref.final_entity.signature
            self._signature = out
        return self._signature

def make_type(constructor, name, type_params, type_args, parent = None, annotations = None, docs = ""):
    return TypeFunction(constructor, name, type_params = type_params, type_args = type_args,
                        parent = parent, annotations = annotations, docs = docs)

def make_literal_type(name, parent = None, annotations = None, docs = ""):
    return make_type("literal", name, type_params = None, type_args = None,
                     parent = parent, annotations = annotations, docs = docs)

def make_wrapper_type(name, type_params, parent = None, annotations = None, docs = ""):
    type_args = [TypeArg(None, TypeExpression(param)) for param in type_params]
    return TypeFunction("extern", newtyperef.name, type_params = type_params, type_args = type_args,
                        parent = parent, annotations = annotations, docs = docs)

def make_func_type(name, type_params, type_args, output_arg, parent = None, annotations = None, docs = ""):
    return TypeFunction("function", name, type_params = type_params, type_args = type_args + [output_arg],
                        parent = parent, annotations = annotations, docs = docs)

AnyType = make_literal_type("any")
VoidType = make_literal_type("void")

