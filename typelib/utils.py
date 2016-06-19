
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
