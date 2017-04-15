import ipdb
import core
from typelib.annotations import Annotatable
import utils

def EnumSymbol(name, parent, value = None, annotations = None, docs = ""):
    out = core.Type(name, parent, "literal", type_params = None, type_args = None, annotations = annotations, docs = docs)
    out.value = value
    return out

def EnumType(name, parent, symbols = None, type_args = None, annotations = None, docs = None):
    out = core.Type(name, parent, "enum", type_params = None, type_args = type_args, annotations = annotations, docs = docs)
    symbols = symbols or []
    for symbol in symbols:
        out.add(symbol)
    return out

