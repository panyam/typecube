
class Type(object):
    def __init__(self, name, args = None):
        self.name = name
        self.args = args or []
        self.validator = None
        self.docs = ""

    def set_name(self, name):
        self.name = name
        return self

    def set_docs(self, docs):
        self.docs = docs
        return self

    def __repr__(self):
        out = "<%s(0x%x)" % (self.__class__.__name__, id(self))
        if self.name:
            out += ": " + self.name
        if self.args:
            out += " [%s]" % ", ".join(self.args)
        out += ">"
        return out

    def set_validator(self, validator):
        self.validator = validator
        return self

    def __getitem__(self, type_vals):
        if type(type_vals) is tuple:
            type_vals = list(iter(type_vals))
        elif type(type_vals) is not list:
            type_vals = [type_vals]
        param_values = dict(zip(self.args, type_vals))
        return self.apply(**param_values)

    def apply(self, **param_values):
        return TypeApp(self, **param_values)

class TypeVar(Type):
    """ A type variable.  """
    def __init__(self, name, args = None):
        Type.__init__(self, name, args)

class TypeApp(Type):
    """ Type applications allow generics to be concretized. """
    def __init__(self, target_type, **param_values):
        Type.__init__(self, target_type.name)
        self.param_values = param_values
        self.root_type = target_type
        if isinstance(target_type, TypeApp):
            self.root_type = target_type.root_type
            self.param_values.update(target_type.param_values)
            # now only update *new* values that have not been duplicated
            for k,v in param_values.iteritems():
                if k in target_type.args:
                    self.param_values[k] = v

class NativeType(Type):
    """ A native type whose details are not known but cannot be 
    inspected further - like a leaf type. 

    eg Array<T>, Map<K,V> etc
    """
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
    def __init__(self, name, args = None):
        Type.__init__(self, name, args)
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

class RecordType(ContainerType): pass

class TupleType(ContainerType): pass

class UnionType(ContainerType): pass

class FunctionType(Type):
    input_types = None
    return_type = None

