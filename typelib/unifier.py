
import ipdb
from core import AnyType
from itertools import izip

def can_substitute(type1, type2):
    """
    Returns True if type2 can be substituted for type1 when passed as a function.
    This checks the types recursively.
    """
    if type1 == type2 or type1 == AnyType:
        return True

    if type1.constructor != type2.constructor:
        return False

    if type1.is_sum_type != type2.is_sum_type:
        return False

    if type1.name != type2.name:
        return False

    if type1.name:  # if a name was provided then check for parents
        if type1.parent != type2.parent:
            return False

        if type1.parent.fqn != type2.parent.fqn:
            return False

    if type1.argcount != type2.argcount:
        return False

    for arg1,arg2 in izip(type1.args, type2.args):
        if not can_substitute(arg1.typeref.final_entity, arg2.typeref.final_entity):
            return False

    return True
