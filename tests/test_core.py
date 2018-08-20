
from ipdb import set_trace
from typecube.core import *
from typecube import defaults
from typecube import checkers

def test_basic_validation():
    checkers.type_check(defaults.Int, 50)
    checkers.type_check(defaults.String, "hello")
    checkers.type_check(defaults.Float, 50.5)
    try: checkers.type_check(defaults.Int, 50.5)
    except AssertionError as ve: pass
    try: checkers.type_check(defaults.String, 50)
    except AssertionError as ve: pass

def test_record_creation():
    Pair = RecordType(["F", "S"]).add_children(
            Field(TypeVar("F"), "first"),
            Field(TypeVar("S"), "second")).set_label("Pair")
    set_trace()
    checkers.type_check(Pair, {'first': 1, 'second': 2})
