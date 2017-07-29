
from ipdb import set_trace
from typecube.core import Fun, TypeArg, Type, Expr, Var, App, TypeApp, FunApp, make_fun_type
from typecube.ext import IntType, StringType, Literal

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
    assert v.beta_reduce({}) == v
    v2 = Var("test2")
    mocker.spy(v2, 'clone')
    x = v.beta_reduce({'test': v2})
    assert v2.clone.call_count == 1
    assert x != v2 and x.name == "test2"
