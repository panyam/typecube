
import os
import ipdb
import json
import core
import utils
import errors

class TypeRegistry(object):
    """
    Keeps track of all types encountered so far in a particular context.
    Types are keyed by the fully qualified name.  The loader of a schema 
    or record file can choose to mark types as UnresolvedTypes so these
    types can be resolved later lazily.
    """
    def __init__(self, parent_registry = None):
        self.parent = parent_registry
        self.type_cache = {}
        self._resolution_handlers = []

        # register default types
        self.register_type("boolean", core.BooleanType)
        self.register_type("byte", core.ByteType)
        self.register_type("int", core.IntType)
        self.register_type("long", core.LongType)
        self.register_type("float", core.FloatType)
        self.register_type("double", core.DoubleType)
        self.register_type("string", core.StringType)

    @property
    def parent_registry(self):
        return self.parent

    def has_type(self, fqn):
        """
        Returns True if a type exists for the given fully qualified name, 
        otherwise returns False
        """
        fqn = (fqn or "").strip()
        return fqn in self.type_cache or (self.parent and self.parent.has_type(fqn))

    def get_type(self, fqn, nothrow = False):
        """
        Gets a type by its fully qualified name.  If it does not exist
        None is returned.
        """
        fqn = (fqn or "").strip()
        out = None
        if fqn in self.type_cache:
            out = self.type_cache[fqn]
        elif self.parent:
            out = self.parent.get_type(fqn, nothrow = True)
        if not out and not nothrow:
            raise errors.TLException("Type '%s' not found" % fqn)
        return out

    def register_type(self, fqn, newtype):
        """
        Register's a new type into the registry.  The type can be Unresolved
        if need be.  If a type already exists and is a resolved type, then 
        a DuplicateTypeException is thrown.  Otherwise if the existing type is unresolved
        then the data from the newtype is copied over.

        Returns
            True if type was successfully registered
            False if a type with the given fqn already exists.
        """

        if fqn is None and newtype:
            newtype.set_resolved(False)
        assert fqn is not None
        if fqn in self.type_cache:
            existing_type = self.type_cache[fqn]
            if existing_type == newtype:
                return existing_type
            # ensure current one is unresolved otherwise throw an error
            elif existing_type.is_resolved:
                raise errors.DuplicateTypeException(fqn)
            elif newtype is not None:
                existing_type.copy_from(newtype)
            else:
                # Do nothing when current type is unresolved and newtype is None
                # we wanted to create an unresolved type at this point anyway
                pass
        else:
            if newtype is not None:
                self.type_cache[fqn] = newtype
            else:
                self.type_cache[fqn] = core.Type(fqn)
                self.type_cache[fqn].set_resolved(False)
        return self.type_cache[fqn]

    @property
    def resolved_types(self):
        """
        Returns the fully qualified names of all types that are currently unresolved.  
        This is only a copy and modifications to this set will go unnoticed.
        """
        return filter(lambda t: t[1].is_resolved, self.type_cache.iteritems())

    @property
    def unresolved_types(self):
        """
        Returns the fully qualified names of all types that are currently unresolved.  
        This is only a copy and modifications to this set will go unnoticed.
        """
        return filter(lambda t: not t[1].is_resolved, self.type_cache.iteritems())

    def resolve_types(self):
        del_indexes = []
        for index,value in enumerate(self._resolution_handlers[:]):
            type_list, handler = value
            # if all types in the list exist and are resolved then call the handler
            if all([t.is_resolved for t in type_list]):
                if type(handler) is function:
                    result = handler(self)
                else:
                    result = handler.handle_resolution(self)
                if result is not False:
                    del_indexes.insert(0, index)
        for index in del_indexes:
            del self._resolution_handlers[index]

    def on_resolution(self, type_list, handler):
        """
        Adds a resolution handler for a given set of types.  This ensures that
        when *all* of the types in the type_list are resolved, the handler is called
        with "self" as the only argument.   If the handler returns False then this
        handler is NOT removed.  If a handler is not removed then in the future the 
        resolution handler of this type list is invoked again.
        """
        self._resolution_handlers.append((type_list, handler))

    def print_types(self, names = None):
        """
        Prints out the given types by ensuring that only types that have not yet been printed out are rendered.
        """
        def sort_func(k1, k2):
            v1 = self.type_cache[k1]
            v2 = self.type_cache[k2]
            if v1.is_resolved == v2.is_resolved:
                return cmp(k1, k2)
            elif v2.is_resolved:
                return 1
            else:
                return -1

        visited = {}
        if not names:
            names = self.type_cache.keys()
        else:
            names = filter(self.has_type, names)

        for key in sorted(names, sort_func):
            value = self.type_cache[key]
            if value.is_resolved:
                print "%s -> " % key, json.dumps(value.to_json(visited = visited), indent = 4, sort_keys = True)
            else:
                print "(Unresolved) %s" % key

        if self._resolution_handlers:
            print 
            print "Resolution Handlers waiting on:"
            print "==============================="
            for type_list, _ in self._resolution_handlers:
                print "(%s)" % (", ".join([x.fqn for x in type_list]))
