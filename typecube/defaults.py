
from typecube.core import *
from typecube import errors

def default_string_validator(thetype, val):
    if type(val) is not str:
        raise errors.ValidationError("%s needs to be a string, found %s" % (str(val), str(type(val))))
    return val

def default_int_validator(thetype, val):
    if type(val) is not int:
        raise errors.ValidationError("%s needs to be a int, found %s" % (str(val), str(type(val))))
    return val

def default_float_validator(thetype, val):
    if type(val) is not float:
        raise errors.ValidationError("%s needs to be a float, found %s" % (str(val), str(type(val))))
    return val

Byte = NativeType("byte")
Char = NativeType("char")
Float = NativeType("float").set_validator(default_float_validator)
Double = NativeType("double").set_validator(default_float_validator)
Int = NativeType("int").set_validator(default_int_validator)
Long = NativeType("Long").set_validator(default_int_validator)
String = NativeType("String").set_validator(default_string_validator)
Array = NativeType("Array", ["T"])
List = NativeType("List", ["T"])
Map = NativeType("Map", ["K", "V"])
DateTime = TypeVar("DateTime")
