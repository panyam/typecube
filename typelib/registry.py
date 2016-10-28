
import os
import fnmatch
import ipdb
import json
import core
import utils
import errors

class TypeRegistry(object):
    """
    Keeps track of all type references encountered so far in a particular context.
    Types are keyed by the fully qualified name.
    """
    def __init__(self):
        self.type_refs = {}

        # register references to default types.
        self.register_type("boolean", core.BooleanType)
        self.register_type("byte", core.ByteType)
        self.register_type("int", core.IntType)
        self.register_type("long", core.LongType)
        self.register_type("float", core.FloatType)
        self.register_type("double", core.DoubleType)
        self.register_type("string", core.StringType)

    def typerefs_for_wildcards(self, wildcards, skip_unresolved = True):
        """
        Return all type refs that match any of the given wild cards.
        If the skip_unresolved parameter is True then only resolved 
        type references are returned.
        """
        source_types = set()
        for tw in wildcards:
            # First go through all resolved types
            for fqn,t in self.type_refs.iteritems():
                if fnmatch.fnmatch(fqn, tw):
                    if t.is_resolved or not skip_unresolved:
                        source_types.add(fqn)
        return source_types

    def has_typeref(self, fqn):
        """
        Returns True if a type exists for the given fully qualified name, 
        otherwise returns False.   Even if a type reference exists but it
        is not resolved, this method would still return True.
        """
        fqn = (fqn or "").strip()
        return fqn in self.type_refs

    def get_typeref(self, fqn, nothrow = False):
        """
        Gets a type reference by its fully qualified name.  If it does not exist
        None is returned.
        """
        fqn = (fqn or "").strip()
        if fqn in self.type_refs:
            return self.type_refs[fqn]
        if nothrow:
            return None
        ipdb.set_trace()
        raise errors.TLException("Reference to type '%s' not found" % fqn)

    def register_type(self, fqn, newtype_or_ref, overwrite = False):
        """
        Register's a new type for a given FQN and returns a reference to the type.
        If the type itself is unresolved or needs to be changed it can be done so
        via the type reference.

        Returns
            A reference to the type pointed by the FQN.
        """
        is_type = type(newtype_or_ref) is core.Type
        is_typeref = isinstance(newtype_or_ref, core.TypeRef)
        if newtype_or_ref and (not is_type) and (not is_typeref):
            ipdb.set_trace()
            assert False, "Newtype must be a Type or a TypeRef instance"

        if fqn is None and newtype_or_ref and is_type:
            newtype_or_ref.set_resolved(False)

        assert fqn is not None
        if fqn not in self.type_refs:
            newtyperef = newtype_or_ref
            if is_type or newtype_or_ref is None:
                newtyperef = core.TypeRef(newtype_or_ref, fqn)
            self.type_refs[fqn] = newtyperef
            return newtyperef

        # Already exists - so check if it is the same
        existing_typeref = self.type_refs[fqn]
        if existing_typeref.target == newtype_or_ref or existing_typeref == newtype_or_ref:
            return existing_typeref

        # Nope - new instance
        # ensure current one is unresolved otherwise throw an error
        if existing_typeref.is_resolved:
            # If it is pointing to a valid type then we may have a problem!
            if not overwrite:
                raise errors.DuplicateTypeException(fqn)
            else:
                print "Overwriting existing type: %s" % fqn
                if newtype_or_ref:
                    ipdb.set_trace()
                existing_typeref.target = newtype_or_ref
        elif newtype_or_ref is not None:
            existing_typeref.target = newtype_or_ref
        else:
            # Do nothing when current type is unresolved and newtype is None
            # we wanted to create an unresolved type at this point anyway
            pass
        return existing_typeref

    @property
    def resolved_typerefs(self):
        """
        Returns the fully qualified names of all types that are currently unresolved.  
        This is only a copy and modifications to this set will go unnoticed.
        """
        return filter(lambda t: t[1].is_resolved, self.type_refs.iteritems())

    @property
    def unresolved_typerefs(self):
        """
        Returns the fully qualified names of all types that are currently unresolved.  
        This is only a copy and modifications to this set will go unnoticed.
        """
        return filter(lambda t: not t[1].is_resolved, self.type_refs.iteritems())

    def typeref_fqn_will_set(self, typeref):
        """
        Called when the name of a typeref will change.
        Returns False if and only if change is not allowed.
        """
        # check that the FQN at this spot isnt taken
        if self.has_typeref(typeref.fqn):
            raise TLException("A type reference with name '%s' already exists" % newvalue)
        else:
            self.type_refs[self.fqn] = typeref
