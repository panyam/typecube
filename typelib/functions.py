
import ipdb
from typelib import utils as tlutils
from typelib import core as tlcore

def FunctionType(input_params, output_typeref, annotations = None, docs = "", fqn = None):
    out = tlcore.Type(None, "function", type_params = None, type_args = input_params,
                      annotations = annotations, docs = docs, fqn = fqn)
    out.output_typeref = output_typeref
    return out

class ParamTypeArg(tlcore.TypeArg):
    """Holds all information about a function's parameter. """
    def __init__(self, name, param_typeref, is_optional, default_value, annotations = None, docs = ""):
        if name and type(name) not in (str, unicode):
            ipdb.set_trace()
            assert type(name) in (str, unicode), "Expected param_name to be string, Found type: '%s'" % type(name)
        tlcore.TypeArg.__init__(self, param_typeref, name, annotations, docs)
        self.is_optional = is_optional
        self.default_value = default_value or None

    @property
    def param_name(self):
        return self.name

    @property
    def param_type(self):
        return self.typeref.first_type
