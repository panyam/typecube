

import ipdb
from typelib import errors as tlerrors
from typelib.annotations import Annotatable

class TypeParam(Annotatable):
    """
    The reference to a parameter to a type.  Currently has the label associated with the type as well as the
    parent type.
    """
    def __init__(self, parent_type, label, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.parent_type = parent_type
        self.label = label

class TypeArg(Annotatable):
    """
    An arugment to a type.
    """
    def __init__(self, typeref_or_param, name = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self._name = name
        self.is_param = type(typeref_or_param) is TypeParam
        if type(typeref_or_param) not in (TypeRef, TypeParam):
            ipdb.set_trace()
            assert False, "Argument must be a TypeRef or a TypeParam"
        self.typeref = typeref_or_param

    def __json__(self, **kwargs):
        return {
            "name": self.name,
            "ref": self.typeref.json(**kwargs)
        }

    @property
    def name(self):
        return self._name

class Type(Annotatable):
    """
    Types in our system.  Note that types dont have names, only constructors.   The constructor
    specifies the whole class of type, eg record, function, enum, array etc.  These are almost
    like monads that can be defined else where.  The advantage of this is that two types can now
    be checked for equivalency regardless of how they are referenced.
    """
    def __init__(self, parent_typeref, constructor, type_params, type_args = None, annotations = None, docs = "", name = None):
        """
        Creates a new type object.

        Params:
            parent_typeref  A reference to the parent type this type is enclosed within.   Ideal for enum types 
                            where the enumerations are essentially types with nullary constructors and under 
                            the parent enum type.
            constructor     The type's constructor, eg "record", "int" etc.  This is not the name 
                            of the type itself but a name that indicates a class of this type.
            type_args       The child types or the argument types of this type function.
            annotations     Annotations applied to the type.
            docs            Documentation string for the type.
            name            The name this type was originally created with.
        """
        Annotatable.__init__(self, annotations, docs)

        if type(constructor) not in (str, unicode):
            ipdb.set_trace()
            raise tlerrors.TLException("constructor must be a string")

        self.parent_typeref = parent_typeref

        # If this is set then we have a possible function
        self.output_typeref = None

        self.constructor = constructor
        self.is_sum_type = False

        self._parameters = type_params

        self._type_args = []

        self._name = name

        if type_args:
            for type_arg in type_args:
                self.add_arg(type_arg)

    @property
    def name(self):
        return self._name

    @property
    def parameters(self):
        return self._parameters

    @property
    def argcount(self):
        return len(self._type_args)

    @property
    def args(self):
        return self._type_args

    def index_for(self, name):
        for i,arg in enumerate(self._type_args):
            if arg.name == name:
                return i
        return -1

    def arg_for(self, name):
        return self.arg_at(self.index_for(name))

    def arg_at(self, index):
        if index >= 0:
            return self._type_args[index]

    def contains(self, name):
        return self.index_for(name) >= 0

    def add_arg(self, arg):
        """
        Add an argument type.
        """
        if not isinstance(arg, TypeArg) and not isinstance(arg, TypeRef):
            ipdb.set_trace()
            raise tlerrors.TLException("Argument must be a TypeArg or TypeRef instance")

        if isinstance(arg, TypeRef):
            # Create an arg out of it
            arg = TypeArg(arg)

        if arg.name:
            index = self.index_for(arg.name)
            if index >= 0:
                raise tlerrors.TLException("Child type by the given name '%s' already exists" % name)

        # Check the typeparam if it is specified is valid
        if arg.is_param:
            if arg.is_param not in self.parameters:
                raise tlerrors.TLException("Invalid type parameter '%s'.  Must be one of (%s)" % arg.name, ", ".join([x.label for x in self.parameters]))
        else:
            # TODO: If the argument is a typeref then check that it is a concrete type (recursively)
            pass

        self._type_args.append(arg)

    def __json__(self, **kwargs):
        out = {}
        if not kwargs.get("no_cons", False):
            out["cons"] = self.constructor
        if self.name:
            out["name"] = self.name
        return out

class TypeRef(Annotatable):
    """
    A TypeRef is a union over a type or another type reference.  Any time a key is provided in the system
    it should be a reference to a type so that a given key always points to the same time.  This way 
    simply changing the object referenced by a key would make this change available to all references 
    to a key.
    """
    def __init__(self, entry, fqn, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        if fqn and type(fqn) not in (str, unicode):
            ipdb.set_trace()
            assert False, "FQN must be string or none"

        self._fqn = fqn
        self._categorise_target(entry)
        self._target = entry

    def __json__(self, **kwargs):
        target = self._target.__json__(**kwargs) if self._target else None
        return {"fqn": self.fqn, "target": target}

    def _categorise_target(self, entry):
        self._is_type = isinstance(entry, Type)
        self._is_ref = isinstance(entry, TypeRef)
        if not (self._is_type or self._is_ref or entry is None):
            ipdb.set_trace()
            assert False, "Referred type must be a Type or a TypeRef or None"
        return entry

    @property
    def is_unresolved(self):
        return self._target is None

    @property
    def is_resolved(self):
        return self._target is not None

    @property
    def is_reference(self):
        return self._is_ref

    @property
    def is_type(self):
        return self._is_type

    @property
    def target(self):
        return self._target

    @property
    def first_type(self):
        """
        Return the first type in this chain that is an actual type and not a typeref.
        """
        curr = self._target
        while curr and type(curr) is not Type:
            curr = curr._target
        return curr

    @property
    def final_type(self):
        """
        The final type transitively referenced by this type.
        """
        # TODO - Memoize the result
        if self.is_reference:
            return self._target.final_type
        return self._target

    @target.setter
    def target(self, newtype):
        self._categorise_target(newtype)
        self.set_target(newtype)

    def set_target(self, newtype):
        # TODO - Check for cyclic references
        self._target = newtype

    @property
    def fqn(self):
        return self._fqn

    @fqn.setter
    def fqn(self, value):
        self._set_fqn(value)

    def _set_fqn(self, value):
        self._fqn = value

BooleanType = Type(None, "boolean", type_params = None)
ByteType = Type(None, "byte", type_params = None)
IntType = Type(None, "int", type_params = None)
LongType = Type(None, "long", type_params = None)
FloatType = Type(None, "float", type_params = None)
DoubleType = Type(None, "double", type_params = None)
StringType = Type(None, "string", type_params = None)

def FixedType(size, annotations = None, docs = None):
    out = Type(None, "fixed", type_params = None, annotations = annotations, docs = docs)
    out.type_data = size
    return out

def UnionType(child_typerefs, annotations = None, docs = None, name = None):
    assert type(child_typerefs) is list
    return Type(None, "union", type_params = None, type_args = child_typerefs, annotations = annotations, docs = docs, name = name)

def TupleType(child_typerefs, annotations = None, docs = None):
    assert type(child_typerefs) is list
    return Type(None, "tuple", type_params = None, type_args = child_typerefs, annotations = annotations, docs = docs)

def ArrayType(value_typeref, annotations = None, docs = None):
    assert value_typeref is not None
    return Type(None, "array", type_params = None, type_args = [value_typeref], annotations = annotations, docs = docs)

def ListType(value_typeref, annotations = None, docs = None):
    assert value_typeref is not None
    return Type(None, "list", type_params = None, type_args = [value_typeref], annotations = annotations, docs = docs)

def SetType(value_typeref, annotations = None, docs = None):
    return Type(None, "set", type_params = None, type_args = [value_typeref], annotations = annotations, docs = docs)

def MapType(key_typeref, value_typeref, annotations = None, docs = None):
    out = Type(None, "map", type_params = None, type_args = [key_typeref, value_typeref], annotations = annotations, docs = docs)
    return out

