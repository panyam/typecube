
import utils
import errors
import core
import ipdb

def RecordType(record_data = None):
    record_data = record_data or Record(None)
    return core.Type("record", record_data)

class Record(object):
    class SourceRecordRef(object):
        def __init__(self, record_fqn, record_type, alias):
            self.record_fqn = record_fqn
            self.alias = alias
            self.record_type = record_type

        def __repr__(self):
            return str(self)

        def __str__(self):
            return "%s as %s" % (self.record_fqn, self.alias)

    def __init__(self, fqn, parent_entity = None, field_projections = None):
        """Creates a new Record declaration.
        Arguments:
            fqn                     --  Fully qualified name of the record.  Records should have names.
            parent_entity           --  The parent record or projection inside which this record is declared (as an inner declaration)
                                        If this is not provided then this record is being defined independantly at the top level.
            field_projections       --  List of projections that describe field declarations.
        """
        self.fqn = fqn
        self._parent_entity = parent_entity
        self.field_projections = field_projections or []
        self.resolved = True
        self.fields = {}
        self.source_records = []
        self.bindings = Bindings()

    @property
    def parent_entity(self):
        return self._parent_entity

    @parent_entity.setter
    def parent_entity(self, value):
        None.a = 3

    def __repr__(self):
        return "<Name: '%s', Fields: (%s)>" % (self.fqn, ", ".join(map(repr, self.fields)))

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
        if name in self.fields:
            return self, field_path
        return None, None

    def add_field(self, field):
        if field.name in self.fields:
            raise errors.DuplicateFieldException(field.name)
        self.fields[field.name] = field

    def add_projection(self, projection):
        """
        Add a projection.
        """
        self._resolved = False
        self.field_projections.append(projection)
        # TODO: see if this field declaration can be resolved.

    def add_source_record(self, source_fqn, source_type, alias = None):
        """
        Add a new source record that this record derives from.
        """
        n,ns,fqn = utils.normalize_name_and_ns(source_fqn, None)
        alias = alias or n
        if self.find_source(alias) is not None:
            raise errors.TLException("A source by name '%s' already exists" % n)
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
    def is_resolved(self):
        return self._resolved

    @property
    def has_sources(self):
        return self.source_count > 0

    @property
    def source_count(self):
        return len(self.source_records)


    def resolve(self, registry):
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
                if source_rec_type is None:
                    unresolved_types.add(source_rec_ref.record_fqn)
                elif source_rec_type.is_unresolved:
                    source_rec_type.resolve(registry)
                    if source_rec_type.is_unresolved:
                        unresolved_types.add(source_rec_ref.record_fqn)
                else:
                    source_rec_ref.record_type = source_rec_type

        if len(unresolved_types) > 0:
            raise errors.TypesNotFoundException(*list(unresolved_types))

        # Step 2: Now go through declarations and resolve into fields
        unresolved_types = set()
        for proj in self.field_projections:
            try:
                proj.resolve(registry)
            except errors.TypesNotFoundException, exc:
                unresolved_types.add(exc.missing_types)

        if len(unresolved_types) > 0:
            raise errors.TypesNotFoundException(*list(unresolved_types))

        # otherwise all of these are resolved so create our field list from these
        self.fields = {}
        for proj in self.field_projections:
            for field in proj.resolved_fields:
                self.add_field(field)

        self._resolved = True
        return True

PROJECTION_TYPE_PLAIN        = 0
PROJECTION_TYPE_RETYPE      = 1
PROJECTION_TYPE_MUTATION    = 2
PROJECTION_TYPE_STREAMING   = 3

class Projection(object):
    """
    Projections are a way of declaring a dependencies between fields in a record.
    """
    def __init__(self, parent_entity, field_path, target_name, target_type, annotations):
        """Creates a projection.
        Arguments:
        field_path      --  A FieldPath instance that contains the field path to the source field as well 
                            as any child field selectors if any.
        target_name     --  Specifies whether the field projected from the source path is to be renamed.  
                            If None then the same name as the source field path is used.
        target_type     --  Specifies whether the field is to be re-typed in the destination record.
        is_optional     --  Whether the field is optional.  
                                If True/False field is optional or required.
                                If None then this value is derived from the source field.
        default_value   --  Default value of the field.  If None, then the value is the default_value 
                            of the source field.
        """
        # Two issues to consider:
        # 1. Matter of scopes - ie how variables names or names in general are bound to?  Should scopes just be 
        #    dicts or should we have "scope providers" where records and projections all participate?
        # 2. Should any kind of type change just be a function that creates a new type given the current
        #    lexical scope?
        if field_path is None or field_path.is_blank:
            field_path = None
        self.field_path = field_path
        self.target_name = target_name
        self._resolved_type = None
        self.is_optional = None
        self.default_value = None
        self.target_type = target_type
        self.projection_type = PROJECTION_TYPE_PLAIN
        if target_type:
            self.projection_type = PROJECTION_TYPE_RETYPE
        self.annotations = annotations or []
        self.resolved_fields = []
        self._resolved = False
        self._parent_entity = parent_entity
        self.path_resolver = PathResolver(parent_entity)

    @property
    def parent_entity(self):
        return self._parent_entity

    @parent_entity.setter
    def parent_entity(self, value):
        None.a = 3

    @property
    def root_record(self):
        if type(self.parent_entity) is Projection:
            return self.parent_entity.root_record
        else:
            # must be a record otherwise
            return self.parent_entity.type_data.root_record

    def get_binding(self, field_path):
        """
        Gets a particular binding by a given name.  For a projection, this is the parameter
        by the given name if the projection type is streaming otherwise if the projection
        type is a mutation then the resolved value is the type of the field within the 
        record (from the source).
        """
        if self.target_type:
            first_part = field_path.get(0)
            for index,param in enumerate(self.target_type.param_names):
                if param == first_part:
                    type_arg = self.source_field.field_type.type_args[index]
                    return type_arg.type_data, FieldPath(field_path._parts[1:], field_path.selected_children)
        return None, None

    @property
    def is_resolved(self):
        return self._resolved

    def resolve(self, registry):
        """
        Resolution of a projection is where the magic happens.  By the end of it the following need to fall in place:

            1. New fields must be created for each projection with name, type, optionality, default values (if any) set.
            2. MOST importantly, for every generated field that is not a new field (ie is projected from an existing 
               field in *some other* record), a dependency must be marked so that when given an instance of the 
               "source type" the target type can also be populated.  The second part is tricky.  How this dependency 
               is generated and stored requires the idea of scopes and bindings.   This is also especially trickier when 
               dealing with type streaming as scopes need to be created in each iteration of a stream.

        Resolution only deals with creation of all mutated records (including within type streams).  
        No field dependencies are generated yet.   This can be done in the next pass (and may not even be required
        since the projection data can be stored as part of the fields).
        """
        if self.is_resolved:
            return True

        if self.field_path and self.field_path.selected_children is not None:
            assert self.target_name is None and \
                   self.target is None or (
                            self.target_type is None and     \
                            self.is_optional is None and     \
                            self.default_value is None),     \
                   "When selected_children is specified, target_type, target_name, default_value and is_optional must all be None"

        self.source_field = None
        self.starting_record = None

        if self.field_path:
            if str(self.field_path) == "ind/labels":
                ipdb.set_trace()
            self.resolve_source_fields(registry)
            source_field = self.source_field
            starting_record = self.starting_record
            # Once fields are created, check for the streaming and other field type constraints
            # If there are binding params, see whether the number match the source_field.field_type's type args
            if self.target_type and self.projection_type == PROJECTION_TYPE_STREAMING:
                if len(self.target_type.param_names) != source_field.field_type.arglimit:
                    raise errors.TLException("Number of streamed arguments does not match argument count of type")

        # Now that the source field has been resolved, we can start resolving target type for
        # mutations and streamings
        self.resolve_target(registry)

        self._resolved = True
        return self.is_resolved

    def resolve_source_fields(self, registry):
        # Find the source field given the field path and the parent record
        # This should give us the field that will be copied to here.
        self.starting_record, self.source_field, self.final_field_path = self.path_resolver.resolve_path(self, registry)

        source_field = self.source_field
        starting_record = self.starting_record

        if source_field:
            if self.field_path.has_children:
                self._include_child_fields(source_field.field_type)
            else:
                target_type = source_field.field_type
                is_optional = source_field.is_optional
                default_value = source_field.default_value

                if self.target_type:
                    target_type = self.target_type
                if self.is_optional:
                    is_optional = self.is_optional
                if self.default_value:
                    default_value = self.default_value

                newfield = Field(self.target_name or source_field.name,
                                        target_type,
                                        self.parent_entity,
                                        is_optional,
                                        default_value,
                                        source_field.documentation,
                                        self.annotations or source_field.annotations)
                self._add_field(newfield)
        else:
            # The Interesting case.  source field could not be found or resolved.
            # There is a chance that this is a "new" field.  That will only be the case if field path has a single entry
            # and target name is not provided and we are not a type stream
            print "FieldPath: ", self.field_path
            if self.field_path.has_children:
                if self.field_path.length == 0 and starting_record != None:
                    # then we are starting from the root itself of the starting record as "multiple" entries
                    self._include_child_fields(starting_record)
                else:
                    raise errors.TLException("New Field '%s' in '%s' must not have child selections" % (self.field_path, self.parent_entity.type_data.fqn))
            elif self.target_name is not None:
                raise errors.TLException("New Field '%s' in '%s' should not have a target_name" % (self.field_path, self.parent_entity.type_data.fqn))
            elif self.target_type is None:
                ipdb.set_trace()
                raise errors.TLException("New Field '%s' in '%s' does not have a target_type" % (self.field_path, self.parent_entity.type_data.fqn))
            elif self.field_path.length > 1:
                raise errors.TLException("New Field '%s' in '%s' must not be a field path" % (self.field_path, self.parent_entity.type_data.fqn))
            else:
                newfield = Field(self.field_path.get(0),
                                        self.target_type,
                                        self.parent_entity,
                                        self.is_optional if self.is_optional is not None else False,
                                        self.default_value,
                                        "",
                                        self.annotations)
                self._add_field(newfield)

    def _include_child_fields(self, starting_record):
        if not self.field_path.all_fields_selected:
            missing_fields = set(self.field_path.selected_children) - set(starting_record.type_data.fields.keys())
            if len(missing_fields) > 0:
                raise errors.TLException("Invalid fields in selection: '%s'" % ", ".join(list(missing_fields)))
        selected_fields = self.field_path.get_selected_fields(starting_record)
        for field in selected_fields.values():
            newfield = Field(field.name, field.field_type, self.parent_entity,
                                field.is_optional, field.default_value, field.documentation,
                                self.annotations or field.annotations)
            self._add_field(newfield)

    def _add_field(self, newfield):
        self.resolved_fields.append(newfield)

    @property
    def resolved_type(self):
        if self.projection_type == PROJECTION_TYPE_STREAMING:
            return self._resolved_type
        else:
            return self.target_type

    def resolve_target(self, registry):
        field_path = self.field_path
        source_field = self.source_field
        parent_entity = self.parent_entity
        if self.projection_type == PROJECTION_TYPE_MUTATION:
            if self.target_type is None:
                raise errors.TLException("Record MUST be specified on a mutation")

            if field_path and field_path.has_children or len(self.resolved_fields) > 1:
                raise errors.TLException("Record mutation cannot be applied when selecting multiple fields")

            # The parent fqn is required because the new record name is based on that.
            # The projection can be in two forms:
            if type(parent_entity) is core.Type:
                # 1. Inside a record or another type
                parent_fqn = parent_entity.type_data.fqn
            else:
                # 2. Inside another projection - ie within a type streaming declaration
                assert self.parent_entity.projection_type == PROJECTION_TYPE_STREAMING
                parent_fqn = parent_entity.source_field.fqn

            if not parent_fqn:
                # Parent name MUST be set otherwise it means parent resolution would have failed!
                raise errors.TLException("Parent record name not set.  May be it is not yet resolved?")

            if self.resolved_fields:
                field_name = self.resolved_fields[0].name
                if not field_name:
                    raise errors.TLException("Source field name is not set.  May be it is not yet resolved?")

                field_type = self.resolved_fields[0].field_type
                if not field_type:
                    raise errors.TLException("Source field name is not set.  May be it is not yet resolved?")

                if field_type.constructor != "record":
                    raise errors.TLException("Cannot mutate a type that is not a record.  Yet")
            else:
                assert self.parent_entity.projection_type == PROJECTION_TYPE_STREAMING
                proj_index = parent_entity.target_type.projections.index(self)
                field_name = "_ta__%d" % proj_index

            if self.target_type.type_data.fqn is None:
                parent_name,ns,parent_fqn = utils.normalize_name_and_ns(parent_fqn, None)
                self.target_type.type_data.fqn = parent_fqn + "_" + field_name
                ipdb.set_trace()
                self.target_type.type_data.parent_entity = self
                if source_field:
                    self.target_type.type_data.add_source_record(source_field.field_type.type_data.fqn, source_field.field_type)
                if not self.target_type.resolve(registry):
                    raise errors.TLException("Could not resolve record mutation for field '%s' in record '%s'" % (field_name, parent_fqn))
        elif self.projection_type == PROJECTION_TYPE_STREAMING:
            # Here we have to resolve target of the streamed type.
            # Do this by resolving each of the projections into a child type and create a constructed
            # type with these child types as the arguments.

            # TODO: Create a second registry here that contains the bindings so that we know which "new" types are to be 
            #       used temporarily in a hierarchical fashion.
            # TODO: Investigate what "hints" can be added to this projection that directly refers to child entries
            #       that can be used to do getters/setters
            for index,proj in enumerate(self.target_type.projections):
                proj.resolve(registry)
            child_types = [ proj.resolved_type for proj in self.target_type.projections ]
            self._resolved_type = core.Type(self.constructor, None, *child_types)

class FieldPath(object):
    def __init__(self, parts, selected_children = None):
        """
        Arguments:
        parts               --  The list of components denoting the field path.   If the first value is an empty 
                                string, then the field path indicates an absolute path.
        selected_children   --  The list of child fields that are selected in a single sweep.  If this field is 
                                specified then is_optional, default_value, target_name, and target_type are ignored 
                                and MUST NOT be specified.  If this value is the string "*" then ALL children all
                                selected.  When this is specified, the source field MUST be of a record type.
        """
        self.inverted = False
        parts = parts or []
        if type(parts) in (str, unicode):
            parts = parts.strip()
            parts = parts.split("/")
        self._parts = parts
        self.selected_children = selected_children or None

    def __repr__(self): 
        return str(self)

    def __str__(self):
        if self.all_fields_selected:
            return "%s/*" % "/".join(self._parts)
        elif self.has_children:
            return "%s/(%s)" % ("/".join(self._parts), ", ".join(self.selected_children))
        else:
            return "/".join(self._parts)

    @property
    def length(self):
        if self.is_absolute:
            return len(self._parts) - 1
        else:
            return len(self._parts)

    def get(self, index):
        """
        Gets the field path part at a given index taking into account whether the path is absolute or not.
        """
        if self.is_absolute:
            index += 1
        return self._parts[index]

    @property
    def is_blank(self):
        return len(self._parts) == 0

    @property
    def is_absolute(self):
        if len(self._parts) == 0:
            ipdb.set_trace()
        return self._parts[0] == ""

    @property
    def has_children(self):
        return self.selected_children is not None

    @property
    def all_fields_selected(self):
        return self.selected_children == "*"

    def get_selected_fields(self, starting_record):
        """
        Given a source field, return all child fields as per the selected_fields spec.
        """
        fields = starting_record.type_data.fields
        if self.all_fields_selected:
            return fields
        else:
            return dict([(k,v) for (k,v) in fields.iteritems() if k in self.selected_children])

class Field(object):
    """
    Holds all information about a field within a record.
    """
    def __init__(self, name, field_type, record, optional = False, default = None, docs = "", annotations = None):
        assert type(name) in (str, unicode), "Found type: '%s'" % type(name)
        # assert isinstance(field_type, core.Type), type(field_type)
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
        if self.record.type_data.fqn:
            return self.record.type_data.fqn + "." + self.name
        else:
            return self.name

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

class Bindings(object):
    """
    Keeps track where certain names are bound to.   Bindings are created when
    a record is created and popped off when they are done with.
    """
    def __init__(self, parent = None):
        self.parent = None
        self.bound_vars = {}

    def push(self):
        """
        Push and start a new scope.
        """
        return Bindings(self)

    def set(self, name, data_type):
        """
        Creates a new binding at the given scope.
        In any scope from this one and "above", any reference to the variable by the given name
        will resolve to the provided data_type.   This check is done only after the parent record
        check has gone through (and assuming the field path is not an absolute path).
        """
        if name in self.bound_vars:
            raise errors.TLException("'%s' already exists in current scope" % name)
        self.bound_vars[name] = data_types

    def get(self, name):
        """
        Gets the "type" associated with a particular name.
        """
        if name in self.bound_vars:
            return self.bound_vars[name]
        elif self.parent:
            return self.parent.get(name)
        else:
            raise errors.TLException("Name '%s' not found in scope" % name)



class TypeStreamDeclaration(object):
    def __init__(self, constructor_fqn, param_names, projections):
        self.constructor = constructor_fqn
        self.param_names = param_names or []
        self.projections = projections

class PathResolver(object):
    """
    PathResolver interface resolvers need to do one thing.  They take in a 
    field path and return three things:

        1. The starting record from which the field path is a valid path.
        2. The source field nested (at some arbitrary depth) from the starting record
           that corresponds to the provided field path.
        3. The final field path that is RELATIVE to the starting record.  Concpetually:
              starting_record + final_field_path = current_context + input_field_path
    """
    def __init__(self, parent_entity):
        self.parent_entity = parent_entity

    def resolve_path(self, projection, registry):
        """
        This is the tricky bit.  Given our current field path, we need to find the source type and field within 
        the type that this field path corresponds to.
        """
        if not projection.field_path:
            return None, None, None

        field_path = projection.field_path
        final_field_path = field_path

        if field_path.is_absolute:
            # then first find the root record
            starting_record = projection.root_record.source_records[0].record_type.type_data
            final_field_path = FieldPath(field_path._parts[1:], field_path.selected_children)
        else:
            # otherwise get the first type in the parent hierarchy that matches the name first field path part
            curr_entity = projection.parent_entity
            starting_record = None
            while curr_entity:
                if type(curr_entity) is core.Type:
                    record_data = curr_entity.type_data
                    if record_data.source_count > 1:
                        raise errors.TLException("Multiple source derivation not yet supported")
                    elif record_data.source_count == 1:
                        source_record = record_data.source_records[0].record_type.type_data
                        starting_record, final_field_path = source_record.get_binding(field_path)
                        if starting_record:
                            break
                    curr_entity = record_data.parent_entity
                elif type(curr_entity) is Projection:
                    # check for bindings for the first name
                    starting_record, final_field_path = curr_entity.get_binding(field_path)
                    if starting_record:
                        break
                    curr_entity = record_data.parent_entity
                else:
                    assert False

        final_record = starting_record
        final_field = None
        if starting_record:
            # we have something to start off from so see if the full path is viable
            # resolve the field path from the starting record
            for i,part in  enumerate(final_field_path._parts):
                if type(final_record) is not Record:
                    # Cannot be resolved as the ith part from the source_record is NOT of type record
                    # so we cannot go any further
                    return starting_record, None, None
                if not final_record.is_resolved:
                    final_record.resolve(registry)
                fields = final_record.fields
                if part not in fields:
                    return starting_record, None, None
                final_field = fields[part]
                final_record = final_field.field_type.type_data
        return starting_record, final_field, final_field_path
