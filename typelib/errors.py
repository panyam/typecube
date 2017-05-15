
import ipdb

class TLException(Exception):
    def __init__(self, msg):
        ipdb.set_trace()
        Exception.__init__(self, msg)

class FieldNotFoundException(TLException):
    def __init__(self, field_name, parent_type):
        TLException.__init__(self, "Field '%s' not found in record: %s" % (field_name, parent_type.fqn))

class DuplicateTypeException(TLException):
    def __init__(self, type_name):
        TLException.__init__(self, "Type '%s' is already defined" % type_name)

class DuplicateFieldException(TLException):
    def __init__(self, field_name, parent_type):
        TLException.__init__(self, "Duplicate Field '%s' encountered in record: %s" % (field_name, parent_type.fqn))

class TransformerException(TLException):
    def __init__(self, msg):
        TLException.__init__(self, msg)
 
class TypesNotFoundException(TLException):
    def __init__(self, *fqn):
        fqn = list(fqn)
        if len(fqn) > 0:
            message = "Types (%s) not found." % ", ".join(fqn)
        else:
            message = "Type '%s' not found." % fqn
        self.missing_types = fqn
        TLException.__init__(self, message)

