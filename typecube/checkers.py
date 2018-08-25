
# Type checkers for data given types
from typecube import core

class Bindings(object):
    class Entry(object):
        def __init__(self, value, level, prev = None):
            self.value = value
            self.level = level
            self.prev = prev

        def __repr__(self):
            if self.prev:
                return "%s[%d] (%s)" % (repr(self.value), self.level, repr(self.prev))
            else:
                return "%s[%d]" % (repr(self.value), self.level)

    def __init__(self):
        self.level = 0
        self.entries = {}

    def __setitem__(self, key, value):
        entry = self.entries.get(key, None)
        if entry is not None:
            assert entry.level < self.level, "Value for '%s' already exists in this level (%d)" % (key, self.level)
        self.entries[key] = Bindings.Entry(value, self.level, entry)

    def __getitem__(self, key):
        while key in self.entries and self.entries[key].level > self.level:
            self.entries[key] = self.entries[key].prev
        if key not in self.entries: return None
        return self.entries[key].value

    def push(self):
        self.level += 1

    def pop(self):
        self.level += 1

def type_check(thetype, data, bindings = None):
    """ Checks that a given bit of data conforms to the type provided  """
    if not bindings: bindings = Bindings()
    if isinstance(thetype, core.RecordType):
        for name,child in zip(thetype.child_names, thetype.child_types):
            value = data[name]
            type_check(child, value, bindings)
    elif isinstance(thetype, core.TupleType):
        assert isinstance(data, tuple)
        assert len(data) == len(thetype.child_types)
        for value,child_type in zip(data, thetype.child_types):
            type_check(child_type, value, bindings)
    elif isinstance(thetype, core.UnionType):
        assert isinstance(thetype, dict)
        children = [(name,child) for name,child in zip(thetype.child_names, thetype.child_types) if name in data]
        assert len(fields) == 1, "0 or more than 1 entry in Union"
        child_name,child_type = children[0]
        type_check(child_type, data[child_name], bindings)
    elif isinstance(thetype, core.TypeApp):
        # Type applications are tricky.  These will "affect" bindings
        bindings.push()
        for k,v in thetype.param_values.items():
            bindings[k] = v
        type_check(thetype.root_type, data, bindings)
        bindings.pop()
    elif isinstance(thetype, core.TypeVar):
        # Find the binding for this type variable
        type_check(bindings[thetype.name], data, bindings)

    # Finally apply any other validators that were nominated 
    # specifically for that particular type
    if thetype.validator:
        thetype.validator(thetype, data)
