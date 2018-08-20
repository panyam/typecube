
from typecube.untyped import *

def test_var():
    print("Var(x) = ", str(Var("x")))

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
    print("FV: ", fv)

def test_abstraction():
    print("\\x: x = ", str(Abs("x", "x")))
    print("\\x: \\y: x y = ", str(Abs("x", Abs("y", App("x", "y")))))

def test_reduce():
    v = Var("x")
    assert v,True == v.reduce()

    v = Abs("x", "y")
    assert v, False == v.reduce()

    v = App("x", "y")
    assert v,False == v.reduce()

    v = App(Abs("x", "x"), "x")
    result,success = v.reduce()
    assert success and result.name == "x"

    v = App(Abs("x", "x"), "y")
    result,success = v.reduce()
    assert success and result.name == "y"

    # This should result in an alpha renaming of the innner "f" since the f that is passed as the
    # substitution is actually bound to the "n", but doing so without alpha renaming the f
    # will result in the identity function
    t,_ = Abs(["n", "f"], "n").apply("f")
    # ipdb.set_trace()
    f, success = t.reduce()

    t,_ = church_lit(1).apply(pred)
    # ipdb.set_trace()
    f, success = t.reduce()

def test_equiv():
    assert equiv(Var("x"), Var("y"))
    assert equiv(Abs("x", "x"), Abs("y", "y"))
    assert not equiv(Abs("x", "x"), Abs("y", "z"))
    assert equiv(Abs("x", App("y", "z")), Abs("a", App("b", "c")))
    assert equiv(Abs("x", App("x", "z")), Abs("a", App("a", "b")))
    assert not equiv(Abs("x", App("y", "z")), Abs("a", App("b", "a")))
    assert not equiv(Abs("x", App("y", "z")), Abs("a", App("a", "b")))
    assert equiv(Abs("x", Abs("y", App("x", "y"))), Abs("y", Abs("x", App("y", "x"))))
    assert equiv(Abs("x", Abs("y", App("x", "y"))), Abs("y", Abs("z", App("y", "z"))))

    # This requires us to work around name bindings too!
    # assert equiv(Abs("x", Abs("x", App("x", "z"))), Abs("a", Abs("b", App("b", "c"))))

def test_application():
    print("\\x: x y = ", str(Abs("x", Var("x")).substitute("x", "y")))
    term = App(Abs("x", Abs("y", App("x", "y"))), "z")
    print("(\\x: \\y: x y) z = ", term)
    print("(\\x: \\y: x y) z - Reduced = ", str(term.reduce()))
    term = App(Abs("x", Abs("y", App("x", "y"))), "z", "w")
    print("(\\x: \\y: x y) z w - Reduced Twice = ", str(term.reduce()))

def test_booleans():
    v = Var("v")
    w = Var("w")
    out = App(test, true, v, w)
    f,success = out.reduce()
    assert f == v

def test_and():
    t = App(f_and, true, true)
    f,success = t.reduce()
    assert equiv(f, true)

    t = App(f_and, true, false)
    f,success = t.reduce()
    assert equiv(f, false)

    t = App(f_and, false, true)
    f,success = t.reduce()
    assert equiv(f, false)

    t = App(f_and, false, false)
    f,success = t.reduce()
    assert equiv(f, false)

def test_or():
    t = App(f_or, true, true)
    f,success = t.reduce()
    assert equiv(f, true)

    t = App(f_or, true, false)
    f,success = t.reduce()
    assert equiv(f, true)

    t = App(f_or, false, true)
    f,success = t.reduce()
    assert equiv(f, true)

    t = App(f_or, false, false)
    f,success = t.reduce()
    assert equiv(f, false)

def test_if():
    a = Var("a")
    b = Var("b")
    t = App(f_if, true, a, b)
    f,success = t.reduce()
    assert f.name == "a"

    t = App(f_if, false, a, b)
    f,success = t.reduce()
    assert f.name == "b"

def test_pair():
    a = Var("a")
    b = Var("b")
    p,success = App(pair, a, b).reduce()
    pfirst,success = App(pair_first, p).reduce()
    psecond,success = App(pair_second, p).reduce()
    assert pfirst.name == a.name
    assert psecond.name == b.name

def test_church_numerals_succ():
    one = church_lit(1)
    two = church_lit(2)
    sone = App(succ, zero)
    f,success = sone.reduce()
    assert equiv(one, f)

    stwo = App(succ, App(succ, zero))
    f,success = stwo.reduce()
    assert equiv(two, f)

def test_church_numerals_pred():
    one = church_lit(1)
    pone = App(pred, one)
    f,success = pone.reduce()
    assert equiv(zero, f)

    two = church_lit(2)
    pone = App(pred, App(pred, one))
    f,success = pone.reduce()
    assert equiv(zero, f)

def test_church_numerals_add():
    five = church_lit(5)
    three = church_lit(3)
    eight = church_lit(8)
    result = App(plus, five, three)
    f,success = result.reduce()
    assert equiv(eight, f)

def test_church_numerals_minus():
    eight = church_lit(8)
    five = church_lit(5)
    result = App(minus, eight, five)
    f,success = result.reduce()
    assert equiv(church_lit(3), f)

def test_church_numerals_mult():
    five = church_lit(6)
    three = church_lit(9)
    result = App(mult, five, three)
    f,success = result.reduce()
    assert equiv(church_lit(54), f)
