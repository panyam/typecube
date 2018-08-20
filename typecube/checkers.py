
# Type checkers for data given types
from typecube import core

def type_check(thetype, data, bindings = None):
    """ Checks that a given bit of data conforms to the type provided  """
    if isinstance(thetype, core.RecordType):
        for child in thetype.children:
            value = data[child.name]
            type_check(child.field_type, value)
    elif isinstance(thetype, core.TupleType):
        assert isinstance(data, tuple)
        assert len(tuple) == len(thetype.children)
        for value,childtype in zip(data, thetype.children):
            type_check(childtype, value)
    elif isinstance(thetype, core.UnionType):
        assert isinstance(thetype, dict)
        fields = [child for child in thetype.children if child.name in data]
        assert len(fields) == 1, "0 or more than 1 entry in Union"
        type_check(fields[0].field_type, data[fields[0].name])
    elif isinstance(thetype, core.TypeApp):
        # Type applications are tricky.  These will "affect" bindings
        assert False
    elif isinstance(thetype, core.TypeVar):
        # Find the binding for this type variable
        assert False

    # Finally apply any other validators that were nominated 
    # specifically for that particular type
    if thetype.validator:
        thetype.validator(data)
