import ipdb

def signature_for_type(thetype, resolver, visited = None):
    if visited is None: visited = set()
    if thetype.name:
        signature = thetype.name
    else:
        assert thetype.constructor is not None
        signature = thetype.constructor
    if thetype.args:
        argsigs = []
        for arg in thetype.args:
            if isinstance(arg.type_expr, Variable):
                argsigs.append(str(arg.type_expr.field_path))
            elif isinstance(arg.type_expr, FunApp):
                assert arg.type_expr.is_type_app
                ipdb.set_trace()
            else:
                argsigs.append(signature_for_typeexpr(arg.type_expr, resolver, visited))
        signature += "<" + ", ".join(argsigs) + ">"
    return signature

def signature_for_typeexpr(type_expr, resolver, visited = None, signature_for_type = signature_for_type):
    if visited is None: visited = set()
    exprtype = type_expr
    import core as tlcore
    if not isinstance(type_expr, tlcore.Type):
        exprtype = type_expr.evaltype(resolver)
    return signature_for_type(exprtype, resolver, visited = visited)

def ensure_types(**conditions):
    """ A decorator when applied to a function performs type checking on the arguments passed to it. """
    def constructor(target_func, *args, **kwargs):
        a = conditions
        ipdb.set_trace()
    return constructor

class FQN(object):
    def __init__(self, name, namespace, ensure_namespaces_are_equal = True):
        name,namespace = (name or "").strip(), (namespace or "").strip()
        comps = name.split(".")
        if len(comps) > 1:
            n2 = comps[-1]
            ns2 = ".".join(comps[:-1])
            if ensure_namespaces_are_equal:
                if namespace and ns2 != namespace:
                    assert ns2 == namespace or not namespace, "Namespaces dont match '%s' vs '%s'" % (ns2, namespace)
            name,namespace = n2,ns2
        fqn = None
        if namespace and name:
            fqn = namespace + "." + name
        elif name:
            fqn = name
        self._name = name
        self._namespace = namespace
        self._fqn = fqn

    @property
    def parts(self):
        return self._name, self._namespace, self._fqn

    @property
    def name(self):
        return self._name

    @property
    def namespace(self):
        return self._namespace

    @property
    def fqn(self):
        return self._fqn

def field_or_fqn(input):
    output = input
    if type(input) not in (str, unicode):
        output = input.fqn
    return output

def normalize_name_and_ns2(name, namespace, ensure_namespaces_are_equal = True):
    name,namespace = (name or "").strip(), (namespace or "").strip()
    comps = name.split(".")
    if len(comps) > 1:
        n2 = comps[-1]
        ns2 = ".".join(comps[:-1])
        if ensure_namespaces_are_equal:
            if namespace and ns2 != namespace:
                assert ns2 == namespace or not namespace, "Namespaces dont match '%s' vs '%s'" % (ns2, namespace)
        name,namespace = n2,ns2
    fqn = None
    if namespace and name:
        fqn = namespace + "." + name
    elif name:
        fqn = name
    return name,namespace,fqn

def evaluate_fqn(namespace, name):
    fqn = name 
    if namespace:
        fqn = namespace + "." + name 
    return fqn

class ResolutionStatus(object):
    def __init__(self):
        self._resolved = False
        self._resolving = False

    @property
    def succeeded(self):
        return self._resolved

    @property
    def in_progress(self):
        return self._resolving

    def _mark_in_progress(self, value):
        self._resolving = value

    def _mark_resolved(self, value):
        self._resolved = value

    def perform_once(self, action):
        result = None
        if not self._resolved:
            if self._resolving:
                from typelib import errors
                raise errors.TLException("Action already in progress.   Possible circular dependency found")

            self._resolving = True

            result = action()

            self._resolving = False
            self._resolved = True
        return result


class FieldPath(object):
    def __init__(self, parts, selected_children = None):
        """
        Arguments:
        parts               --  The list of components denoting the field path.   If the first value is an empty 
                                string, then the field path indicates an absolute path.
        selected_children   --  The list of child fields that are selected in a single sweep.  If this field is 
                                specified then is_optional, default_value, target_name, and target_type are ignored 
                                and MUST NOT be specified.  If this value is the string "*" then ALL children all
                                selected.  When this is specified, the source field MUST be of a record type.
        """
        self.inverted = False
        parts = parts or []
        if type(parts) in (str, unicode):
            parts = parts.strip()
            parts = parts.split("/")
        # if len(parts) == 0: ipdb.set_trace()
        self._parts = parts
        self.selected_children = selected_children or None

    def __repr__(self): 
        return str(self)

    def __str__(self):
        if self.all_fields_selected:
            return "%s/*" % "/".join(self._parts)
        elif self.has_children:
            return "%s/(%s)" % ("/".join(self._parts), ", ".join(self.selected_children))
        else:
            return "/".join(self._parts)

    def with_child(self, field_name):
        """
        Creates a new field path, with the given name added to the end.  If this field path
        has children then the children are replaced with this field name otherwise
        a new level is added at the end.
        """
        return FieldPath(self._parts + [field_name])

    @property
    def length(self):
        if self.is_absolute:
            return len(self._parts) - 1
        else:
            return len(self._parts)

    @property
    def last(self):
        """
        Gets the last component of a field path.
        """
        return self._parts[-1]

    @property
    def _children_copy(self):
        if type(self.selected_children) is (str, unicode) or not self.selected_children:
            return self.selected_children
        else:
            return self.selected_children[:]

    def copy(self):
        return FieldPath(self._parts[:], self._children_copy)

    def pop(self):
        return self._parts[0], FieldPath(self._parts[1:], self._children_copy)

    def push(self, part):
        return FieldPath([part] + self._parts[:], self._children_copy)

    def get(self, index):
        """
        Gets the field path part at a given index taking into account whether the path is absolute or not.
        """
        if self.is_absolute:
            index += 1
        return self._parts[index]

    @property
    def is_blank(self):
        return len(self._parts) == 0

    @property
    def is_absolute(self):
        if len(self._parts) == 0:
            return False
        return self._parts[0] == ""

    @property
    def has_children(self):
        return self.selected_children is not None

    @property
    def all_fields_selected(self):
        return self.selected_children == "*"

    def get_selected_fields(self, starting_record):
        """
        Given a source field, return all child fields as per the selected_fields spec.
        """
        if self.all_fields_selected:
            return [arg.name for arg in starting_record.args]
        else:
            return [arg.name for arg in starting_record.args if arg.name in self.selected_children]
