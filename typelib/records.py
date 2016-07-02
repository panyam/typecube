
import utils
import errors
import core
import ipdb

def RecordType(record_data = None):
    record_data = record_data or Record()
    return core.Type("record", record_data)

class Record(object):
    class SourceRecordRef(object):
        def __init__(self, record_fqn, record_type, alias):
            self.record_fqn = record_fqn
            self.alias = alias
            self.record_type = record_type

    def __init__(self, enclosing_projection = None, field_projections = None):
        """Creates a new Record declaration.
        Arguments:
        enclosing_projection    --  The projection in which the record is being defined (either as a record mutation or as a brand new record).  
                                    If this is not provided then this record is being defined independantly at the top level.
        field_projections       --  List of projections that describe field declarations.
        """
        self.enclosing_projection = enclosing_projection
        self.field_projections = field_projections or []
        self.resolved = True
        self.fields = {}
        self.source_records = []

    @property
    def root_record(self):
        if self.enclosing_projection is None:
            return self
        return self.enclosing_projection.parent_record.root_record

    @property 
    def is_resolved(self):
        return self._resolved

    def add_field(self, field):
        if field.name in self.fields:
            raise errors.DuplicateFieldException(field.name)
        self.fields[field.name] = field

    def add_projection(self, projection):
        """
        Add a projection.
        """
        self._resolved = False
        self.projections.append(projection)
        # TODO: see if this field declaration can be resolved.

    def add_source_record(self, source_fqn, source_type, alias = None):
        """
        Add a new source record that this record derives from.
        """
        n,ns,fqn = utils.normalize_name_and_ns(source_fqn)
        alias = alias or n
        if self.find_source(alias) is not None:
            raise TLException("A source by name '%s' already exists" % n)
        self.source_records.append(Record.SourceRecordRef(source_fqn, source_type, alias))

    def find_source(self, name):
        """
        Find a source by a given name.
        """
        for source_rec_ref in self.source_records:
            if source_rec_ref.alias == alias:
                return source_rec_ref.record_fqn
        return None

    @property
    def has_sources(self):
        return self.source_count > 0

    @property
    def source_count(self):
        return len(self.source_records)


    def resolve(self, thetype, registry, resolver):
        """
        Tries to resolve all dependencies for this record.

        Resolution does the following:

            1. First check if registry has all the sources.  If any of the sources are missing 
               an UnresolvedType exception is thrown.
            2. 
        """
        # Step 1: Check if source records are resolved and if they are then throw unresolved types exception if sources are missing
        unresolved_types = set()
        for source_rec_ref in self.source_records:
            if source_rec_ref.record_type is None or source_rec_ref.record_type.is_unresolved:
                source_rec_type = registry.get_type(source_rec_ref.record_fqn)
                if source_rec_type is None or source_rec_type.is_unresolved:
                    unresolved_types.add(source_rec_ref.record_fqn)
                else:
                    source_rec_ref.record_type = source_rec_type

        if len(unresolved_types) > 0:
            raise errors.TypesNotFoundException(*list(unresolved_types))

        # Step 2: Now go through declarations and resolve into fields
        unresolved_types = set()
        for proj in self.projections:
            try:
                proj.resolve(registry)
            except errors.TypesNotFoundException, exc:
                unresolved_types.add(exc.missing_types)

        if len(unresolved_types) > 0:
            raise errors.TypesNotFoundException(*list(unresolved_types))

        # otherwise all of these are resolved so create our field list from these
        self.fields = {}
        for proj in self.projections:
            for field in proj.resolved_fields:
                self.add_field(field)
        return True

class Projection(object):
    """
    Projections are a way of declaring a dependencies between a fields.
    """
    def __init__(self, parent_record, source_field_path, target_type, target_name,
            is_optional = None, default_value = None, selected_children = None,
            annotations = None):
        """Creates a projection.
        Arguments:
        parent_record       --  The parent record in which the projections are defined.
        source_field_paths  --  The list of components denoting the field path.   If the first value is an empty 
                                string, then the field path indicates an absolute path.
        target_name         --  Specifies whether the field projected from the source path is to be renamed.  
                                If None then the same name as the source field path is used.
        target_type         --  Specifies whether the field is to be re-typed in the destination record.
        is_optional         --  Whether the field is optional.  
                                    If True/False field is optional or required.
                                    If None then this value is derived from the source field.
        default_value       --  Default value of the field.  If None, then the value is the default_value 
                                of the source field.
        selected_children   --  The list of child fields that are selected in a single sweep.  If this field is 
                                specified then is_optional, default_value, target_name, and target_type are ignored 
                                and MUST NOT be specified.  If this value is the string "*" then ALL children all
                                selected.  When this is specified, the source field MUST be of a record type.
        annotations         --  Any annotations that apply to this projection (common ones are type mappers).
        """
        self.source_field_path = source_field_path
        self.target_type = target_type
        self.target_name = target_name
        self.is_optional = is_optional
        self.default_value = default_value
        self.selected_children = selected_children
        self.annotations = annotations or []
        self.inverted = False
        self._resolved = False

        if selected_children is not None:
            assert target_type is None and \
                   target_name is None and \
                   is_optional is None and \
                   default_value is None, \
                   "When selected_children is specified, target_type, target_name, default_value and is_optional must all be None"

        # Parameters that are inputs to type streaming.  If these 
        self.stream_params = None

        # TODO: should each projection also have a "param name"?   We could be referring to a record to 
        # begin from, but we could also 

        # How to do bindings?  A projection is really referring to a "field" or "param" outside its scope.
        # How to bring in concept of scopes?   Should types themselves have parents?
        # We can do it in a few ways, each projection or a type can point to its enclosing/parent type.
        # and each projection, but then projections themselves must have a concept of parent records and
        # records must have concepts of parent projections (ie the projection they are created in) so we
        # can traverse up a chain if need be.  
        self.bindings = None

    @property
    def resolved(self):
        return self._resolved

class FieldDeclaration(object):
    """
    Describes a field declaration.  The same declaration is used for both mutating an 
    existing field as well as adding new fields as well removing existing fields.

    A Field declaration will be remain in an "unresolved" state until all its 
    dependant types are also provided.
    """
    def __init__(self, source_record, starting_record_type, field_path_parts,
                 starts_at_root = False, negates_inclusion = False, annotations = None):
        # How the retyping happens.   THis can happen in one of a few ways:
        self.type_stream = None

    @property
    def all_fields_selected(self):
        return self.child_fields is None

    def resolve(self, registry):
        """
        Starting from the source_record's source types resolve the type of this given field.
        """
        if self.resolved:
            return True

        # How to find the source record given the first part in the field path parts?
        # If source record has 1 type then the first part must NOT refer to the source type - it must be part of the field path
        # If the source record has 0 or more than 1 sources, then first part MUST refer to a valid type (in the registry or source list), otherwise unresolved type exception
        record_data = self.source_record.type_data
        source_type = None
        real_field_path_parts = self.field_path_parts
        if record_data.source_count == 1:
            source_type = record_data.source_records[0].record_type
        elif record_data.source_count == 0:
            source_type = registry.get_type(self.field_path_parts[0])
            real_field_path_parts = self.field_path_parts[1:]

        self.source_type = source_type
        self.field_path = FieldPath(self.source_type, self.field_path_str)
        self.resolved = True
        return self.resolved

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

