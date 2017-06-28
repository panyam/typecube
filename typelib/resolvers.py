import ipdb
from typelib import errors

class Resolver(object):
    def resolve_name(self, name, condition = None): return None

class MapResolver(Resolver):
    def __init__(self, bindings):
        self.bindings = bindings

    def resolve_name(self, name, condition = None):
        out = self.bindings.get(name, None)
        if condition is None or condition(out):
            return out
        return None

class ResolverStack(Resolver):
    def __init__(self, resolver, parent):
        self.resolver = resolver
        self.parent = parent

    def resolve_name(self, name, condition = None):
        out = self.resolver.resolve_name(name)
        if out is not None and (condition is None or condition(out)):
            return out
        elif self.parent:
            return self.parent.resolve_name(name)
        else:
            raise errors.TLException("Unable to resolve name: %s" % name)

    def push(self, resolver):
        return ResolverStack(resolver, self)
