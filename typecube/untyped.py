import ipdb
from collections import defaultdict

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
        if not equiv(Var(term1.varname), Var(term2.varname), mapping12, mapping21):
            return False
        return equiv(term1.term, term2.term, mapping12, mapping21)
    else:
        return len(term1.terms) == len(term2.terms) and \
                all(equiv(t1, t2, mapping12, mapping21) for t1,t2 in zip(term1.terms, term2.terms))

def normalize_term(term):
    if issubclass(term.__class__, Term):
        return term
    elif type(term) is str:
        return Var(term)
    ipdb.set_trace()
    assert False

class Term(object):
    """ Top level terms in untyped lambda calculus. """
    def __init__(self):
        self._free_variables = None

    @property
    def free_variables(self):
        if self._free_variables is None:
            self._free_variables = self.eval_free_variables()
        return self._free_variables

    def eval_free_variables(self):
        return set()

    def substitute(self, name, term):
        """ Substitutes a particular variable by a term in this term. Returns the term after the substitution is done."""
        return None

    def reduce_once(self):
        """ Implement this, and return the reduced term which could be this term itself if no reduction was possible. """
        return self, False

    def reduce(self):
        tmp = None
        curr, reduced = self.reduce_once()
        success = reduced
        while reduced:
            tmp = curr
            curr, reduced = curr.reduce_once()
            success = success or reduced
        return curr,success

class Var(Term):
    def __init__(self, name):
        Term.__init__(self)
        self.name = name

    def substitute(self, name, term):
        """ Substitutes a particular variable by a term in this term. """
        if name == self.name:
            return normalize_term(term), True
        return self, True

    def __repr__(self): return "<Var(%x): %s>" % (id(self), str(self))
    def __str__(self):
        return self.name

    def eval_free_variables(self):
        return {self.name}

class Abs(Term):
    def __init__(self, varnames, term):
        Term.__init__(self)
        if type(varnames) is str:
            varnames = [varnames]
        N = len(varnames)
        self.varname = varnames[0]
        out = normalize_term(term)
        for i in range(N - 1, 0, -1):
            out = Abs(varnames[i], out)
        self.term = out

    def __repr__(self): return "<Abs(%x): %s>" % (id(self), str(self))

    def __str__(self):
        names = "\\" + self.varname
        # return "%s : (%s)" % (names, str(self.term))
        if type(self.term) in (Abs, Var):
            return "%s : %s" % (names, str(self.term))
        else:
            return "%s : (%s)" % (names, str(self.term))

    def eval_free_variables(self):
        out = self.term.free_variables
        if self.varname in out:
            out.remove(self.varname)
        return out

    def apply(self, term):
        out,success = self.term.substitute(self.varname, term)
        out = out if success else self
        return out, success

    def reduce_once(self):
        term, reduced = self.term.reduce()
        out = self if not reduced else Abs(self.varname, term)
        return out, reduced

    def substitute(self, varname, term):
        """ Substitutes a particular variable by a term in this term. """
        # First calculate all free variables
        term = normalize_term(term)
        if self.varname == varname:
            # Do an alpha conversion of this expr but what name do we give this?
            return self, True

        this = self
        if self.varname in term.free_variables:
            fvt = term.free_variables
            fve = self.term.free_variables
            # naive way of finding an unbound var!
            newname = ""
            for i in xrange(1000000):
                newname = "%s_%d" % (self.varname, i)
                if newname not in fvt and newname not in fve:
                    break
            assert newname
            subst,success = self.term.substitute(self.varname, newname)
            this = Abs(newname, subst)
        subst, success = this.term.substitute(varname, term)
        out = this if not success else Abs(this.varname, subst)
        return out, success

class App(Term):
    """ Application of a source term to a target term. This does not yet result in an evaluation."""
    def __init__(self, *terms):
        Term.__init__(self)
        self.terms = map(normalize_term, terms)

    def __repr__(self): return "<App(%x): %s>" % (id(self), str(self))
    def __str__(self):
        return " ".join([str(t) if type(t) is Var else "(" + str(t) + ")" for t in self.terms])

    def eval_free_variables(self):
        return reduce(lambda x,y: x.union(y), [t.free_variables for t in self.terms])

    def substitute(self, name, term):
        """ Substitutes a particular variable by a term in this term. """
        substituted = [t.substitute(name, term) for t in self.terms]
        success = any(succeeded for result,succeeded in substituted)
        return App(*(term for term,_ in substituted)), success

    def reduce_once(self):
        curr = 1
        self.terms = [t.reduce()[0] for t in self.terms]
        out = self.terms[0]
        if type(out) is not Abs: return self, False
        while type(out) is Abs and curr < len(self.terms):
            currterm = self.terms[curr]
            result,_ = out.apply(currterm)
            out = result
            curr += 1
        out = out if curr >= len(self.terms) else App(out, *self.terms[curr:])
        return out, True

# Church Booleans
true = Abs("t", Abs("f", "t"))
false = Abs("t", Abs("f", "f"))
test = Abs("l", Abs("m", Abs("n", App("l", "m", "n"))))

f_and = Abs("p", Abs("q", App("p", "q", "p")))
f_or = Abs("p", Abs("q", App("p", "p", "q")))
f_if = Abs("p", Abs("a", Abs("b", App("p", "a", "b"))))

# Church Pairs
pair = Abs("x", Abs("y", Abs("z", App("z", "x", "y"))))
pair_first = Abs("p", App("p", Abs("x", Abs("y", "x"))))
pair_second = Abs("p", App("p", Abs("x", Abs("y", "y"))))

# Church numerals
def church_lit(n):
    base = "x"
    while n > 0:
        base = App("f", base)
        n -= 1
    return Abs(["f", "x"], base)
zero = church_lit(0)

plus = Abs(["m", "n", "f", "x"], App("m", "f", App("n", "f", "x")))
succ = Abs(["n", "f", "x"], App("f", App("n", "f", "x")))
pred = Abs(["n", "f", "x"], App("n", Abs(["g", "h"], App("h", App("g", "f"))), Abs("u", "x"), Abs("u", "u")))
mult = Abs(["m", "n", "f"], App("m", App("n", "f")))
minus = Abs(["m", "n"], App(App("n", pred), "m"))

