

import ipdb
import errors
from annotations import *

class Type(object):
    def __init__(self, constructor, type_data = None, *type_args):
        self.constructor = constructor
        self.type_args = list(type_args)
        self.type_data = type_data
        self.docs = ""
        self._resolved = True

    def __repr__(self):
        return "<Type: %s %s>" % (self.constructor, self.type_data)

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
            if self.type_data and hasattr(self.type_data, "resolve"):
                self._resolved = self.type_data.resolve(registry)
        return self.is_resolved

    def copy_from(self, another):
        self.constructor = another.constructor
        self.type_data = another.type_data
        self.type_args = another.type_args
        self.docs = another.docs

    @property
    def arglimit(self):
        return len(self.type_args) if self.type_args else 0

    def __eq__(self, another):
        return self.constructor == another.constructor  and     \
                self.type_data == another.type_data     and     \
                self.type_args == another.type_args

BooleanType = Type("boolean")
IntType = Type("int")
LongType = Type("long")
FloatType = Type("float")
DoubleType = Type("double")
StringType = Type("string")

def FixedType(size):
    return Type("fixed", size)

def AliasType(target_type): 
    return Type("alias", None, target_type)

def UnionType(*child_types):
    return Type("union", None, *child_types)

def TupleType(*child_types):
    return Type("tuple", None, *child_types)

def ListType(value_type):
    return Type("list", None, value_type)

def SetType(value_type):
    return Type("set", None, value_type)

def MapType(key_type, value_type):
    return Type("map", None, key_type, value_type)

