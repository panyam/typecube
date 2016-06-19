
class Annotation(object):
    def __init__(self, fqn):
        self.fqn = fqn

class SimpleAnnotation(Annotation):
    def __init__(self, fqn):
        super(SimpleAnnotation, self).__init__(fqn)

class PropertyAnnotation(Annotation):
    def __init__(self, fqn, value):
        super(PropertyAnnotation, self).__init__(fqn)
        self.value = value

class CompoundAnnotation(Annotation):
    def __init__(self, fqn, param_specs):
        super(CompoundAnnotation, self).__init__(fqn)
        self.param_specs = param_specs
