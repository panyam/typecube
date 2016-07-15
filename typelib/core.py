

import ipdb
import errors
from annotations import *

class Type(object):
    def __init__(self, constructor, type_args = None):
        self._constructor = constructor
        self.docs = ""

        # Documentation for each of the child types
        self._child_docs = []

        # Annotations for child types
        self._child_annotations = []

        # child types of the type
        self._is_named = type(type_args) is dict
        self._child_types = []
        self._child_names = []

        self._child_data = []

        # Custom data for the type - particular used for resolutions
        self.type_data = None

        if type_args:
            if self._is_named:
                for k,v in type_args.iteritems():
                    self.add_child(v,k)
            else:
                for v in type_args:
                    self.add_child(v)
        self._resolved = True

    def copy_from(self, another):
        self._constructor = another.constructor
        self._is_named = another._is_named
        self._child_types = another._child_types[:]
        self._child_docs = another._child_docs[:]
        self._child_names = another._child_names[:]
        self._child_data = another._child_data[:]
        self._child_annotations = another._child_annotations[:]
        self._resolved = another._resolved
        self.docs = another.docs
        self.type_data = another.type_data
        # TODO: This is hacky - how do we ensure that all type_data objects 
        # have a reference back to the Type object that refers to it???
        if self.type_data:
            self.type_data.thetype = self

    @property
    def name(self):
        if self.type_data and hasattr(self.type_data, "name"):
            return self.type_data.name
        return self.constructor

    @property
    def namespace(self):
        if self.type_data and hasattr(self.type_data, "namespace"):
            return self.type_data.namespace
        return ""

    @property
    def fqn(self):
        if self.type_data and hasattr(self.type_data, "fqn"):
            return self.type_data.fqn
        return self.constructor

    @property
    def child_names(self):
        if not self._is_named:
            raise errors.TLException("Cannot get child type names for unnamed children")
        return self._child_names[:]

    @property
    def children(self):
        if not self._is_named:
            return self._child_types[:]
        else:
            return zip(self._child_names, self._child_types)

    def index_for(self, name):
        if self._child_names:
            for i,n in enumerate(self._child_names):
                if n == name:
                    return i

    def contains(self, name):
        index = self.index_for(name)
        return index is not None and index >= 0

    def set_docs_at(self, index, value):
        """
        Set documentation for type at the given index.
        """
        self._child_docs[index] = value

    def docs_for(self, name):
        """
        Set documentation for a named child type.
        """
        self._child_docs[self.index_for(name)] = value

    def docs_at(self, index):
        """
        Return documentation for type at the given index.
        """
        return self._child_docs[index]

    def docs_for(self, name):
        """
        Return documentation for a named child type.
        """
        return self._child_docs[self.index_for(name)]

    def set_annotations_at(self, index, value):
        """
        Set annotations for type at the given index.
        """
        self._child_annotations[index] = value

    def annotations_for(self, name):
        """
        Set annotations for a named child type.
        """
        self._child_annotations[self.index_for(name)] = value

    def annotations_at(self, index):
        """
        Return annotations for type at the given index.
        """
        return self._child_annotations[index]

    def annotations_for(self, name):
        """
        Return annotations for a named child type.
        """
        return self._child_annotations[self.index_for(name)]

    def child_type_at(self, index):
        """
        Gets the child argument at the given index.
        """
        return self._child_types[index]

    def child_type_for(self, name):
        """
        Gets the child argument with the given name.
        """
        return self.child_type_at(self.index_for(name))

    def child_data_at(self, index):
        """
        Gets the child data at the given index.
        """
        return self._child_data[index]

    def child_data_for(self, name):
        """
        Gets the child data with the given name.
        """
        return self.child_data_at(self.index_for(name))

    def add_child(self, value, name = None, docs = "", annotations = None, child_data = None):
        """
        Adds a child type with a name.  The name must be provided if and only if this is a named type.
        If the type is un named but there are no child arguments then the type is converted a named
        container type.
        """
        if type(value) is not Type:
            ipdb.set_trace()
            raise errors.TLException("value MUST be a type")

        if self._is_named:
            if not name:
                raise errors.TLException("Name MUST be provided for named child types")
            # see if name already exists
            index = self.index_for(name)
            if index is not None and index >= 0:
                ipdb.set_trace()
                raise errors.TLException("Child type by the given name '%s' already exists" % name)
            self._child_names.append(name)
        else:
            if name:
                raise errors.TLException("Name MUST NOT be provided for unnamed child types")
        self._child_types.append(value)
        self._child_docs.append(docs or "")
        self._child_annotations.append(annotations or [])
        self._child_data.append(child_data or [])

    @property
    def constructor(self):
        return self._constructor

    def __repr__(self):
        return "<Type, ID: 0x%x, Constructor: %s, Data: %s>" % (id(self), self.constructor, self.type_data)

    @property
    def is_unresolved(self):
        return not self.is_resolved

    @property
    def is_resolved(self):
        if not self._resolved:
            return False
        if self.type_data and hasattr(self.type_data, "is_resolved"):
            return self.type_data.is_resolved
        else:
            return True

    def set_resolved(self, value):
        self._resolved = value

    def resolve(self, registry):
        if not self.is_resolved:
            if self.type_data and hasattr(self.type_data, "is_resolved"):
                # copy resolved status from type data to avoid full resolution
                self._resolved = self.type_data.is_resolved

        if not self.is_resolved:
            if self.type_data and hasattr(self.type_data, "resolve"):
                self._resolved = self.type_data.resolve(registry)
        return self.is_resolved

    @property
    def arglimit(self):
        return len(self._child_types) if self._child_types else 0

BooleanType = Type("boolean")
IntType = Type("int")
LongType = Type("long")
FloatType = Type("float")
DoubleType = Type("double")
StringType = Type("string")

def FixedType(size):
    out = Type("fixed")
    out.type_data = size
    return out

def UnionType(*child_types):
    return Type("union", list(child_types))

def TupleType(*child_types):
    return Type("tuple", list(child_types))

def ListType(value_type):
    return Type("list", [value_type])

def SetType(value_type):
    return Type("set", [value_type])

def MapType(key_type, value_type):
    return Type("map", [key_type, value_type])

