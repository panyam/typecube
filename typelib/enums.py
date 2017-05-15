import ipdb
import core
from typelib.annotations import Annotatable
import utils

def EnumSymbol(name, parent, value = None, annotations = None, docs = ""):
    out = core.make_literal_type(name, parent, annotations = annotations, docs = docs)
    out.value = value
    return out

def EnumType(name, parent, symbols = None, type_args = None, annotations = None, docs = None):
    out = core.make_type("enum", name, parent, type_args = type_args, annotations = annotations, docs = docs)
    for symbol in symbols or []:
        out.args.add(core.TypeArg(symbol.name, core.TypeExpression(symbol)))
    return out

