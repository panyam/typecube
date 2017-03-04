
import core
from typelib.annotations import Annotatable
import utils

class EnumSymbol(Annotatable):
    def __init__(self, name, value = None, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.name = name
        self.value = value

def EnumType(symbols = None, type_args = None, annotations = None, docs = None):
    out = core.Type(None, "enum", type_params = None, type_args = type_args, annotations = annotations, docs = docs)
    out.type_data = symbols
    return out

