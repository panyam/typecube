import ipdb

def signature_for_type(thetype, resolver, visited = None):
    if visited is None: visited = set()
    if thetype.name:
        signature = thetype.name
    else:
        assert thetype.category is not None
        signature = thetype.category
    if thetype.args:
        argsigs = []
        for arg in thetype.args:
            if isinstance(arg.expr, Var):
                argsigs.append(str(arg.expr.field_path))
            elif isinstance(arg.expr, FunApp):
                assert arg.expr.is_type_app
                ipdb.set_trace()
            else:
                argsigs.append(signature_for_typeexpr(arg.expr, resolver, visited))
        signature += "<" + ", ".join(argsigs) + ">"
    return signature

def signature_for_typeexpr(expr, resolver, visited = None, signature_for_type = signature_for_type):
    if visited is None: visited = set()
    exprtype = expr
    import core as tlcore
    if not isinstance(expr, tlcore.Type):
        exprtype = expr.evaltype(resolver)
    return signature_for_type(exprtype, resolver, visited = visited)

def ensure_types(**conditions):
    """ A decorator when applied to a function performs type checking on the arguments passed to it. """
    def category(target_func, *args, **kwargs):
        a = conditions
        ipdb.set_trace()
    return category

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

def normalize_name_and_ns(name, namespace, ensure_namespaces_are_equal = True):
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
                from typecube import errors
                raise errors.TLException("Action already in progress.   Possible circular dependency found")

            self._resolving = True

            result = action()

            self._resolving = False
            self._resolved = True
        return result

