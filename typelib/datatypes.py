

import ipdb
import errors
from annotations import *

class TypeConstructor(object):
    def __init__(self, name, arglimit = -1, *argnames):
        """
        Creates a new type constructor.
        
        Params:

            \name       Name of the type constructor, eg list, set, union etc
            \arglimit   Maximum number of arguments that can be passed to this type constructor.  If -ve then there are no limits (eg for records, unions and tuples)
            \argnames   Names of the arguments provided for the arguments.  Not all arguments need to have names.  The first len(argnames) arguments will have names
                        and rest will be unnamed.
        """
        self.name = name
        self._arglimit = arglimit
        self.argnames = list(argnames)

    @property
    def has_arglimit(self):
        return self._arglimit < 0 or self._arglimit is None

    @property
    def arglimit(self):
        return self._arglimit

PairTypeConstructor = TypeConstructor("tuple", 2, "first", "second")
MapTypeConstructor = TypeConstructor("map", 2, "key", "value")
ListTypeConstructor = TypeConstructor("map", 1, "value")
UnionTypeConstructor = TypeConstructor("union", -1)
RecordTypeConstructor = TypeConstructor("record", -1)

class Type(object):
    def __init__(self, constructor, type_data = None, *type_args):
        self.constructor = constructor
        self.type_args = list(type_args)
        self.type_data = type_data
        self.docs = ""

    def copy_from(self, another):
        self.constructor = constructor
        self.type_data = another.type_data
        self.type_args = another.type_args
        self.docs = another.docs

    @property
    def arglimit(self):
        return len(self.type_args)

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

def RecordType(record_data):
    return Type("record", record_data)

def EnumType(enum_data):
    return Type("enum", list(enum_symbols))

