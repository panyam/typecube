
import utils
import errors
import core
import ipdb

def RecordType(record_data = None):
    record_data = record_data or Record()
    return core.Type("record", record_data)

class Record(object):
    def __init__(self):
        self.resolved = True
        self.field_declarations = []
        self.source_records = []

    def add_field_declaration(self, field_decl):
        """
        Add a field declaration.
        """
        self.resolved = False
        self.field_declarations.append(field_decl)
        # TODO: see if this field declaration can be resolved.

    def add_source_record(self, source_record, alias = None):
        """
        Add a new source record that this record derives from.
        """
        n,ns,fqn = utils.normalize_name_and_ns(source_record)
        alias = alias or n
        if self.find_source(alias) is not None:
            raise TLException("A source by name '%s' already exists" % n)
        self.source_records.append((source_record, alias))

    def find_source(self, name):
        """
        Find a source by a given name.
        """
        for (rec,alias) in self.source_records:
            if name == alias:
                return rec
        return None

    @property
    def has_sources(self):
        return self.source_count > 0

    @property
    def source_count(self):
        return len(self.source_records)

class FieldDeclaration(object):
    """
    Describes a field declaration.  The same declaration is used for both mutating an 
    existing field as well as adding new fields as well removing existing fields.

    A Field declaration will be remain in an "unresolved" state until all its 
    dependant types are also provided.
    """
    def __init__(self, source_record, field_path_parts,
                 starts_at_root = False, negates_inclusion = False, annotations = None):
        # Source record in which the declaration is provided
        self.source_record = source_record

        # Field path string which refers to one or more fields within the
        # source record.  Following are possible:
        self.field_path_parts = field_path_parts

        # Set to True after field path and source record resolution is complete
        self.resolved = False

        # Whether the field path starts at the root or at the "current"
        # level
        self.starts_at_root = starts_at_root

        # Tells if we are adding or deleting fields
        self.negates_inclusion = negates_inclusion

        # Annotations on the field inclusion
        self.annotations = annotations or []

        # Whether the field is being renamed.
        # This can ONLY be set if the field path string refers to a single field
        # If multiple fields are referred to then this will throw an error when
        # the source record type has been resolved.
        self.declared_name = None

        # The type as was declared for this field
        self.declared_type = None

        # Which of the fields are being selected?
        # If this is None then "all" fields are being selected 
        # (or negated depending on the negate_inclusions flags)
        # otherwise it must be a list of field names which will be included 
        # (or excluded depending on the negates_inclusions flag)
        self.child_fields = True

        # Marks whether a field's optionality is being changed
        self.is_optional = False

        # Marks whether a field's default value is being changed
        self.default_value = None

        # How the retyping happens.   THis can happen in one of a few ways:
        self.type_stream = None

    @property
    def all_fields_selected(self):
        return self.child_fields is None

    def resolve(self, source_type):
        """
        Starting from the source_type resolve the type of this given field.
        """
        if not self.resolved:
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
        if self.declared_name:
            return self.declared_name
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

            for (field_name, field_declared_name) in field_selectors:
                field = self.final_field_type.type_data.fields[field_name]
                newfield = field.copy()
                newfield.parent_record = parent_record
                newfield.name = field_declared_name
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

class TypeStreamDeclaration(object):
    """
    Keeps track of the parameters and values of the input and output types 
    during type streaming.
    """
    def __init__(self, type_constructor, param_names, field_decls):
        self.type_constructor = type_constructor
        self.param_names = param_names
        self.field_decls = field_decls







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
    def __init__(self, components, starts_at_root = False):
        """
        Given a bunch of field path components.
        """
        self.resolved = False
        self.starts_at_root = starts_at_root 
        self.components = components

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
                curr_comp._final_type = core.ListType(curr_comp._final_type)
            elif parent_type.is_set_type:
                calc_type_at_x(x, parent_type.type_data.value_type)
                curr_comp._final_type = core.SetType(curr_comp._final_type)
            elif parent_type.is_map_type:
                calc_type_at_x(x, parent_type.type_data.value_type)
                curr_comp._final_type = core.MapType(parnet_type.key_type, curr_comp._final_type)
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

