
import os
import ipdb
import json
import datatypes, fields
import utils
import errors

class TypeRegistry(object):
    """
    Keeps track of all types encountered so far in a particular context.
    Types are keyed by the fully qualified name.  The loader of a schema 
    or record file can choose to mark types as UnresolvedTypes so these
    types can be resolved later lazily.
    """
    def __init__(self):
        self.type_cache = {}
        self._resolution_handlers = []
        self._unresolved_types = set()

        # register default types
        self.register_type(datatypes.IntType)
        self.register_type(datatypes.LongType)
        self.register_type(datatypes.FloatType)
        self.register_type(datatypes.DoubleType)
        self.register_type(datatypes.BooleanType)
        self.register_type(datatypes.StringType)

    def has_type(self, fqn):
        """
        Returns True if a type exists for the given fully qualified name, 
        otherwise returns False
        """
        fqn = (fqn or "").strip()
        return fqn in self.type_cache

    def get_type(self, fqn, nothrow = False):
        """
        Gets a type by its fully qualified name.  If it does not exist
        None is returned.
        """
        fqn = (fqn or "").strip()
        if nothrow:
            return self.type_cache.get(fqn, None)
        else:
            return self.type_cache[fqn]

    def register_type(self, newtype):
        """
        Register's a new type into the registry.  The type can be Unresolved
        if need be.  If a type already exists and is a resolved type, then 
        a DuplicateTypeException is thrown.  Otherwise if the existing type is unresolved
        then the data from the newtype is copied over.

        Returns
            True if type was successfully registered
            False if a type with the given fqn already exists.
        """
        if newtype.fqn in self.type_cache:
            # ensure current one is unresolved otherwise throw an error
            if self.type_cache[newtype.fqn].is_resolved:
                raise errors.DuplicateTypeException(newtype.fqn)
            else:
                self.type_cache[newtype.fqn].copy_from(newtype)
        else:
            self.type_cache[newtype.fqn] = newtype
        return self.type_cache[newtype.fqn]

    def resolve_type(self, atype):
        """
        Resolves a type if it is currently unresolved by replacing it with the new type's
        details

        For this to succeed:
            * The type currently registered by atype.fqn must be unresolved.
            * If atype is of an unresolved type then the resolution is ignored

        Returns:
            True, if resolution succeeded otherwise False.
        """
        if not atype.is_resolved_type or atype.fqn not in self._unresolved_types:
            return False

        # TBD
        None.a = 3

    def merge_from(self, another):
        """
        Merges the contents of another type registry into this one.

        If the same type exists in both registries, then following rules are applied
        (assuming T1 in self and T2 in another having the same fqn):
        * If T2 is unresolved, T2 is dropped.
        * otherwise:
        *   If T1 is unresolved and T2 is resolved, T1 is replaced by T2.
        *   If T1 is resolved and has same type as T2 then all is fine and T2 is dropped (due to equavalency).
        *   Otherwise a TypeConflict exception is thrown.
        """
        # TBD
        None.a = 3

    @property
    def resolved_type_names(self):
        """
        Return a list of all resolved types.
        """
        return [k for (k,v) in self.type_cache.iteritems() if v.is_resolved]

    @property
    def unresolved_type_names(self):
        """
        Return a list of all resolved types.
        """
        return [k for (k,v) in self.type_cache.iteritems() if v.is_unresolved]

    @property
    def unresolved_types(self):
        """
        Returns the fully qualified names of all types that are currently unresolved.  
        This is only a copy and modifications to this set will go unnoticed.
        """
        return self._unresolved_types[:]

    def on_resolution(self, type_list, handler):
        """
        Adds a resolution handler for a given set of types.  This ensures that
        when *all* of the types in the type_list are resolved, the handler is called
        with "self" as the only argument.   If the handler returns False then this
        handler is NOT removed.  If a handler is not removed then in the future the 
        resolution handler of this type list is invoked again.
        """
        self._resolution_handlers.append((type_list, handler))

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
