
import core
from typelib.annotations import Annotatable
import utils

def EnumSymbol(name, parent, value = None, annotations = None, docs = ""):
    out = core.Type(name, parent, "literal", annotations = symbol.annotations, docs = symbol.docs)
    out.value = value
    return out

def EnumType(name, parent, symbols = None, type_args = None, annotations = None, docs = None):
    out = core.Type(name, parent, "enum", type_params = None, type_args = type_args, annotations = annotations, docs = docs)
    symbols = symbols or []
    for symbol in symbols:
        out.add_entity(symbol)
    return out

