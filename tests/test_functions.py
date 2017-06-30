
from ipdb import set_trace
from typelib.core import Fun, TypeArg, Type, Expr, Var, App, TypeApp, FunApp, make_fun_type
from typelib.ext import IntType, StringType, Literal
from typelib.resolvers import Resolver, MapResolver, ResolverStack

def funtype(*names_and_types):
    output_name, output_type = names_and_types[-2:]
    output_arg = TypeArg(output_name, output_type) if output_type else None
    names_and_types = names_and_types[:-2]
    type_args = []
    for i in xrange(0, len(names_and_types), 2):
        name = names_and_types[i]
        typeexpr = names_and_types[i + 1]
        type_args.append(TypeArg(name, typeexpr))
    return make_fun_type(None, type_args, output_arg)

def test_fun_creation_null_expr():
    fun = Fun("test", funtype("a", IntType, "b", IntType, "c", StringType), None, None)
    assert not fun.is_type_fun
    assert fun.is_external

def test_app_resolve_function(mocker):
    fun = Fun("test", funtype("a", IntType, "b", IntType, "c", StringType), None, None)
    resolver_stack = ResolverStack(MapResolver({"test":  fun}))
    args = [Literal(3, IntType), Literal(4, IntType)]
    app = App(Var("test"), args)
    value = app.resolve_function(resolver_stack)
    assert value == fun

def test_type_app_external(mocker):
    expr = None
    fun = Fun("test", funtype("a", Type, "b", Type, "c", Type), expr, None)
    mocker.spy(fun, 'apply')
    resolver_stack = ResolverStack(MapResolver({"test":  fun}))
    args = [IntType, IntType]
    app = TypeApp(Var("test"), args)
    value = app.resolve(resolver_stack)
    assert app.resolve_function(resolver_stack) == fun
    assert value == app
    assert fun.apply.call_count == 1

def test_fun_apply_external_func_returns_none(mocker):
    expr = None
    fun = Fun("test", funtype("a", IntType, "b", IntType, "c", IntType), expr, None)
    resolver_stack = ResolverStack(MapResolver({"test":  fun}))
    args = [Literal(3, IntType), Literal(4, IntType)]
    app = FunApp(Var("test"), args)
    value = app.resolve(resolver_stack)
    assert value.func_expr == fun

def test_type_app(mocker):
    """ Test application of a type function to a bunch of type arguments. """
    expr = Type("record", "Pair", [TypeArg("first", Var("a")), TypeArg("second", Var("b"))], TypeArg("dest", Var("c")), None)
    fun = Fun("test", funtype("a", Type, "b", Type, "c", Type, None, Type), expr, None)
    mocker.spy(fun, 'apply')
    resolver_stack = ResolverStack(MapResolver({"test":  fun}))
    args = [IntType, IntType, StringType]
    app = TypeApp(Var("test"), args)
    value = app.resolve(resolver_stack)
    assert fun.apply.call_count == 1
    assert value.name == "Pair"
    assert value.constructor == "record"
    assert value.args[0].name == "first"
    assert value.args[0].type_expr == args[0]
    assert value.args[1].name == "second"
    assert value.args[1].type_expr == args[1]
    assert value.output_arg.name == "dest"
    assert value.output_arg.type_expr == args[2]
