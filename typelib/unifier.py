
import ipdb
from core import AnyType
from itertools import izip

def can_substitute(peg_type, hole_type):
    """
    Returns True if peg_type can fit into a hole_type (ie be substituted for when called as an argument to a function).
    This checks the types recursively.
    """
    if not peg_type or not hole_type: ipdb.set_trace()
    if peg_type == hole_type or hole_type == AnyType:
        return True

    if peg_type.constructor != hole_type.constructor:
        return False

    if peg_type.name != hole_type.name:
        return False

    if peg_type.name:  # if a name was provided then check for parents
        if peg_type.parent != hole_type.parent:
            return False

        if peg_type.parent != hole_type.parent:
            return False

    if peg_type.args.count != hole_type.args.count:
        return False

    for arg1,arg2 in izip(peg_type.args, hole_type.args):
        if not can_substitute(arg1.type_expr.resolved_value, arg2.type_expr.resolved_value):
            return False

    return True
