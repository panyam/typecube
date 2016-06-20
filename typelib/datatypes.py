
import ipdb
import errors
from annotations import *
from type_classes import *

class Type(object):
    def __init__(self, type_class, name = "", ns = "", docs = "", type_data = None):
        self.type_class = type_class
        self.type_data = type_data
        self.source_type_specs = []
        self.parent_type = None
        self.key_in_parent = None
        self.name = name or ""
        self.namespace = ns or ""
        self.documentation = docs

    def copy_from(self, another):
        self.type_class = another.type_class
        self.type_data = another.type_data
        self.source_type_specs = another.source_type_specs
        self.parent_type = another.parent_type
        self.key_in_parent = another.key_in_parent
        self.name = another.name
        self.namespace = another.namespace
        self.documentation = another.documentation

    @property
    def name(self):
        return self.__name

    @property
    def namespace(self):
        return self.__namespace

    @property
    def fqn(self):
        return self.namespace + "." + self.name if self.namespace else self.name

    @name.setter
    def name(self, value):
        import utils
        n,ns,_ = utils.normalize_name_and_ns(value, "")
        self.__name = n
        if ns:
            self.namespace = ns

    @namespace.setter
    def namespace(self, value):
        self.__namespace = value

    def __str__(self):
        out = self.fqn
        if self.type_data:
            return "[%s: %s]" % (out, str(self.type_data))
        return out

    @property
    def signature(self):
        return self.type_data.signature(self) if self.type_data else self.fqn

    @property
    def list_type(self):
        # TODO - move this to template/generator backend as this is
        # really backend/langauge dependant and will/may require
        # changes to how signature is generated and used
        fqn = self.fqn
        if self.type_class == BASIC_TYPE:
            fqn = self.name[0].upper() + self.name[1:]
        return fqn + "Array"

    def resolve_field_from_path(self, field_path):
        return self.type_data.resolve_field_from_path(self, field_path)

    def to_json(self, visited):
        if self.fqn:
            if self.fqn in visited:
                return self.fqn
            if visited is not None:
                visited[self.fqn] = True
        if self.type_data:
            return self.type_data.to_json(self, visited = visited)
        else:
            return self.fqn

    @property
    def is_null_type(self):
        return self.type_class == NULL_TYPE

    @property
    def is_resolved(self):
        return self.type_class is not None and self.type_class != UNRESOLVED_TYPE

    @property
    def is_unresolved(self):
        return not self.is_resolved

    @property
    def is_basic_type(self):
        return self.type_class == BASIC_TYPE

    @property
    def is_alias_type(self):
        return self.type_class == ALIAS_TYPE

    @property
    def is_reference_type(self):
        return self.type_class == REFERENCE_TYPE

    @property
    def is_tuple_type(self):
        return self.type_class == TUPLE_TYPE

    @property
    def is_record_type(self):
        return self.type_class == RECORD_TYPE

    @property
    def is_function_type(self):
        return self.type_class == FUNCTION_TYPE

    @property
    def is_list_type(self):
        return self.type_class == LIST_TYPE or \
                (self.type_class == ALIAS_TYPE and self.type_data.value_type.is_list_type)

    @property
    def is_set_type(self):
        return self.type_class == SET_TYPE or \
                (self.type_class == ALIAS_TYPE and self.type_data.value_type.is_set_type)

    @property
    def is_map_type(self):
        return self.type_class == MAP_TYPE or \
                (self.type_class == ALIAS_TYPE and self.type_data.value_type.is_map_type)

    @property
    def is_enum_type(self):
        return self.type_class == ENUM_TYPE

    @property
    def is_fixed_type(self):
        return self.type_class == FIXED_TYPE

    @property
    def is_union_type(self):
        return self.type_class == UNION_TYPE

    @property
    def is_value_type(self):
        if self.type_class in (ReferenceType, ListType, MapType, SetType, FunctionType):
            return False
        elif self.type_class == ALIAS_TYPE:
            return self.type_data.target_type.is_value_type
        elif self.type_class == BASIC_TYPE:
            return True
        elif self.type_class == RECORD_TYPE:
            return not self.type_data.is_reference_type
        return False

    @property
    def leaf_type(self):
        if self.type_class == BASIC_TYPE:
            return self.type_data
        elif self.type_class in (ALIAS_TYPE, REFERENCE_TYPE):
            return self.type_data.target_type.leaf_type()
        elif self.type_class == RECORD_TYPE:
            return self.type_data
        return None

BooleanType = Type(BASIC_TYPE, "boolean")
IntType = Type(BASIC_TYPE, "int")
LongType = Type(BASIC_TYPE, "long")
FloatType = Type(BASIC_TYPE, "float")
DoubleType = Type(BASIC_TYPE, "double")
StringType = Type(BASIC_TYPE, "string")

class AliasTypeData(object):
    def __init__(self, target_type):
        self.target_type = target_type

    def signature(self, thetype):
        return thetype.fqn

    def to_json(self, thetype, visited = None):
        # return '"%s"' % thetype.fqn
        return self.target_type.to_json(visited)

    def resolve_field_from_path(self, thetype, field_path):
        return self.target_type.resolve_field_from_path(field_path)

class FixedTypeData(object):
    def __init__(self, size):
        self.type_size = size

    def signature(self, thetype):
        return "Fixed<%d>" % self.type_size

    def to_json(self, thetype, visited = None):
        out = {
            "type": "fixed",
            "size": self.type_size,
            "doc": thetype.documentation
        }
        if thetype.name:
            out["name"] = thetype.fqn
        if thetype.namespace:
            out["namespace"] = thetype.namespace
        return out


class ReferenceTypeData(object):
    def __init__(self, target_type):
        self.target_type = target_type

class MapTypeData(object):
    def __init__(self, key_type, value_type):
        self.key_type = key_type
        self.value_type = value_type

    def signature(self, thetype):
        return "Map<%s => %s>" % (self.key_type.signature, self.value_type.signature)

    def __str__(self):
        return "<%s,%s>" % (str(self.key_type), str(self.value_type))

    def to_json(self, thetype, visited = None):
        return {"type": "map", "values": self.value_type.to_json(visited = visited)}

class SetTypeData(object):
    def __init__(self, value_type):
        self.value_type = value_type

    def signature(self, thetype):
        return "[ %s ]" % (self.value_type.signature)

    def to_json(self, thetype, visited = None):
        return {"type": "set", "items": self.value_type.to_json(visited = visited)}

    def resolve_field_from_path(self, thetype, field_path):
        return self.value_type.resolve_field_from_path(field_path)

class ParametricTypeData(object):
    def __init__(self, type_name, *param_names_and_types):
        self.type_name = type_name
        self.param_names = [n for n,v in param_names_and_types]
        self.param_types = [v for n,v in param_names_and_types]

    def signature(self, thetype):
        param_types = [t.to_json(visited = visited) for t in self.param_types]
        return "%s[ %s ]" % (self.type_name, ",".join(param_types))

    def to_json(self, thetype, visited = none):
        return {"type": self.type_name, "params": dict(izip(self.param_names, self.param_types))}

class ListTypeData(object):
    def __init__(self, value_type):
        self.value_type = value_type

    def signature(self, thetype):
        return "[ %s ]" % (self.value_type.signature)

    def to_json(self, thetype, visited = none):
        return {"type": "array", "items": self.value_type.to_json(visited = visited)}

    def resolve_field_from_path(self, thetype, field_path):
        return self.value_type.resolve_field_from_path(field_path)

class TupleTypeData(object):
    def __init__(self, *child_types):
        self.child_types = child_types 

    def signature(self, thetype):
        return "( %s )" % ",".join([x.signature for x in self.child_types])

    def __str__(self):
        return "<%s>" % ",".join(map(str, self.child_types))

    def to_json(self, thetype, visited = None):
        return {"type": "map", "values": self.value_type.to_json(visited = visited)}

class EnumTypeData(object):
    class Symbol(object):
        def __init__(self, name, annotations = [], doc = ""):
            self.name = name
            self.annotations = annotations
            self.doc = doc

        def to_json(self):
            return self.name

    def __init__(self, *symbols):
        self.symbols = list(*symbols)
        self.source_types = []
        self.annotations = []

    def signature(self, thetype):
        return "Enum<%s>" % thetype.fqn
    
    def add_symbol(self, name, annotations = [], doc = ""):
        self.symbols.append(EnumTypeData.Symbol(name, annotations, doc))

    def __str__(self):
        return "[%s: %s]" % (self.name, ",".join(self.symbols))

    def to_json(self, thetype, visited = None):
        out = {
            "type": "enum",
            "doc": thetype.documentation, 
            "symbols": [s.to_json() if type(s) not in (str,unicode) else s for s in self.symbols]
        }

        if thetype.name:
            out["name"] = thetype.fqn
        return out

class UnionTypeData(Type):
    def __init__(self, *child_types):
        self.child_types = [c for c in child_types]

    def signature(self, thetype):
        return "Union { %s }" % ",".join([x.signature for x in self.child_types])
    
    def add_type(self, child):
        self.child_types.append(child)

    def __str__(self):
        return "{%s}" % (",".join(["%s = %s" % (k,v) for (k,v) in self.child_types.iteritems()]))

    def to_json(self, thetype, visited = None):
        out = []
        for child in self.child_types:
            out.append(child.to_json(visited = visited))
        return out

def EnumType(name, namespace, *symbols):
    import utils
    n,ns,fqn = utils.normalize_name_and_ns(name, namespace)
    return Type(ENUM_TYPE, name = n, ns = ns, type_data = EnumTypeData(*symbols))

def UnionType(name, namespace, *child_types):
    import utils
    n,ns,fqn = utils.normalize_name_and_ns(name, namespace)
    return Type(UNION_TYPE, name = n, ns = ns, type_data = UnionTypeData(*child_types))

def AliasType(name, namespace, target_type): 
    import utils
    n,ns,fqn = utils.normalize_name_and_ns(name, namespace)
    out = Type(ALIAS_TYPE, name = n, ns = ns)
    out.type_data = AliasTypeData(target_type)
    return out

def ListType(value_type):
    return Type(LIST_TYPE, type_data = ListTypeData(value_type))

def MapType(key_type, value_type):
    return Type(MAP_TYPE, type_data = MapTypeData(key_type, value_type))

def RecordType(name, namespace = ""):
    import utils
    n,ns,fqn = utils.normalize_name_and_ns(name, namespace)
    return Type(RECORD_TYPE, name = n, ns = ns, type_data = RecordTypeData())

class SourceTypeSpec(object):
    """
    Keeps track of the source type that a given type "derives" from
    """
    def __init__(self, source_type, key = None, field_names = None):
        """
        Params:

            source_type     The source type that is being derived from.
            key             The alias for this derivation so that it can be used instead in field declarations
                            instead of the name of the source type.
            field_names     Names of fields being included/excluded.
        """
        assert source_type is not None
        self.source_type = source_type

        # TODO: This needs to be cleaned.  We are using SourceTypeSpec as common for all types.  Currently only 
        # unions/enums/records can have source type specs but fields only applies to records so this needs to be 
        # broken up to be type class specific.
        self.field_names = field_names
        self.key = key or source_type.name

class SourceTypeSpecList(object):
    def __init__(self):
        self.source_type_specs = []

    def __getitem__(self, index):
        return self.source_type_specs[index]

    @property
    def count(self):
        return len(self.source_type_specs)

    def add_spec(self, spec):
        # TODO: check this is not a duplicate
        self.source_type_specs.append(spec)

    def find_spec(self, name):
        """
        Finds the source type spec for a given name.
        """
        for source_type_spec in self.source_type_specs:
            if name == source_type_spec.key :
                return source_type_spec

        # Search by key failed so search by name or fqn
        for source_type_spec in self.source_type_specs:
            if name in (source_type_spec.source_type.name, source_type_spec.source_type.fqn):
                return source_type_spec

class RecordTypeData(object):
    """
    Records (or models).
    """
    AddMode_None = 0
    AddMode_Overwrite = 1
    AddMode_Replace = 2

    def __init__(self, annotations = None):
        self._is_reference_type = False
        self.fields = {}
        self.source_types = []
        self.annotations = annotations or []
        # list of field include specs.  This are lazily resolved
        # after all dependant types have been loaded and resolved
        self.field_includes = []

    def signature(self, thetype):
        return thetype.fqn

    def is_reference_type(self):
        return self._is_reference_type

    def set_is_reference_type(self, value):
        self._is_reference_type = value

    def resolve_field_from_path(self, thetype, field_path):
        starting_field = None
        while field_path:
            if not starting_field:
                if field_path[0].name not in self.fields:
                    raise errors.FieldNotFoundException(field_path[0].name, thetype)
                starting_field = self.fields[field_path[0].name]
            else:
                starting_field = starting_field.field_type.resolve_field_from_path([field_path[0]])
            field_path = field_path[1:]
        return starting_field

    def get_field(self, field_name):
        return self.fields[field_name]

    def add_field(self, field, mode = None):
        mode = mode or RecordTypeData.AddMode_None
        if field.name not in self.fields or mode == RecordTypeData.AddMode_Replace:
            self.fields[field.name] = field
            return
        elif self.contains_field(field.name) and mode == RecordTypeData.AddMode_None:
            raise errors.DuplicateFieldException(field.name, self)

        if mode == RecordTypeData.AddMode_Replace:
            self.fields[field.name] = field
        else:
            self.fields[field.name].copyfrom(field)

    def contains_field(self, name):
        return name and name in self.fields

    def set_fields(self, fields):
        self.fields = dict(map(lambda f: (f.name, f), fields))

    def remove_field(self, field_or_name):
        field_name = field_or_name
        if type(field_name) not in (str,  unicode):
            field_name = field_or_name.name
        if field_name in self.fields:
            del self.fields[field_name]

    def all_fields(self):
        return self.fields.values()

    def __str__(self):
        return "<Fields: %s>" % self.fields

    def add_field_include_spec(self, field_include):
        self.field_includes.append(field_include)

    @property
    def field_includes_resolved(self):
        return all(f.resolved for f in self.field_includes)

    def get_source_record(self, type_alias):
        for (alias, st) in self.source_types:
            if alias == type_alias:
                return st
        return None

    def add_source_record(self, source_type, type_alias = None):
        """
        Mark a record as a source for this record.
        If the type alias is not provided then the name of the source type
        is used.
        """
        if type_alias is None:
            type_alias = source_type.name
        for (alias, st) in self.source_types:
            if alias == type_alias:
                if source_type.fqn == st.fqn:
                    # already exists so dont add it again
                    return
                raise Exception("Alias '%s' previously pointing to '%s' now being redefined as '%s'" % type_alias, st.fqn, source_type.fqn)
        self.source_types.append((type_alias, source_type))

    def to_json(self, thetype, visited = None):
        fields = []
        out = {"type": "record",
               "name": thetype.fqn,
               "namespace": thetype.namespace,
               "doc": thetype.documentation,
               "fields": fields}
        if self.source_types:
            out["source_types"] = [y.fqn for x,y in self.source_types]
        for (name, field) in sorted(self.fields.iteritems(), lambda x,y: cmp(x[0], y[0])):
            # if name == "phoneNumbers": ipdb.set_trace()
            field_json = {"name": name}
            if field.field_type.name:
                field_json["type"] = field.field_type.fqn
            else:
                field_json["type"] = field.field_type.to_json(visited = visited)
            field_json["type"] = field_json["type"]  or field.field_type.signature
            if field.source_field_path:
                field_json["sourceField"] = str(field.source_field_path)
            if field.is_optional:
                field_json["optional"] = True
            if field.default_value is not None:
                field_json["default"] = field.default_value
            if field.documentation:
                field_json["doc"] = field.documentation
            fields.append(field_json)
        return out


    def handle_resolution(self, registry):
        """
        This idempotent method ensures that all field include rules are properly
        resolved (and ensuring that fields to be included are properly added).
        """
        if not self.field_includes_resolved:
            # All field includes have been reso
            for field_include in self.field_includes:
                # see what fields need to be created for this:
                if not field_includes_resolved:
                    source_type = self.get_source_record(field_include.source_record_name)
                    if not source_type:
                        raise Exception("Invalid alias '%s': " % field_include.source_record_name)
                    elif not source_type.is_resolved or not source_type.type_data.field_includes_resolved:
                        return False

                    # and create the appropriate type
                    new_fields = field_include.create_fields(source_type, self)
                    for field in new_fields:
                        self.add_field(field)
