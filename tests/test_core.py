
from ipdb import set_trace
from typecube.core import Expr, Var, Abs, Fun, Type, App, TypeApp, FunApp, make_fun_type, equiv, eprint

# Church Booleans
true = Abs(["t", "f"], Var("t"))
false = Abs(["t", "f"], Var("f"))
test = Abs(["l", "m", "n"], App("l", [Var("m"), Var("n")]))

f_and = Abs(["p", "q"], App("p", [Var("q"), Var("p")]))
f_or = Abs(["p", "q"], App("p", [Var("p"), Var("q")]))
f_if = Abs(["p", "a", "b"], App("p", [Var("a"), Var("b")]))

# Church Pairs
pair = Abs(["x", "y", "z"], App("z", [Var("x"), Var("y")]))
pair_first = Abs("p", App("p", Abs(["x", "y"], Var("x"))))
pair_second = Abs("p", App("p", Abs(["x", "y"], Var("y"))))

# Church numerals
def church_lit(n):
    base = "x"
    while n > 0:
        base = App("f", base)
        n -= 1
    return Abs(["f", "x"], base)
zero = church_lit(0)

plus = Abs(["m", "n", "f", "x"], App("m", ["f", App("n", ["f", "x"])]))
succ = Abs(["n", "f", "x"], App("f", App("n", ["f", "x"])))
pred = Abs(["n", "f", "x"],
            App("n",
                [Abs(["g", "h"], App("h", App("g", "f"))),
                 Abs("u", "x"),
                 Abs("u", "u")]))
mult = Abs(["m", "n", "f"], App("m", App("n", "f")))
minus = Abs(["m", "n"], App(App("n", pred), "m"))


def test_expr_init():
    assert Expr().parent is None
    a = object()
    assert Expr(a).parent is a

def test_set_parent(mocker):
    ex = Expr()
    mocker.spy(ex, 'validate_parent')
    mocker.spy(ex, 'parent_changed')
    mocker.spy(ex, 'set_parent')
    ex.parent = object()
    assert ex.set_parent.call_count == 1
    assert ex.validate_parent.call_count == 1
    assert ex.parent_changed.call_count == 1

def test_var(mocker):
    v = Var("test")
    assert v.name == "test"

def test_var_reduce(mocker):
    v = Var("test")
    assert v.substitute({})[0].name == v.name
    v2 = Var("test2")
    mocker.spy(v2, 'clone')
    x,reduced = v.substitute({'test': v2})
    assert v2.clone.call_count == 1
    assert x != v2 and x.name == "test2"

def test_substitution_unbound_var():
    # Test substitution where we are trying to change bound var
    expr = Abs("x", Var("y"))
    result, reduced = expr.substitute({'y': Var('z')})
    assert result.isa(Abs)
    assert result.params == ["x"]
    assert result.expr.isa(Var)
    assert result.expr.name == "z"

def test_substitution_bound_var():
    # Test substitution where we are trying to change bound var
    expr = Abs("x", Var("x"))
    result, reduced = expr.substitute({'x': Var('y')})
    assert result.isa(Abs)
    assert result.params == ["x"]
    assert result.expr.isa(Var)
    assert result.expr.name == "x"

def test_substitution_multi_var(mocker):
    expr = Abs(["x", "y"], App("sum", [Var("x"), Var("y")]))
    app = App(expr, [Var("a"), Var("b")])
    result, reduced = app.reduce()
    assert result.isa(App)
    assert result.expr.isa(Var)
    assert result.expr.name == "sum"

def test_app_simple():
    """ Simple applications.  """
    expr = Abs("x", "y")
    result = expr.apply("z")
    assert result.isa(Var)
    assert result.name == "y"
    expr = Abs("x", "x")
    result = expr.apply("z")
    assert result.isa(Var)
    assert result.name == "z"

def test_app_simple():
    # \x. (x (y z))
    expr = Abs("x", App("x", ["y", "z"]))
    set_trace()
    result = expr.apply("z")

def test_booleans():
    v = Var("v")
    w = Var("w")
    out = App(test, [true, v, w])
    f,success = out.reduce()
    assert f.name == v.name
    out = App(test, [false, v, w])
    f,success = out.reduce()
    assert f.name == w.name

def test_and():
    t = App(f_and, [true, true])
    f,success = t.reduce()
    assert equiv(f, true)

    t = App(f_and, [true, false])
    f,success = t.reduce()
    assert equiv(f, false)

    t = App(f_and, [false, true])
    f,success = t.reduce()
    assert equiv(f, false)

    t = App(f_and, [false, false])
    f,success = t.reduce()
    assert equiv(f, false)

def test_or():
    t = App(f_or, [true, true])
    f,success = t.reduce()
    assert equiv(f, true)

    t = App(f_or, [true, false])
    f,success = t.reduce()
    assert equiv(f, true)

    t = App(f_or, [false, true])
    f,success = t.reduce()
    assert equiv(f, true)

    t = App(f_or, [false, false])
    f,success = t.reduce()
    assert equiv(f, false)

def test_if():
    a = Var("a")
    b = Var("b")
    t = App(f_if, [true, a, b])
    f,success = t.reduce()
    assert f.name == "a"

    t = App(f_if, [false, a, b])
    f,success = t.reduce()
    assert f.name == "b"

def test_pair():
    a = Var("a")
    b = Var("b")
    p = App(pair, [a, b])
    p,success = p.reduce()
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
    set_trace()
    f,success = pone.reduce()
    assert equiv(zero, f)

    two = church_lit(2)
    pone = App(pred, App(pred, one))
    f,success = pone.reduce()
    assert equiv(zero, f)

"""
def test_church_numerals_add():
    five = church_lit(5)
    three = church_lit(3)
    eight = church_lit(8)
    result = App(plus, [five, three])
    f,success = result.reduce()
    assert equiv(eight, f)

def test_church_numerals_minus():
    eight = church_lit(8)
    five = church_lit(5)
    result = App(minus, [eight, five])
    f,success = result.reduce()
    assert equiv(church_lit(3), f)

def test_church_numerals_mult():
    five = church_lit(6)
    three = church_lit(9)
    result = App(mult, [five, three])
    f,success = result.reduce()
    assert equiv(church_lit(54), f)
"""
