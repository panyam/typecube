
class OneringException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class FieldNotFoundException(OneringException):
    def __init__(self, field_name, parent_type):
        Exception.__init__(self, "Field '%s' not found in record: %s" % (field_name, parent_type.fqn))

class DuplicateTypeException(OneringException):
    def __init__(self, type_name):
        Exception.__init__(self, "Type '%s' is already defined" % type_name)

class DuplicateFieldException(OneringException):
    def __init__(self, field_name, parent_type):
        Exception.__init__(self, "Duplicate Field '%s' encountered in record: %s" % (field_name, parent_type.fqn))

class TransformerException(OneringException):
    def __init__(self, msg):
        Exception.__init__(self, msg)
 
class TypeNotFoundException(OneringException):
    def __init__(self, fqn):
        Exception.__init__(self, "Type '%s' not found.  Are class and/or jar paths set correctly?" % fqn)
        self.missing_type = fqn

