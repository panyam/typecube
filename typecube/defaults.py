
from typecube.core import *

def default_string_validator(val):
    assert type(val) is str
    return val

def default_int_validator(val):
    assert type(val) is int
    return val

def default_float_validator(val):
    assert type(val) is float
    return val

Byte = NativeType().set_label("byte")
Char = NativeType().set_label("char")
Float = NativeType().set_label("float").set_validator(default_float_validator)
Double = NativeType().set_label("double").set_validator(default_float_validator)
Int = NativeType().set_label("int").set_validator(default_int_validator)
Long = NativeType().set_label("Long").set_validator(default_int_validator)
String = NativeType().set_label("String").set_validator(default_string_validator)
Array = NativeType(["T"]).set_label("Array")
List = NativeType(["T"]).set_label("List")
Map = NativeType(["K", "V"]).set_label("Map")
DateTime = TypeVar().set_label("DateTime")
