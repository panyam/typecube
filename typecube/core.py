
class Type(object):
    def __init__(self, param_names = None):
        self.param_names = param_names or []
        self.validator = self.default_validator
        self.docs = ""
        self.label = ""

    def set_label(self, label):
        self.label = label
        return self

    def set_docs(self, docs):
        self.docs = docs
        return self

    def set_validator(self, validator):
        self.validator = validator
        return self

    def __getitem__(self, type_vals):
        if type(type_vals) is not list:
            type_vals = [type_vals]
        param_values = dict(zip(self.param_names, type_vals))
        return self.apply(**param_values)

    def apply(self, **param_values):
        return TypeApp(self, **param_values)

    @classmethod
    def default_validator(cls, data, thetype):
        assert False, "Default validator not implemented"

class TypeApp(Type):
    def __init__(self, target_type, **param_values):
        self.param_values = {}
        self.root_type = target_type
        if isinstance(target_type, TypeApp):
            self.root_type = target_type.root_type
            self.param_values.update(target_type.param_values)
            # now only update *new* values that have not been duplicated
            for k,v in param_values.iteritems():
                if k in target_type.param_names:
                    self.param_values[k] = v

class TypeVar(Type):
    """ A type variable. """
    resolved_type = None

class NativeType(Type):
    """ A native type whose details are not known but cannot be inspected further - like a leaf type. """
    pass

class Field(object):
    """ Each child type in a container type is captured in a TypeField. """
    def __init__(self, field_type, name = None):
        self.field_type = field_type
        self.name = name

class ContainerType(Type):
    """ Non leaf types.  These include:

        Product types (Records, Tuples, Named tuples etc) and 
        Sum types (Eg Unions, Enums (Tagged Unions), Algebraic Data Types.
    """
    def __init__(self, param_names = None):
        Type.__init__(self, param_names)
        self.children = []

    def add_children(self, *fields):
        for f in fields:
            self.add_child(f)
        return self

    def add_child(self, field):
        if field.name and field.name in [c.name for c in self.children if c.name]:
            assert False, "Child type with name '%s' already exists" % field.name
        self.children.append(field)
        return self

class TaggedType(ContainerType):
    """ A tagged type is a type constructor that can have 0 or more (unnamed) parameters.
    This is very much like a record type but the children are unnamed.
    This is also like a tuple type but unlike a tuple type this type has 
    a "first class" name.
    """
    def __init__(self, param_names = None, children = None):
        ContainerType.__init__(self, param_names)
        self.add_children(children)

class RecordType(ContainerType):
    def __init__(self, param_names = None):
        ContainerType.__init__(self, param_names)

class TupleType(ContainerType):
    def __init__(self, param_names = None):
        ContainerType.__init__(self, param_names)

class UnionType(ContainerType):
    def __init__(self, param_names = None):
        ContainerType.__init__(self, param_names)

class FunctionType(Type):
    input_types = None
    return_type = None

