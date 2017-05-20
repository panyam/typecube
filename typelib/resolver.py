
import ipdb
from collections import deque
import errors as tlerrors

def resolve_type_expression(type_exp, context):
    """ We are given a type expression and it needs to be resolved to a Type.   How can this be done? """

def resolve_type_bindings(root_entity):
    """ Resolves all unresolved types/typerefs starting from the root in a breadth-first manner.

    At this point it assumed that we have a tree of entities (modules, types and functions) that
    are referring to type references which could be resolved types/typerefs, unresolved typerefs
    or actual name bindings - referring to type parameters in a generic.

    The goal of this method is to resolve these unresolved type targets, in the process creating
    reified types from generics if necessary.   This resolver works in a breadth first fashion.
    """
    queue = deque([root_entity])
    while queue:
        next_entity = queue.popleft()
        resolve_entity(next_entity, root_entity)

        # For each entity, we find all its child entities and have them resolved
        for child_entity in next_entity.child_entities:
            queue.append(child_entity)

def resolve_entity(entity, from_entity):
    if type(entity) is Type:
        resolve_type(entity, from_entity)
    elif issubclass(entity.__class__, EntityRef):
        resolve_entityref(entity, from_entity)
    elif type(entity) is Module:
        pass
    elif type(entity) is Function:
        resolve_type(entity.func_type, entity)
    else:
        ipdb.set_trace()
        assert False


def resolve_type(thetype, from_entity):
    """ Resolves a type object from a given entity.  """
    assert type(thetype) is Type
    if thetype.output_typeref:
        resolve_entityref(thetype.output_typeref, from_entity)
    for arg in thetype.args:
        resolve_entityref(arg.typeref, from_entity)

def resolve_entityref(entityref, from_entity):
    """ Resolves an entity reference from a given entity.  """
    assert issubclass(entityref.__class__, EntityRef)
    symref = entityref
    while symref and not symref.is_resolved:
        symref.target = from_entity.find_fqn(symref.fqn)
        # only drill into it we have another entity ref
        if symref.target and not issubclass(symref.target.__class__, EntityRef): break
        symref = symref.target

    final_entity = None if not symref else symref.final_entity
    if symref and not final_entity:
        # Try to resolve it too
        resolve_entityref(symref.last_unresolved, from_entity)
        final_entity = None if not symref else symref.final_entity
        if not final_entity:
            raise tlerrors.TLException("%s could not be resolved" % entityref.fqn)

    if type(final_entity) is Type:
        # for the final entity, resolve the bindings of its args too!
        resolve_type(final_entity, from_entity)

    """
    # Resolve types here - bind them to somewhere along the module chain where they are visible!
    src_typerefs = [arg.typeref for arg in self.typeref.args]
    dest_typeref = self.typeref.output_typeref
    for typeref in src_typerefs + [dest_typeref]:
        # Yep find it up *its* module chain!
        self.resolve_binding(typeref)
    """
    return symref

