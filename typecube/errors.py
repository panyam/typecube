
import ipdb

class TCException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class ValidationError(TCException): pass

class FieldNotFoundException(TCException):
    def __init__(self, field_name, parent_type):
        TCException.__init__(self, "Field '%s' not found in record: %s" % (field_name, parent_type.fqn))

