
class TypeTemplate(Annotatable):
    """
    A type template defines a generic type with parameters and its arguments.  The arguments can themselves
    be concrete types instantiated by referring to the type parameters of this type template.  For instance:

        data Tree a = Empty | Leaf a | Node (Tree a) (Right a)

        Here the type template would be:

            parameters = ["a"]
            is_union = True

            Before args can be specified, we should create 3 more TypeTemplates:

            Tree.Empty = {
                parent = Tree
                parameters = None
                is_union = False
                args = None
            }

            Tree.Leaf = {
                parent = Tree
                parameters = ["x"]
                is_union = False
                args = [ TypeArg(TypeParam("x")) ]
            }

            Tree.Node = {
                parent = Tree
                parameters = ["x"]
                is_union = False
                args = [  TypeArg(TypeParam("x")), TypeArg(TypeParam("x")) ]    # Two unnamed arguments
            }

            Based on this Tree.args would look like:
            Tree.args = [
                TypeArg(Tree.Empty),                    - A normal type ref as Tree.Empty is parametrized or has 0 params
                TypeArg(make_concrete(Tree.Leaf, "$a"), - Concretizing a parametrized type with arguments - Args can be params referring to anther type
                                                          Labels ("a") must be a parameter in the parent type.
                TypeArg(make_concrete(Tree.Node, "$a", "$a")
            ]

        One thing to see is if we want the entries pointed in the typerefs to be Type or TypeTemplate?  Or can/should we allow both?
        This distinction is only required if a TypeTemplate differs from a Type.  Can/Should the two be unified and overloaded or
        be refactored into distinct objects?

        Another example: Array:

        data array x 

        parameters = ["x"]
        is_union = False
        args = TypeArg(TypeParam("x"))

        This is a template type.  The concrete version would be:

        "array".make_concrete(TypeRef("Statement"))

        To use this in a template type with a param we would have:

        "array".make_concrete(TypeParam("x"))

        TypeParam must somehow link back to the right parent via the parent_type (not ref) or parent_typetemplate may be?

        Also "make_concrete" must return a Type which can then be wrapped by the caller in a typeref.
    """
    pass


