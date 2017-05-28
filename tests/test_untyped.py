
from typelib.untyped import *

def test_var():
    print "Var(x) = ", str(Var("x"))

def test_freevariables():
    assert len(Var("x").free_variables) == 1

    fv = Abs("x", "y").free_variables
    assert len(fv) == 1 and "y" in fv

    fv = Abs("x", "x").free_variables
    assert len(fv) == 0

    fv = App("x", "x").free_variables
    assert len(fv) == 1

    fv = App("x", "y").free_variables
    assert len(fv) == 2

    fv = Abs("x", App("x", "y")).free_variables
    assert len(fv) == 1

    fv = Abs("x", Abs("y", Abs("f", App("f", "x")))).substitute("x", "z")

    fv = Abs("x", Abs("f", Abs("x", App("f", "x")))).substitute("x", "z")
    print "FV: ", fv

def test_abstraction():
    print "\\x: x = ", str(Abs("x", "x"))
    print "\\x: \\y: x y = ", str(Abs("x", Abs("y", App("x", "y"))))

def test_reduce():
    v = Var("x")
    assert v == v.reduce()

    v = Abs("x", "y")
    assert v == v.reduce()

    v = App("x", "y")
    assert v == v.reduce()

    v = App(Abs("x", "x"), "x")
    assert v.reduce().name == "x"

def test_application():
    print "\\x: x y = ", str(Abs("x", Var("x")).substitute("x", "y"))
    term = App(Abs("x", Abs("y", App("x", "y"))), "z")
    print "(\\x: \\y: x y) z = ", term
    print "(\\x: \\y: x y) z - Reduced = ", str(term.reduce())
    term = App(Abs("x", Abs("y", App("x", "y"))), "z", "w")
    print "(\\x: \\y: x y) z w - Reduced Twice = ", str(term.reduce())

def test_booleans():
    v = Var("v")
    w = Var("w")
    out = App(test, true, v, w)
    f = out.reduce()
    assert f == v

def test_and():
    f = App(f_and, true, true).reduce()
    assert equiv(f, true)

    f = App(f_and, true, false).reduce()
    assert equiv(f, false)

    f = App(f_and, false, true).reduce()
    assert equiv(f, false)

    f = App(f_and, false, false).reduce()
    assert equiv(f, false)

def test_or():
    f = App(f_or, true, true).reduce()
    assert equiv(f, true)

    f = App(f_or, true, false).reduce()
    assert equiv(f, true)

    f = App(f_or, false, true).reduce()
    assert equiv(f, true)

    f = App(f_or, false, false).reduce()
    assert equiv(f, false)

def test_if():
    a = Var("a")
    b = Var("b")
    f = App(f_if, true, a, b).reduce()
    assert f.name == "a"

    f = App(f_if, false, a, b).reduce()
    assert f.name == "b"

def test_pair():
    a = Var("a")
    b = Var("b")
    p = App(pair, a, b).reduce()
    assert App(pair_first, p).reduce().name == a.name
    assert App(pair_second, p).reduce().name == b.name
