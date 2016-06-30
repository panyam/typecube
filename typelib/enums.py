
import core

def EnumType(enum_data = None):
    enum_data = enum_data or EnumData()
    return core.Type("enum", enum_data)

class EnumData(object):
    class Symbol(object):
        def __init__(self, name, annotations = [], doc = ""):
            self.name = name
            self.annotations = annotations
            self.doc = doc
 
        def to_json(self):
            return self.name
 
    def __init__(self, *symbols):
        self.symbols = list(*symbols)
        self.source_types = []
        self.annotations = []
 
    def signature(self, thetype):
        return "Enum<%s>" % thetype.fqn
    
    def add_symbol(self, name, annotations = [], doc = ""):
        self.symbols.append(EnumData.Symbol(name, annotations, doc))
 
    def __str__(self):
        return "[%s: %s]" % (self.name, ",".join(self.symbols))
 
    def to_json(self, thetype, visited = None):
        out = {
            "type": "enum",
            "doc": thetype.documentation, 
            "symbols": [s.to_json() if type(s) not in (str,unicode) else s for s in self.symbols]
        }
 
        if thetype.name:
            out["name"] = thetype.fqn
        return out
