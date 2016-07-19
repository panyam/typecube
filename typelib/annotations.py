
class Annotation(object):
    def __init__(self, fqn):
        self.fqn = fqn

    @property
    def name(self):
        return self.fqn

    def __repr__(self):
        return "<Annotation(0x%x), Name: %s" % (id(self), self.fqn)

class SimpleAnnotation(Annotation):
    def __init__(self, fqn):
        super(SimpleAnnotation, self).__init__(fqn)

    def __repr__(self):
        return "<SimpleAnnotation(0x%x), Name: %s" % (id(self), self.fqn)

class PropertyAnnotation(Annotation):
    def __init__(self, fqn, value):
        super(PropertyAnnotation, self).__init__(fqn)
        self.value = value

    def __repr__(self):
        return "<PropertyAnnotation(0x%x), Name: %s, Value: %s" % (id(self), self.fqn, str(self.value))

class CompoundAnnotation(Annotation):
    def __init__(self, fqn, param_specs):
        super(CompoundAnnotation, self).__init__(fqn)
        self.param_specs = param_specs

    def __repr__(self):
        return "<CompoundAnnotation(0x%x), Name: %s, Values: %s" % (id(self), self.fqn, ", ".join(["[%s=%s]" % (x,y) for x,y in self.param_specs]))

    def value_of(self, name):
        for param,value in self.param_specs:
            if param == name:
                return value
        return None
