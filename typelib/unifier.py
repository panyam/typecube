
import ipdb
import core
from itertools import izip

def can_substitute(peg_typeexpr, hole_typeexpr):
    """
    Returns True if peg_type can fit into a hole_type (ie be substituted for when called as an argument to a function).
    This checks the types recursively.
    """
    if not peg_typeexpr or not hole_typeexpr: ipdb.set_trace()
    ipdb.set_trace()
    resolved_peg = peg_typeexpr.resolved_value
    resolved_hole = hole_typeexpr.resolved_value

    if resolved_peg == resolved_hole or resolved_hole == core.AnyType: return True

    # if type(resolved_peg) != type(resolved_hole): return False

    if type(resolved_peg) is core.Fun or type(resolved_hole) is core.Fun:
        ipdb.set_trace()

    if resolved_peg.constructor != resolved_hole.constructor:
        return False

    if resolved_peg.name != resolved_hole.name:
        return False

    if resolved_peg.name:  # if a name was provided then check for parents
        if resolved_peg.parent != resolved_hole.parent:
            return False

    if resolved_peg.args.count != resolved_hole.args.count:
        return False

    for arg1,arg2 in izip(resolved_peg.args, resolved_hole.args):
        if not can_substitute(arg1.type_expr.resolved_value, arg2.type_expr.resolved_value):
            return False

    return True
