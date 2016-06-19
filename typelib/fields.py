
import datatypes
import ipdb

class Field(object):
    """
    Holds all information about a field within a record.
    """
    def __init__(self, name, source_field_path, field_type, record,
                 optional = False, default = None, docs = "", annotations = None):
        assert type(name) in (str, unicode)
        assert isinstance(field_type, datatypes.Type), type(field_type)
        assert record.is_record_type, "record parameter must be a RecordType, instead found: %s" % str(type(record))
        self.name = name or ""
        self.source_field_path = source_field_path
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
        if self.source_field_path:
            out["sourceField"] = self.source_field_path
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
        out = Field(self.name, self.source_field_path, self.field_type, self.record, self.is_optional, self.default_value, self.documentation, self.annotations)
        out.errors = self.errors 
        return out

    def copyfrom(self, another):
        self.name = another.name
        self.source_field_path = another.source_field_path
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

class FieldInclude(object):
    """
    Describes include definitions of a field.
    """
    def __init__(self, source_record_name, field_path_str, annotations):
        self.source_record_name = source_record_name
        self.field_path_str = field_path_str
        self.annotations = annotations
        self.renamed_as = None
        self.retyped_as = None
        self.select_all_fields = True
        self.selectors = None
        self.mappers = []
        self.field_path = None
        self.resolved = False

    def resolve(self, source_type):
        self.source_type = source_type
        self.field_path = FieldPath(self.source_type, self.field_path_str)
        self.resolved = True

    @property
    def final_field_type(self):
        if self.retyped_as:
            return self.retyped_as
        elif not self.field_path_str:
            return self.source_type
        else:
            return self.field_path.final_type

    @property
    def final_field_name(self):
        if self.renamed_as:
            return self.renamed_as
        else:
            return self.field_path.final_name

    def create_fields(self, source_type, parent_record):
        # Resolve final types first
        self.resolve(source_type)

        # now that source record is valid create the new fields
        outfields = []
        if self.select_all_fields or self.selectors:
            # Pick all fields from final type
            field_selectors = self.selectors
            if not self.selectors:
                field_selectors = [(f.name,f.name) for f in self.final_field_type.type_data.fields]

            for (field_name, field_renamed_as) in field_selectors:
                field = self.final_field_type.type_data.fields[field_name]
                newfield = field.copy()
                newfield.parent_record = parent_record
                newfield.name = field_renamed_as
                if self.annotations:
                    newfield.annotations = self.annotations
                outfields.append(newfield)
            # TODO: apply mappers
        else:
            outfields = [fields.Field(self.final_field_name,
                                 self.field_path,
                                 self.final_field_type,
                                 parent_record,
                                 self.final_field.is_optional,
                                 self.final_field.default_value,
                                 self.final_field.docs,
                                 self.annotations or self.final_field.annotations)]

        return outfields

class FieldPath(object):
    """
    An json-path/XPath like field selector for fields from a source type to a target type.

    The syntax has the following constraints which may be removed later on.
        * Unknown nodes cannot be selected - ie no "*" selectors for nodes or attributes
        * Nesting is strictly limited to the successive children for now - 
            ie now "//" selectors and no Axes
        * Only one path can be selected at a time - ie no "|" selections, this can be done by 
            specifying multiple field paths that is easy enough
        * No predicates for now - ie no [ ]
    """
    class PathComponent(object):
        """
        Defines a component in a field path list.  Field paths are hierarchical paths 
        for collecting elements and sub resources starting from a root

        This is a subset of xpath syntax with the following constraints:
        """
        def __init__(self, name):
            self.name = name.strip()
            self.index = 0
            self.isLast = False
            self.predicate = None
            self._final_type = None
            self.source_type = None
            self.resolved = False

        @property
        def final_type(self):
            return self._final_type

        def __repr__(self):
            return self.name if not self.predicate else "%s[%s]" % (self.name, self.predicate)

    def __init__(self, source_type, field_path_str):
        """
        Creates a new field path given the feld path string.
            path := entry ( "/" entry) *
            entry := field_name 
        """
        self.resolved = False
        self.components = map(FieldPath.PathComponent, field_path_str.split("/"))

        # Now find the source type and see if we need to remove the "first" entry
        source_name = self.components[0].name
        self.source_type = source_type
        if self.source_type.is_resolved:
            self.resolve()

    @property
    def final_name(self):
        return self.components[-1].name

    @property
    def final_type(self):
        """
        The type at component[X] is:
                type(component[X + 1]) if component[X] is not a container
                otherwise, container(component[X])(type(component X + 1))
        """

        def calc_type_at_x(x, parent_type):
            curr_comp = self.components[x]

            if parent_type.is_list_type:
                calc_type_at_x(x, parent_type.type_data.value_type)
                curr_comp._final_type = datatypes.ListType(curr_comp._final_type)
            elif parent_type.is_set_type:
                calc_type_at_x(x, parent_type.type_data.value_type)
                curr_comp._final_type = datatypes.SetType(curr_comp._final_type)
            elif parent_type.is_map_type:
                calc_type_at_x(x, parent_type.type_data.value_type)
                curr_comp._final_type = datatypes.MapType(parnet_type.key_type, curr_comp._final_type)
            else: # elif parent_type.is_record_type:
                # MUST be record type otherwise we cannot be indexing further
                try:
                    comp_type = parent_type.type_data.fields[curr_comp.name].field_type
                except:
                    ipdb.set_trace()
                curr_comp._final_type = comp_type

                if x < len(self.components) - 1:
                    # Type of the component X - is just the type of the field type of the parent type
                    calc_type_at_x(x + 1, comp_type)
                    curr_comp._final_type = self.components[x + 1].final_type

        if not self.resolved:
            calc_type_at_x(0, self.source_type)
            self._final_type = self.components[0]._final_type
            self.resolved = True

            if self.components:
                self.components[-1].isLast = True
                for i,c in enumerate(self.components):
                    c.index = i
        return self._final_type

    def __repr__(self):
        return " / ".join(map(repr, self.components))

    def __getitem__(self, index):
        return self.components.__getitem__(index)

    def resolve(self):
        """
        Given a source type validates and resolves the components of the field path for 
        each sub component.   If any of the components does not match the type from the 
        resource and exception is thrown.
        """
        self.final_type
