
# typecube

A type system library and toolchain for python.

How to do a simple type library for making schema conversions seamless?

Everything has a Type.  Every object has a "final" type.  Every TypeOp (TypeFunction) has an intermediate type?

what we really want is to be able to express:

    record Pair<X,Y>  {
            first : X
            second : Y
    }

    or 

    record<X,Y> Pair {
            first : X
            second : Y
    }

but without going into defining a new syntax, if we start with schemas to define structure, we could have:

    class Pair(Record[X,Y]):
        """
        First value in the pair.
        """
        @field(default = 0)
        first : X

        """
        Second value in the pair
        """
        second : Y = 0

or 

Pair = Record[X,Y](first : X = Field(.....), second = Y)

I personally prefer the first version as we can take advantage of normal py syntax to express documentations etc instead of having to have explicit functions and constructors.  Just cleaner.

Also though for now we are avoiding annotations (as these can be actual function specs), the first leaves room to bring back annotations if necessary as a first class object. eg:

    class Pair(Record[X,Y]):
        """
        Definition of a field.
        """
        @annotation1(....)
        @annotation2(....)
        x : Optional[X] = 0

Here an annotation only expects that it takes a class var and returns a class var.

One problem with above is that it is not clear that X,Y and type parameters.

The instantiation of a Pair instance could be as:

    x = Pair[int,string]()

How about atomic types?

Int = TypeAtom("int")

x : Int

FunctionType

For record instead of treating every class variable as a field, how about making it explicit?  ie those whose values are instances of Type, eg:

@TypeVar('X')
@TypeVar('Y')
class Pair(Record):
    @default(0)
    @optional(False)
    first = X

    @default(0)
    second = Y

then i should be able to do this:

class StreetAddress(Record):
    number = Int
    street = String
    location = Pair[float, float]
    zipcode = String

class POCode(Record):
    country = String
    code = Int

class Address(Union):
    street_address = StringAddress
    pobox = POCode

Going back to Pair above, optional could be a type?  ie Optional[X]?  This could mean two things depending on domain:
Union[X, None] - ie "first" has either no type or type X.  Or it could mean that "first" may not have have a value.  So should we treat Optional as a type and not worry about domain specific interpretation?  This is not a bad idea because if somebody truly wants to share type semantics across domains they could make that a "common" type and say call it OptionalValued[X] and OptionalTyped[Y].  Point of typecube is that you should be able to create arbitrary types easily.

Second observation is that we are only forced to resort to:

first = X

syntax because of compatibility with Python2.  What if this was a python 3.5+ lib all together?  Then we could still gowith class vars whose annotation is of a type Type instead of a value AND we get the benefit of inlinining default values, ie:

first : Int = 0

Atomic/Native Types
===================

class AtomType(Type):
    def __init__(self, label):
        self.label = label

so we can do:

Int = AtomType('Int')
Float = AtomType('Float')
String = AtomType('str')

or:

class Float(AtomType): pass
class String(AtomType): pass
class Int(AtomType): pass

Note that the above have no tie to an actual base/primitive/native type in the language.  The point is that these are meant to be universal across domains and even languages so that if/when code gen happens they will be mapped to proper types.

Ok how about collections and "extern" types eg List<String>, Map<Int, String> and so on?  We can create simple unions and records that are parametrized but these are more like external types that dont have a specific definition.  eg list<String> maps to list, List<String> (in py3k) or List<String> in java or std::list<string> in C++.  This can be done via type operators:

@typevar<X>
class List(AtomType): pass

or can we just do:

List = AtomType[typevar('X')]('List')

or:

List = ExternType('List')

By this definition both Atom and Extern are almost the same since they are both dependent on the platform and are "opaque".  So why not combine them?  eg:

Int = AtomType('Int')
Float = AtomType('Int')
List = AtomType('List', 'E')
Map = AtomType('List', 'K', 'V')
Set = AtomType('List', 'E')

E = TypeVar('E')

# or 
List = AtomType('List', E)
Map = AtomType('List', TypeVar('K'), TypeVar('V'))
Set = AtomType('List', TypeVar('E'))

Type Variables
==============

One thing about type vars - They are unique by name, regardless of how many times they are created.  This means they will always resolve to the same static context of the type in which they are used and not where they were created.

eg:

Type Generation
===============

So now we have defined the onering model above which is the DAO for the Channel.   We know what fields it contains and ONLY the fields.  Nothing else.  This is the model that is extracted off the wire (or very close to it).  At the very least this is the application level model that is independant of any wire or storage factors to it.

This is where it gets interesting.   All our business logic will work with the above (*pure* DAO) model.  But it will have to be converted to different other models for other purposes.  

For instance when it needs to be written back to Http it has to be converted to a HttpResponse. 

when it needs to be written to a DB, it has to be converted to some DB specific object that the DB's client library canaccept and so on.  This gets more interesting as this is either for the purpose of an "update" or for the purposes of a "create".

So when we do this creation, does the target model already exist or can it be auto generated.  May depend.  Regardless of how the target model/schema is specified it has to be created/maintained/source controlled.

Our options for schema:

1. Manually create target schema

Here we would create all schemas in all domains.

Pros:
    Simple and does not need fancy logic.  
    no need to worry about bi-directionality.

Cons:
    Lot of duplication and curation of schemas when one changes it has a manual cascading effect.  
    Transformer functions still needed and will most likely be manual.

2. Have type function that creates a new type from one or more source types into one or more target type in some "algorithmic" way so that general rules (based n generator function) will be standard.

Pros:
    No manual schema management.
    If done right, we get some transformations that can be auto generated.
    Bidirectionality *may* be solved if this heuristics are two way from the get go.

Cons:
    Management of many rules/heuristics for recognizing and applying field to field mappings/transformations.
    Bidirectionality can still be a hard problem to solve.

3. Some combination of the two - ie a multipass generator that creates some basic ones via filters + maps etc and then allows the addition/deletion of fields.

Pros:
    Working with type level primitivies, ie Add Field, Remove Field, Replace/Rename Field operators
    Can restrict primitives to be reversible to help with bidrectionality.  ie if Add Field is needed going from A -> B then B -> A would be a remove field.

Cons:
    TBD

Transformers
============
This still does not allow transformers to be auto generated because the types may be completely different in each domain.  For instance in our typecub Record, fields would have our own property types, eg IntType, StringType, TimestampType etc.  To go from here to an appengine model, these may need to be converted respective GAE types, eg IntegerProperty, StringProperty, DateTimeProperty and so on.

Also the transformation can be of several types:

```
    source.field1 -> target.field1      # plain one to one with no name or type changes
    source.field1 -> target.field2      # field to field mapping with only a name change
    F(source.field1) -> target.field2       # A source field transformed and applied onto a target field
    F(source.f1,f2)  -> target.field2       # A few source fields transformed and applied onto a target field
```

Couple of things to note:
    With transformers we only need to worry about transformation of objects and not types (in the case of instances).
    In the above, only the first two are reversible.  The last two are not reversible transformations.  So a single transformer wont suffice making it almost worthless to combine the type generation and instance transformation phases.



Type constructors
=================

We have a case where Types can have "attributes".   Eg StringField with max_length attribute.
*BUT* - how is this *not* a dependant type?  *or* a Type with "validators"?  For example

a List<10> is actually a list of 10 elements only.  Should this be a type or a validtor?
If we had the above, then we still havent told what the type is.  So how do we say?  List<Int, 10>?  *So* what is the base type here?
 
is it List?, List<Int>? or List<Int, max_size = 10>?

At the end of the day having this as a dependant type is "pure", but essentially will cause two problems:

1. Very expensive to reason about "equality" of types.

The checker has to do more things in terms of not only invoking these custom validator functions and then marshall the results as type objects and will make ser/deser inefficient.

2. Validation coupled with ser/deser.

For the scenario where we want serialization/deser to happen to a certain format before any validation happens we are forcing it all to happen at the same time, unless we actually explicitly create the types for the two stages and then let transformers do the work?

*But*, if base types was left off as Generics with validators/annotations that we add, it should suffice as we are not doing computation on objects and letting validators do their thing as long as validators conform to a particular contract.

The problem of treating these as validators is they are untyped and unbounded.  For instance it is easy to do something like:

@mustbe("hello")
age : Integer

This contrived "mustbe" validator enforces that its value is the one provided.  However this can never apply to an Integer value.

There are a couple of options for making this work:

* Make validators typed functions, eg:

```
mustbe :: String -> String
```

This way the provider can decide how to implement (and resolve) this function.

While this is good to "chain" things, it may not help with what *should* be chained?

ie just because have a valid typed validator, does not mean it should.

eg a StringField in django could have an "unique" attribute, 

but StringProperty in gae could have a "default" attribute.

The StringField and StringProperty are both a type+validator combo even the underlying value for both is a String type.

ie StringProperty/StringField -> String conversion only matches if validations succeed.

so our gae schema could be:

@gae.default("..")
@gae.max_length(50)
@gae.unique(True)
name : String

Unique - is a totally datastore stipulation
Max_length - write time validation
default - readtime decoration

I am not sure the concept of typed annotations is even the right thing.

A SchemaEntry is not a type, but rather type + validations or expectations.

So why arent we treating it as such?

ie SchemaField = {
    name : String
    metadata/validators : ...
    documentation : ...
}

Currently we are treating a child in a Type as the above and documentation is just another "annotation".  Problem with annotation is they are completely untyped so it would be good to annotate them.
