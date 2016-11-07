
import core
from typelib.annotations import Annotatable
import utils

class EnumSymbol(Annotatable):
    def __init__(self, name, annotations = None, docs = ""):
        Annotatable.__init__(self, annotations, docs)
        self.name = name

def EnumType(symbols = None, annotations = None, docs = None):
    out = core.Type(None, "enum", type_params = None, type_args = None, annotations = annotations, docs = docs)
    out.type_data = symbols
    return out

