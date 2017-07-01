
from enum import Enum

class TypeCategory(Enum):
    # Named basic types
    LEAF_TYPE           = 0

    # t1 x t2 x ... x tN
    PRODUCT_TYPE        = 1

    # t1 + t2 + ... + tN
    SUM_TYPE            = 2

    # t1 -> t2 -> ... -> tN
    FUNCTION_TYPE       = 3

    # forall(t1,t2,...,tN) -> tN(t1...tN-1)
    UNIVERSAL_TYPE      = 4

    # exists(t1,t2,...,tN) -> tN(t1...tN-1)
    EXISTENTIAL_TYPE    = 5

    # \(t1,t2,...,tN) -> tN(t1...tN-1)
    ABSTRACTION         = 6

    # t1(t2...tN)
    APPLICATION         = 7

class Type(Expr, Annotatable):

    KIND = Type(TypeCategory.PRODUCT_TYPE, "*", "*", [], None)

    def __init__(self, category, constructor, name, type_args, parent, annotations = None, docs = ""):
        """
        Creates a new type function.  Type functions are responsible for creating concrete type instances
        or other (curried) type functions.

        Params:
            category        Defines the category of this type, FUNCTION, SUM, etc
            constructor     The type's constructor, eg "record", "literal" etc.  This is not the name 
                            of the type itself but a name that indicates a class of this type.
            name            Name of the type.
            type_args       Type arguments are fields/children of a given type are themselves exprs 
                            (whose final type must be of Type).
            parent          A reference to the parent container entity of this type.
            annotations     Annotations applied to the type.
            docs            Documentation string for the type.
        """
        Annotatable.__init__(self, annotations = annotations, docs = docs)
        Expr.__init__(self)

        if type(category) is not TypeCategory:
            raise errors.TLException("category must be a TypeCategory enum instance")
        if type(constructor) not in (str, unicode):
            raise errors.TLException("constructor must be a string")

        self.category = category
        self.constructor = constructor
        self.parent = parent
        self.name = name
        self.args = TypeArgList(type_args)
        self._default_resolver_stack = None

    def _equals(self, another):
        return self.name == another.name and \
               self.constructor == another.constructor and \
               self.category == another.category and \
               self.parent == another.parent and \
               self.args.equals(another.args)

    @property
    def default_resolver_stack(self):
        if self._default_resolver_stack is None:
            self._default_resolver_stack = ResolverStack(self.parent, None)
        return self._default_resolver_stack

    @property
    def fqn(self):
        out = self.name
        if self.parent and self.parent.fqn:
            out = self.parent.fqn + "." + out
        return out or ""

    def _evaltype(self, resolver_stack):
        """ Type of a "Type" is a KindType!!! """
        return KIND

    def _resolve(self, resolver_stack):
        # A Type resolves to itself
        new_type_args = [arg.resolve(resolver_stack) for arg in self.args]
        if any(x != y for x,y in zip(new_type_args, self.args)):
            return Type(self.category, self.constructor, self.name, new_type_args, self.parent, self.annotations, self.docs)
        return self

    def __json__(self, **kwargs):
        out = {}
        if self.name:
            out["name"] = self.name
        if kwargs.get("include_docs", False) and self.docs:
            out["docs"] = self.docs
        if not kwargs.get("no_cons", False):
            out["type"] = self.constructor
        if self.args:
            out["args"] = [arg.json(**kwargs) for arg in self.args]
        return out

class TypeArg(Expr, Annotatable):
    """ A type argument is a child of a given type.  Akin to a member/field of a type.  """
    def __init__(self, name, type_expr, is_optional = False, default_value = None, annotations = None, docs = ""):
        Expr.__init__(self)
        Annotatable.__init__(self, annotations, docs)
        self.name = name
        self.type_expr = type_expr
        self.is_optional = is_optional
        self.default_value = default_value or None

    @classmethod
    def validate(cls, arg):
        if isinstance(arg, TypeArg):
            return arg
        elif issubclass(arg.__class__, Expr):
            return TypeArg(None, arg)
        elif type(arg) in (str, unicode):
            return TypeArg(None, Var(arg))
        else:
            raise errors.TLException("Argument must be a TypeArg, Expr or a string. Found: '%s'" % type(arg))

    def _equals(self, another):
        return self.name == another.name and \
                self.is_optional == another.is_optional and \
                (self.default_value == another.default_value or self.default_value.equals(another.default_value)) and \
                self.type_expr.equals(another.type_expr)

    def __json__(self, **kwargs):
        out = {}
        if self.name:
            out["name"] = self.name
        return out

    def _evaltype(self, resolver_stack):
        """ Type of a "Type" is a KindType!!! """
        resolved = self.resolve(resolver_stack)
        return resolved.type_expr.resolve(resolver_stack)

    def _resolve(self, resolver_stack):
        out = self
        if self.type_expr is None:
            return self
        new_expr = self.type_expr.resolve(resolver_stack)
        if new_expr != self.type_expr:
            out =  TypeArg(self.name, new_expr, self.is_optional, self.docs, annotations = self.annotations, docs = self.docs)
        return out

    def unwrap_with_field_path(self, full_field_path, resolver_stack):
        starting_var, field_path = full_field_path.pop()
        curr_typearg = self
        curr_path = curr_field_name = starting_var
        yield curr_field_name, curr_path, curr_typearg
        while field_path.length > 0:
            next_field_name, tail_path = field_path.pop()
            next_path = curr_path + "/" + next_field_name
            if curr_typearg is None:
                set_trace()
            next_typearg = curr_typearg.type_expr.resolve(resolver_stack).args.withname(next_field_name)
            curr_field_name, curr_path, field_path = next_field_name, next_path, tail_path
            yield curr_field_name, curr_path, curr_typearg

class TypeArgList(object):
    """ A list of type args for a particular type container. """
    def __init__(self, type_args):
        self._type_args = []
        for type_arg in type_args or []:
            self.add(type_arg)

    def equals(self, another):
        return len(self._type_args) == len(self._type_args) and all(x.equals(y) for x,y in izip(self._type_args, another._type_args))

    def __getitem__(self, slice):
        return self._type_args.__getitem__(slice)

    def __iter__(self): return iter(self._type_args)

    def __len__(self): return len(self._type_args)

    def __repr__(self):
        return repr(self._type_args)

    @property
    def count(self): return len(self._type_args)

    def index_for(self, name):
        for i,arg in enumerate(self._type_args):
            if arg.name == name:
                return i
        return -1

    def withname(self, name):
        return self.atindex(self.index_for(name))

    def atindex(self, index):
        return None if index < 0 else self._type_args[index]

    def contains(self, name):
        return self.index_for(name) >= 0

    def add(self, arg):
        """
        Add an argument type.
        """
        arg = TypeArg.validate(arg)
        if arg.name:
            index = self.index_for(arg.name)
            if index >= 0:
                raise errors.TLException("Child type by the given name '%s' already exists" % arg.name)
        self._type_args.append(arg)
