
from collections import defaultdict
import ipdb
from utils import ensure_types
from typelib import errors as tlerrors
from typelib.annotations import Annotatable

class Entity(Annotatable):
    """Base class of all onering entities."""
    def __init__(self, name, parent = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self._name = name
        self._parent = parent 
        self.child_entities = []
        self.entity_map = {}
        self._symbol_refs = {}
        self.aliases = {}

    def set_alias(self, name, fqn):
        """Sets the alias of a particular name to an FQN."""
        self.aliases[name] = self.add_symbol_ref(fqn)

    @property
    def tag(self): return self.__class__.TAG 

    @property
    def fqn(self):
        out = self.name
        if self.parent and self.parent.fqn:
            out = self.parent.fqn + "." + out
        return out or ""

    def add_symbol_ref(self, fqn):
        if fqn not in self._symbol_refs:
            # Ensure symbol refs dont have a parent as they are not bound to the parent but
            # to some arbitrary scope that is using them to refer to the FQN
            self._symbol_refs[fqn] = SymbolRef(fqn)
        return self._symbol_refs[fqn]

    def add(self, entity):
        """ Adds a new child entity. """
        if not (entity.name and entity.name not in self.entity_map):
            ipdb.set_trace()
        assert entity.name and entity.name not in self.entity_map
        self.entity_map[entity.name] = entity
        entity._parent = self
        self.child_entities.append(entity)

    def get(self, fqn_or_parts):
        """ Given a list of key path parts, tries to resolve the descendant entity that matchies this part prefix. """
        parts = fqn_or_parts
        if type(fqn_or_parts) in (unicode, str):
            parts = fqn_or_parts.split(".")
        curr = self
        for part in parts:
            if part not in curr.entity_map:
                return None
            curr = curr.entity_map[part]
        return curr

    def find_fqn(self, fqn):
        """Looks for a FQN in either the aliases or child entities or recursively in the parent."""
        out = None
        curr = self
        while curr and not out:
            out = curr.aliases.get(fqn, None)
            if not out:
                out = curr.get(fqn)
            if not out:
                curr = curr.parent
        return out

    def ensure_key(self, fqn_or_name_or_parts):
        """Ensures that a descendant hierarchy of Entities or EntityRefs exists given the key path parts."""
        parts = fqn_or_name_or_parts
        if type(parts) in (str, unicode):
            parts = parts.split(".")
        curr = self
        for part in parts:
            if part not in curr.entity_map:
                curr.entity_map[part] = EntityRef(None, part, parent = curr)
            curr = curr.entity_map[part]
        return curr

    def resolve_binding(self, typeref):
        if not typeref: return
        assert issubclass(typeref.__class__, EntityRef)
        symref = typeref
        while symref and not symref.is_resolved:
            symref.target = self.find_fqn(symref.fqn)
            # only drill into it we have another entity ref
            if symref.target and not issubclass(symref.target.__class__, EntityRef): break
            symref = symref.target

        final_entity = None if not symref else symref.final_entity
        if symref and not final_entity:
            # Try to resolve it too
            self.resolve_binding(symref.last_unresolved)
            final_entity = None if not symref else symref.final_entity
            if not final_entity:
                raise tlerrors.TLException("%s could not be resolved" % typeref.fqn)
        if type(final_entity) is Type:
            # for the final entity, resolve the bindings of its args too!
            if final_entity.output_typeref:
                self.resolve_binding(final_entity.output_typeref)
            for arg in final_entity.args: self.resolve_binding(arg.typeref)
        return symref

    @property
    def name(self): return self._name

    @property
    def parent(self): return self._parent

    """
    @name.setter
    def name(self, value):
        self._set_name(value)

    def _set_name(self, value):
        self._name = value
    """

class EntityRef(Entity):
    """
    A named reference to an entity.
    """
    TAG = "REF"
    def __init__(self, entry, name, parent, annotations = None, docs = ""):
        Entity.__init__(self, name, parent, annotations, docs)
        if name and type(name) not in (str, unicode):
            ipdb.set_trace()
            assert False, "Name for an reference must be string or none"

        self._categorise_target(entry)
        self._target = entry

    def __json__(self, **kwargs):
        target = self._target.__json__(**kwargs) if self._target else None
        out = {}
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if self.name:
            # return self.name
            out["name"] = self.name
        elif target and len(target) > 0:
            return target
            # out["target"] = target
        return out

    def _categorise_target(self, entry):
        self._is_ref = issubclass(entry.__class__, EntityRef)
        self._is_entity = isinstance(entry, Entity)
        if not (self._is_entity or self._is_ref or entry is None):
            ipdb.set_trace()
            assert False, "Referred target must be a Entity or a EntityRef or None"
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
    def is_entity(self):
        return self._is_entity

    @property
    def last_unresolved(self):
        curr = self
        while curr.target:
            curr = curr.target
            if not issubclass(curr.__class__, EntityRef): return None
        return curr

    @property
    def target(self):
        return self._target

    @property
    def first_entity(self):
        """
        Return the first type in this chain that is an actual entity and not an entity ref.
        """
        curr = self._target
        while curr and not issubclass(curr.__class__, EntityRef):
            curr = curr._target
        return curr

    @property
    def final_entity(self):
        """
        The final type transitively referenced by this ref.
        """
        # TODO - Memoize the result
        curr = self._target
        while curr and issubclass(curr.__class__, EntityRef):
            curr = curr._target
        return curr

    @target.setter
    def target(self, newentity):
        self._categorise_target(newentity)
        self.set_target(newentity)

    def set_target(self, newentity):
        # TODO - Check for cyclic references
        self._target = newentity

class SymbolRef(EntityRef):
    TAG = "SYM"
    def __init__(self, fqn):
        EntityRef.__init__(self, None, fqn, None)

    @property
    def fqn(self):
        return self.name

class Type(Entity):
    """
    Types in our system.  Note that types dont have names, only constructors.   The constructor
    specifies the whole class of type, eg record, function, enum, array etc.  These are almost
    like monads that can be defined else where.  The advantage of this is that two types can now
    be checked for equivalency regardless of how they are referenced.
    """
    def __init__(self, name, parent, constructor, type_params, type_args = None, annotations = None, docs = ""):
        """
        Creates a new type object.

        Params:
            parent          A reference to the parent container entity of this type.   Ideal for enum types 
                            where the enumerations are essentially types with nullary constructors and under 
                            the parent enum type.
            name            The name this type was originally created with.
            constructor     The type's constructor, eg "record", "int" etc.  This is not the name 
                            of the type itself but a name that indicates a class of this type.
            type_args       The child types or the argument types of this type function.
            annotations     Annotations applied to the type.
            docs            Documentation string for the type.
        """
        Entity.__init__(self, name, parent, annotations = annotations, docs = docs)

        if type(constructor) not in (str, unicode):
            ipdb.set_trace()
            raise tlerrors.TLException("constructor must be a string")

        # If this is set then we have a possible function
        self.output_typeref = None

        self.constructor = constructor
        self.is_sum_type = False

        self._signature = None
        self._parameters = type_params

        self._type_args = []

        self._name = name

        if type_args:
            for type_arg in type_args:
                self.add_arg(type_arg)

    TAG = "TYPE"

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
        if not isinstance(arg, TypeArg) and not issubclass(arg.__class__, EntityRef):
            ipdb.set_trace()
            raise tlerrors.TLException("Argument must be a TypeArg or EntityRef instance")

        if issubclass(arg.__class__, EntityRef):
            # Create an arg out of it
            arg = TypeArg(arg)

        if arg.name:
            index = self.index_for(arg.name)
            if index >= 0:
                raise tlerrors.TLException("Child type by the given name '%s' already exists" % arg.name)

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
        if self.name:
            out["name"] = self.name
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if not kwargs.get("no_cons", False):
            out["type"] = self.constructor
        if self._type_args:
            out["args"] = [arg.json(**kwargs) for arg in self._type_args]
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
        if not (issubclass(typeref_or_param.__class__, TypeParam) or issubclass(typeref_or_param.__class__, EntityRef)):
            ipdb.set_trace()
            assert False, "Argument must be a EntityRef or a TypeParam"
        self.typeref = typeref_or_param

    def __json__(self, **kwargs):
        out = {}
        if self.name:
            out["name"] = self.name
        if self.typeref.fqn:
            out["type"] = self.typeref.fqn
        else:
            out["type"] = self.typeref.json(**kwargs)
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        return out

    @property
    def name(self):
        return self._name

AnyType = Type("any", None, "literal", type_params = None)
BooleanType = Type("boolean", None, "literal", type_params = None)
ByteType = Type("byte", None, "literal", type_params = None)
IntType = Type("int", None, "literal", type_params = None)
LongType = Type("long", None, "literal", type_params = None)
FloatType = Type("float", None, "literal", type_params = None)
DoubleType = Type("double", None, "literal", type_params = None)
StringType = Type("string", None, "literal", type_params = None)

def FixedType(name, parent, size, annotations = None, docs = None):
    out = Type(name, parent, "fixed", type_params = None, annotations = annotations, docs = docs)
    out.type_data = size
    return out

def UnionType(name, parent, child_typerefs, annotations = None, docs = None):
    assert type(child_typerefs) is list
    return Type(name, parent, "union", type_params = None, type_args = child_typerefs, annotations = annotations, docs = docs, name = name)

def TupleType(name, parent, child_typerefs, annotations = None, docs = None):
    assert type(child_typerefs) is list
    return Type(name, parent, "tuple", type_params = None, type_args = child_typerefs, annotations = annotations, docs = docs)

def ArrayType(name, parent, value_typeref, annotations = None, docs = None):
    assert value_typeref is not None
    return Type(name, parent, "array", type_params = None, type_args = [value_typeref], annotations = annotations, docs = docs)

def ListType(name, parent, value_typeref, annotations = None, docs = None):
    assert value_typeref is not None
    return Type(name, parent, "list", type_params = None, type_args = [value_typeref], annotations = annotations, docs = docs)

def SetType(name, parent, value_typeref, annotations = None, docs = None):
    return Type(name, parent, "set", type_params = None, type_args = [value_typeref], annotations = annotations, docs = docs)

def MapType(name, parent, key_typeref, value_typeref, annotations = None, docs = None):
    out = Type(name, parent, "map", type_params = None, type_args = [key_typeref, value_typeref], annotations = annotations, docs = docs)
    return out

