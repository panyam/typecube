import ipdb
from typelib import errors

class Resolver(object):
    def resolve_name(self, name, condition = None): return None

    def debug_show(self, level = 0):
        assert False, "Not Implemented"

class MapResolver(Resolver):
    def __init__(self, bindings):
        self.bindings = bindings

    def resolve_name(self, name, condition = None):
        out = self.bindings.get(name, None)
        if condition is None or condition(out):
            return out
        return None

    def debug_show(self, level = 0):
        print ("  " * level) + "MapResolver"
        for key,value in self.bindings.iteritems():
            print ("  " * (level + 1)) + ("%s: %s" % (key,value))

class ResolverStack(Resolver):
    def __init__(self, resolver, parent = None):
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

    def debug_show(self, level = 0):
        curr = self
        while curr:
            print ("  " * level) + "=" * 50
            print ("  " * level) + "StackResolver: %s" % repr(curr.resolver)
            curr.resolver.debug_show(level + 1)
            curr = curr.parent
