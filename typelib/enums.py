import ipdb
import core
from typelib.annotations import Annotatable
import utils

def EnumSymbol(fqn, parent, value = None, annotations = None, docs = ""):
    out = core.make_literal_type(fqn, parent, annotations = annotations, docs = docs)
    out.value = value
    return out

def EnumType(fqn, parent, symbols = None, type_args = None, annotations = None, docs = None):
    out = core.make_type(core.TypeCategory.SUM_TYPE, fqn, type_args, parent, annotations = annotations, docs = docs)
    for symbol in symbols or []:
        out.args.add(core.TypeArg(symbol.fqn, symbol))
    return out

