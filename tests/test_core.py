
from ipdb import set_trace
from typecube.core import Expr, Var, Abs, Fun, Type, App, TypeApp, FunApp, make_fun_type

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
    expr = Abs(["x", "y"], App(Var("sum"), [Var("x"), Var("y")]))
    app = App(expr, [Var("a"), Var("b")])
    result, reduced = app.reduce()
    assert result.isa(App)
    assert result.expr.isa(Var)
    assert result.expr.name == "sum"
