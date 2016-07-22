
import utils
import errors
import core
import ipdb

def RecordType(record_data = None, annotations = None, docs = None):
    out = core.Type("record", {}, annotations = annotations, docs = docs)
    record_data = record_data or Record(None, out, None)
    record_data.thetype = out
    out.type_data = record_data
    return out

class Record(object):
    def __init__(self, fqn, thetype, parent_entity):
        """Creates a new Record declaration.
        Arguments:
            fqn                     --  Fully qualified name of the record.  Records should have names.
            parent_entity           --  The parent record or projection inside which this record is declared (as an inner declaration)
                                        If this is not provided then this record is being defined independantly at the top level.
        """
        self._fqn = fqn
        self.thetype = thetype
        self._resolved = True
        self._parent_entity = parent_entity

    @property
    def name(self):
        return utils.normalize_name_and_ns(self.fqn, "")[0]


    @property
    def namespace(self):
        return utils.normalize_name_and_ns(self.fqn, "")[1]
    
    @property
    def fqn(self):
        return self._fqn
    
    @fqn.setter
    def fqn(self, value):
        self._fqn = value

    @property
    def parent_entity(self):
        return self._parent_entity

    def __repr__(self):
        return "<ID: 0x%x, Name: '%s'>" % (id(self), self.fqn)

    @property
    def root_record(self):
        if self.parent_entity is None:
            return self
        if type(self.parent_entity) is core.Type:
            return self.parent_entity.type_data.root_record
        else:
            return self.parent_entity.root_record

    def get_binding(self, field_path):
        """
        Gets a particular binding by a given name.  For a record this will be a field name within this record.
        """
        name = field_path.get(0)
        if self.thetype.contains(name):
            return self.thetype, field_path
        return None, None

    @property 
    def is_resolved(self):
        return self._resolved


class FieldData(object):
    """
    Holds all information about a field within a record.
    """
    def __init__(self, name, parent_type, optional, default):
        self.field_name = name
        self.parent_type = parent_type
        self.is_optional = optional
        self.default_value = default or None

    @property
    def field_type(self):
        return self.parent_type.child_type_for(self.field_name)

    @property
    def docs(self):
        return self.parent_type.docs_for(self.field_name)

    @property
    def annotations(self):
        return self.parent_type.annotations_for(self.field_name)



