
import datatypes
import ipdb

class Field(object):
    """
    Holds all information about a field within a record.
    """
    def __init__(self, name, field_type, record, optional = False, default = None, docs = "", annotations = None):
        assert type(name) in (str, unicode)
        assert isinstance(field_type, datatypes.Type), type(field_type)
        assert record.is_record_type, "record parameter must be a RecordType, instead found: %s" % str(type(record))
        self.name = name or ""
        self.field_type = field_type
        self.record = record
        self.is_optional = optional
        self.default_value = default or None
        self.documentation = docs
        self.errors = []
        self.annotations = annotations or []

    def to_json(self):
        out = {
            "name": self.field_name,
            "type": self.field_type
        }
        return out

    @property
    def fqn(self):
        return self.record.fqn + "." + self.name

    def __hash__(self):
        return hash(self.fqn)

    def __cmp__(self, other):
        result = cmp(self.record, other.record)
        if result == 0:
            result = cmp(self.name, other.name)
        return result

    def copy(self):
        out = Field(self.name, self.field_type, self.record, self.is_optional, self.default_value, self.documentation, self.annotations)
        out.errors = self.errors 
        return out

    def copyfrom(self, another):
        self.name = another.name
        self.field_type = another.field_type
        self.record = another.record
        self.is_optional = another.is_optional
        self.default_value = another.default_value
        self.documentation = another.documentation
        self.errors = another.errors
        self.annotations = another.annotations

    def has_errors(self):
        return len(self.errors) > 0

    def __repr__(self): return str(self)
    def __str__(self):
        return self.fqn
