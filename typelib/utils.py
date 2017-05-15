import ipdb

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
                from onering import errors
                raise errors.OneringException("Action already in progress.   Possible circular dependency found")

            self._resolving = True

            result = action()

            self._resolving = False
            self._resolved = True
        return result
