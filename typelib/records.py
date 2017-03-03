
import ipdb
from typelib import utils as tlutils
from typelib import core as tlcore

def RecordType(fields, annotations = None, docs = None, name = None):
    return tlcore.Type(None, "record", type_params = None, type_args = fields, annotations = annotations, docs = docs, name = name)

class FieldTypeArg(tlcore.TypeArg):
    """
    Holds all information about a field within a record.
    """
    def __init__(self, name, field_typeref, is_optional, default_value, annotations = None, docs = ""):
        if type(name) not in (str, unicode):
            ipdb.set_trace()
            assert type(name) in (str, unicode), "Expected field_name to be string, Found type: '%s'" % type(name)
        tlcore.TypeArg.__init__(self, field_typeref, name, annotations, docs)
        self.is_optional = is_optional
        self.default_value = default_value or None

    @property
    def field_name(self):
        return self.name

    @property
    def field_type(self):
        return self.typeref.first_type

