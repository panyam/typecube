
import ipdb

class TCException(Exception):
    def __init__(self, msg):
        ipdb.set_trace()
        Exception.__init__(self, msg)

class FieldNotFoundException(TCException):
    def __init__(self, field_name, parent_type):
        TCException.__init__(self, "Field '%s' not found in record: %s" % (field_name, parent_type.fqn))

class DuplicateTypeException(TCException):
    def __init__(self, type_name):
        TCException.__init__(self, "Type '%s' is already defined" % type_name)

class DuplicateFieldException(TCException):
    def __init__(self, field_name, parent_type):
        TCException.__init__(self, "Duplicate Field '%s' encountered in record: %s" % (field_name, parent_type.fqn))

class TransformerException(TCException):
    def __init__(self, msg):
        TCException.__init__(self, msg)
 
class TypesNotFoundException(TCException):
    def __init__(self, *fqn):
        fqn = list(fqn)
        if len(fqn) > 0:
            message = "Types (%s) not found." % ", ".join(fqn)
        else:
            message = "Type '%s' not found." % fqn
        self.missing_types = fqn
        TCException.__init__(self, message)

