import ipdb
from itertools import izip

def equiv(term1, term2, mapping12 = None, mapping21 = None):
    """ Checks if two terms are equivalent. """
    if term1 == term2: return True
    if type(term1) != type(term2): return False
    if mapping12 is None: mapping12 = {}
    if mapping21 is None: mapping21 = {}

    if type(term1) is Var:
        if term1.name in mapping12 and term2.name in mapping21:
            return term2.name == mapping12[term1.name] and mapping21[term2.name] == term1.name
        elif term1.name not in mapping12 and term2.name not in mapping21:
            mapping12[term1.name] = term2.name
            mapping21[term2.name] = term1.name
            return True
        else:
            return False
    elif type(term1) is Abs:
        return equiv(term1.term, term2.term, mapping12, mapping21) and \
                equiv(Var(term1.bound_varname), Var(term2.bound_varname), mapping12, mapping21) 
    else:
        return len(term1.terms) == len(term2.terms) and \
                all(equiv(t1, t2, mapping12, mapping21) for t1,t2 in izip(term1.terms, term2.terms))

def normalize_term(term):
    if issubclass(term.__class__, Term):
        return term
    elif type(term) in (str, unicode):
        return Var(term)
    ipdb.set_trace()
    assert False

class Term(object):
    """ Top level terms in untyped lambda calculus. """
    def __init__(self):
        pass

    def substitute(self, name, term):
        """ Substitutes a particular variable by a term in this term. Returns the term after the substitution is done."""
        return None

    @property
    def free_variables(self):
        return {}

    def reduce_once(self):
        """ Implement this, and return the reduced term which could be this term itself if no reduction was possible. """
        return self

    def reduce(self):
        curr = self
        next = self.reduce_once()
        while curr != next:
            curr = next
            next = next.reduce_once()
        return next


       
class Var(Term):
    def __init__(self, name):
        Term.__init__(self)
        self.name = name

    def substitute(self, name, term):
        """ Substitutes a particular variable by a term in this term. """
        return normalize_term(term) if self.name == name else self

    def __repr__(self): return "Var(%x): %s" % (id(self), str(self))
    def __str__(self):
        return self.name

    @property
    def free_variables(self):
        return {self.name}

class Abs(Term):
    def __init__(self, bound_varname, term):
        Term.__init__(self)
        self.bound_varname = bound_varname
        self.term = normalize_term(term)

    def __repr__(self): return "Abs(%x): %s" % (id(self), str(self))

    def __str__(self):
        if type(self.term) is Abs:
            return "\\%s . (%s)" % (self.bound_varname, str(self.term))
        else:
            return "\\%s . %s" % (self.bound_varname, str(self.term))

    @property
    def free_variables(self):
        out = self.term.free_variables
        if self.bound_varname in out:
            out.remove(self.bound_varname)
        return out

    def apply(self, term):
        return self.term.substitute(self.bound_varname, term)

    def substitute(self, name, term):
        """ Substitutes a particular variable by a term in this term. """
        if self.bound_varname == name:
            return self
        term = normalize_term(term)
        if self.bound_varname in term.free_variables:
            return self
        return Abs(self.bound_varname, self.term.substitute(name, term))

class App(Term):
    """ Application of a source term to a target term. This does not yet result in an evaluation."""
    def __init__(self, *terms):
        Term.__init__(self)
        self.terms = map(normalize_term, terms)

    def __repr__(self): return "App(%x): %s" % (id(self), str(self))
    def __str__(self):
        return "(" + " ".join(map(str, self.terms)) + ")"

    @property
    def free_variables(self):
        return reduce(lambda x,y: x.union(y), [t.free_variables for t in self.terms])

    def substitute(self, name, term):
        """ Substitutes a particular variable by a term in this term. """
        term = normalize_term(term)
        substituted = [t.substitute(name, term) for t in self.terms]
        return App(*substituted)

    def reduce_once(self):
        out = self.terms[0]
        if type(out) is not Abs: return self

        curr = 1
        while type(out) is Abs and curr < len(self.terms):
            out = out.apply(self.terms[curr])
            curr += 1
        return out if curr >= len(self.terms) else App(out, *self.terms[curr:])

true = Abs("t", Abs("f", "t"))
false = Abs("t", Abs("f", "f"))
test = Abs("l", Abs("m", Abs("n", App("l", "m", "n"))))

f_and = Abs("p", Abs("q", App("p", "q", "p")))
f_or = Abs("p", Abs("q", App("p", "p", "q")))
f_if = Abs("p", Abs("a", Abs("b", App("p", "a", "b"))))

pair = Abs("x", Abs("y", Abs("z", App("z", "x", "y"))))
pair_first = Abs("p", App("p", Abs("x", Abs("y", "x"))))
pair_second = Abs("p", App("p", Abs("x", Abs("y", "y"))))
