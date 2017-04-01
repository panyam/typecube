
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
        ipdb.set_trace()
        return False

    if type1.is_sum_type != type2.is_sum_type:
        ipdb.set_trace()
        return False

    if type1.fqn != type2.fqn:
        ipdb.set_trace()
        return False

    if type1.argcount != type2.argcount:
        ipdb.set_trace()
        return False

    for arg1,arg2 in izip(type1.args, type2.args):
        if not can_substitute(arg1.typeref.final_type, arg2.typeref.final_type):
            return False

    return True
