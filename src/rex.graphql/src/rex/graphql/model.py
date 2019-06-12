"""

    rex.graphql.model
    =================

    :copyright: 2019-present Prometheus Research, LLC

"""

import os
import inspect
import hashlib
import typing
import abc
import cached_property
import functools

from htsql_rex_deploy import domain as domain_extra
from htsql.core.tr.binding import (
    DefineBinding,
    SelectionBinding,
    TableBinding,
    LocateBinding,
    ClipBinding,
)
from htsql.core.tr.lookup import unwrap
from htsql.core import domain
from graphql import error
from graphql.type import scalars as gql_scalars

from rex.core import Error, guard
from rex.db import get_db
from rex.query.bind import RexBindingState
from rex.query.query import LiteralSyntax

from . import code_location, desc, introspection, q


class SchemaNode(abc.ABC):
    """ Nodes of a GraphQL schemas, types, fields or descriptions of those."""


class IsInputType(abc.ABC):
    """ Type which can be used for computed field arguments."""


class IsQueryInputType(abc.ABC):
    """ Type which can be used for query field arguments."""

    @abc.abstractmethod
    def bind_value(self, state, value):
        """ This can be either None or a function which accepts binding state
        and query syntax and returns a binding."""

    @property
    @abc.abstractmethod
    def domain(self):
        """ HTSQL domain."""


def find_named_type(type):
    while not isinstance(type, (EntityType, ObjectType, ScalarType, EnumType)):
        if isinstance(type, (ListType, NonNullType)):
            type = type.type
        else:
            return None
    return type


class Type(SchemaNode):
    def serialize(self, value):
        return value


class ObjectType(Type):
    def __init__(self, descriptor, fields):
        self.fields = fields
        self.descriptor = descriptor

    name = property(lambda self: self.descriptor.name)
    description = property(lambda self: self.descriptor.description)
    loc = property(lambda self: self.descriptor.loc)

    def __hash__(self):
        return hash((type(self), self.name))

    def __eq__(self, other):
        return self.name == other.name

    def __getitem__(self, name):
        return self.fields[name]


class RecordType(ObjectType):
    pass


class EntityType(RecordType):
    def __init__(self, descriptor, table, fields):
        super(EntityType, self).__init__(descriptor=descriptor, fields=fields)
        self.table = table


class ListType(Type, IsInputType, IsQueryInputType):
    def __init__(self, type):
        self.type = type

    def bind_value(self, state, value):
        assert self.domain is not None, "is_input_type check should catch that"
        return state.bind_cast(self.domain, [LiteralSyntax(value)])

    @property
    def domain(self):
        item_domain = self.type.domain
        if item_domain is None:
            return None
        return domain.ListDomain(item_domain)

    def __eq__(self, other):
        return type(self) is type(other) and self.type == other.type

    def __str__(self):
        return f"[{self.type}]"


class NonNullType(Type, IsInputType, IsQueryInputType):
    def __init__(self, type: SchemaNode):
        self.type = type

    def bind_value(self, state, value):
        return self.type.bind_value(state, value)

    domain = property(lambda self: self.type.domain)

    def __eq__(self, other):
        return type(self) is type(other) and self.type == other.type

    def __str__(self):
        return f"{self.type}!"


class EnumType(Type, IsInputType):
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self._names = set(v.name for v in self.values)

    name = property(lambda self: self.descriptor.name)
    values = property(lambda self: self.descriptor.values)
    description = property(lambda self: self.descriptor.description)
    loc = property(lambda self: self.descriptor.loc)

    def __eq__(self, other):
        return self.name == other.name

    def serialize(self, value):
        return value

    def parse_literal(self, ast):
        v = gql_scalars.parse_string_literal(ast)
        if v not in self._names:
            return None
        return v

    def parse_value(self, v):
        if v not in self._names:
            return None
        return v


class ScalarType(Type, IsInputType, IsQueryInputType):
    """ Scalar types represent primitive leaf values in a GraphQL type system.
    GraphQL responses take the form of a hierarchical tree; the leaves on these
    trees are GraphQL scalars.


    All GraphQL scalars are representable as strings, though depending on the
    response format being used, there may be a more appropriate primitive for
    the given scalar type, and server should use those types when appropriate.
    """

    def __init__(self, name, serialize, parse_literal, parse_value, domain):
        self.name = name
        self.serialize = serialize
        self.descriptor = self
        self.parse_literal = parse_literal
        self.parse_value = parse_value
        self._domain = domain

    # IsQueryInputType
    domain = property(lambda self: self._domain)

    def bind_value(self, state, value):
        assert self.domain is not None, "is_input_type check should catch that"
        return state.bind_cast(self.domain, [LiteralSyntax(value)])

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return f"ScalarType({self.name!r})"

    def __str__(self):
        return self.name


class DatabaseEnumType(ScalarType):
    def __init__(self, name, values):
        super(DatabaseEnumType, self).__init__(
            name=name,
            serialize=self.serialize,
            parse_literal=self.parse_literal,
            parse_value=self.parse_value,
            domain=None,
        )
        if not isinstance(values, set):
            values = set(values)
        self.values = values

    def serialize(self, v):
        return v

    def parse_value(self, v):
        if v not in self.values:
            return None
        return v

    def parse_literal(self, ast):
        v = gql_scalars.parse_string_literal(ast)
        if v is None:
            return None
        return self.parse_value(v)

    @classmethod
    def from_domain(cls, dom):
        values = []
        h = hashlib.sha256()
        for label in dom.labels:
            values.append(desc.EnumValue(name=label))
            h.update(label.encode("utf8"))
        # TODO: Try to get the enum type from pg catalog instead.
        name = f"Enum_{h.hexdigest()[:8]}"
        return cls(name=name, values=values)


class Field(SchemaNode):
    """ Base class for fields."""

    params = NotImplemented

    @cached_property.cached_property
    def args(self):
        return {
            name: param
            for name, param in self.params.items()
            if isinstance(param, desc.Argument)
        }


class ComputedField(Field):
    """ Fields computed with resolver."""

    def __init__(self, descriptor, type, params):
        self.descriptor = descriptor
        self.type = type
        self.params = params

    resolver = property(lambda self: self.descriptor.resolver)
    description = property(lambda self: self.descriptor.description)
    deprecation_reason = property(
        lambda self: self.descriptor.deprecation_reason
    )
    loc = property(lambda self: self.descriptor.loc)

    def __eq__(self, o):
        assert isinstance(o, self.__class__)
        return self.type == o.type and self.descriptor == o.descriptor

    def __hash__(self):
        return id(self)


class QueryField(Field):
    def __init__(self, descriptor, type, plural, optional, params):
        self.descriptor = descriptor
        self.plural = plural
        self.optional = optional
        self.type = type
        self.params = params

    loc = property(lambda self: self.descriptor.loc)
    description = property(lambda self: self.descriptor.description)
    deprecation_reason = property(
        lambda self: self.descriptor.deprecation_reason
    )

    def __getitem__(self, name):
        return self.type[name]

    def __eq__(self, o):
        assert isinstance(o, self.__class__)
        return self.type == o.type and self.descriptor == o.descriptor

    def __hash__(self):
        return id(self)


def type_from_domain(ctx, dom: domain.Domain):
    """ Infer GraphQL type from HTSQL domain."""
    # We support only scalar types at the moment, mostly because object type (a
    # record-like type) in GraphQL is a named type (requires name to be
    # specified).
    if isinstance(dom, domain.BooleanDomain):
        return ctx.root.types["Boolean"]
    elif isinstance(dom, domain.FloatDomain):
        return ctx.root.types["Float"]
    elif isinstance(dom, domain.IntegerDomain):
        return ctx.root.types["Int"]
    elif isinstance(dom, domain.TextDomain):
        return ctx.root.types["String"]
    elif isinstance(dom, domain.DateDomain):
        return ctx.root.types["Date"]
    elif isinstance(dom, domain.DateTimeDomain):
        return ctx.root.types["Datetime"]
    elif isinstance(dom, domain.DecimalDomain):
        return ctx.root.types["Decimal"]
    elif isinstance(dom, domain.EnumDomain):
        return DatabaseEnumType.from_domain(dom)
    elif isinstance(dom, domain_extra.JSONDomain):
        return ctx.root.types["JSON"]
    else:
        return None


### Specification aware helpers


def is_input_type(type: Type):
    return isinstance(type, IsInputType)


def is_query_input_type(type: Type):
    return isinstance(type, IsQueryInputType) and type.domain is not None


class SchemaContext:
    @cached_property.cached_property
    def root(self):
        ctx = self
        while True:
            if isinstance(ctx, RootSchemaContext):
                return ctx
            ctx = ctx.parent


class RootSchemaContext(SchemaContext):
    __slots__ = ("types", "loc")

    def __init__(self, types, loc):
        self.types = types
        self.loc = loc


class TypeSchemaContext(SchemaContext):
    __slots__ = ("name", "parent", "loc")

    def __init__(self, name, parent, loc):
        self.name = name
        self.parent = parent
        self.loc = loc


class QuerySchemaContext(SchemaContext):
    __slots__ = ("output", "table", "parent", "loc")

    def __init__(self, output, table, parent, loc):
        self.output = output
        self.table = table
        self.parent = parent
        self.loc = loc


class ComputeSchemaContext(SchemaContext):
    __slots__ = ("parent", "loc")

    def __init__(self, parent, loc):
        self.parent = parent
        self.loc = loc


@functools.singledispatch
def construct(arg, ctx, *args):
    """ Construct schema node out of description."""
    assert False, f"Do not know how to construct schema of {arg!r}"


@functools.singledispatch
def check(arg, ctx, *args):
    """ Check schema node against context."""
    assert False, f"Do not know how to check {arg!r}"


@construct.register(desc.Object)
def _(descriptor, ctx):
    with code_location.context(
        descriptor.loc,
        desc=f"While configuring object type '{descriptor.name}':",
    ):
        # Try to check if we have it constructd already
        type = ctx.root.types.get(descriptor.name)
        if type is None:
            # First store it in cache so we can refer to it recursively...
            fields = {}
            type = ObjectType(fields=fields, descriptor=descriptor)
            ctx.root.types[descriptor.name] = type
            # ...and then validate its fields
            next_ctx = TypeSchemaContext(
                name=descriptor.name, parent=ctx, loc=descriptor.loc
            )
            desc_fields = list(descriptor.fields.items()) + [
                ("__typename", introspection.typename_field)
            ]
            for name, field in desc_fields:
                assert isinstance(field, desc.Field)
                field = construct(field, next_ctx, name)
                fields[name] = field
        else:
            if not descriptor is type.descriptor:
                raise Error(
                    "Type with the same name is already defined:", type.loc
                )
        return type


@construct.register(desc.Entity)
def _(descriptor, ctx):
    err_ctx = lambda: code_location.context(
        descriptor.loc, desc=f"While configuring entity '{descriptor.name}':"
    )

    with err_ctx():
        with code_location.context(
            ctx.loc, desc="Type is used in the context:"
        ):
            # Check that we are in the query context.
            if not isinstance(ctx, QuerySchemaContext):
                raise Error("Entity type can only be queried with query(..)")
            if ctx.table is None:
                raise Error(
                    f"Entity type can only be queried with query(..) which"
                    f" result in a table"
                )

    # Try to check if we have it constructd already.
    type = ctx.root.types.get(descriptor.name)
    if type is None:
        # First store it in cache so we can refer to it recursively...
        fields = {}
        type = EntityType(
            table=ctx.table, fields=fields, descriptor=descriptor
        )
        ctx.root.types[descriptor.name] = type
        # ...and then validate its fields
        next_ctx = TypeSchemaContext(
            name=descriptor.name, parent=ctx, loc=descriptor.loc
        )

        desc_fields = list(descriptor.fields.items())
        desc_fields.append(("__typename", introspection.typename_field))
        desc_fields.append(("id", desc.query(q.id(), type=desc.scalar.ID)))

        for name, field in desc_fields:
            field_loc = field.loc
            field = construct(field, next_ctx, name)
            if not isinstance(field, QueryField) and name != "__typename":
                with err_ctx():
                    msg = "Entity types can only contain queries but got:"
                    raise Error(msg, field_loc)
            fields[name] = field
    else:
        with err_ctx():
            # Check that the type is originating from the same descriptor,
            # otherwise it's an error.
            if not descriptor is type.descriptor:
                msg = "Type with the same name is already defined:"
                raise Error(msg, type.loc)
        if not isinstance(type, EntityType):
            raise Error("Expected entity type but got:", type)
        check(type, ctx)
    return type


@construct.register(desc.Record)
def _(descriptor, ctx):
    err_ctx = lambda: code_location.context(
        descriptor.loc, desc=f"While configuring record '{descriptor.name}':"
    )

    with err_ctx():
        with code_location.context(
            ctx.loc, desc="Type is used in the context:"
        ):
            # Check that we are in the query context.
            if not isinstance(ctx, QuerySchemaContext):
                raise Error("Entity type can only be queried with query(..)")

    # Try to check if we have it constructed already.
    type = ctx.root.types.get(descriptor.name)
    if type is None:
        # First store it in cache so we can refer to it recursively...
        fields = {}
        type = RecordType(fields=fields, descriptor=descriptor)
        ctx.root.types[descriptor.name] = type
        # ...and then validate its fields
        next_ctx = TypeSchemaContext(
            name=descriptor.name, parent=ctx, loc=descriptor.loc
        )

        desc_fields = list(descriptor.fields.items())
        desc_fields.append(("__typename", introspection.typename_field))

        for name, field in desc_fields:
            field_loc = field.loc
            field = construct(field, next_ctx, name)
            if not isinstance(field, QueryField) and name != "__typename":
                with err_ctx():
                    msg = "Record types can only contain queries but got:"
                    raise Error(msg, field_loc)
            fields[name] = field
    else:
        with err_ctx():
            # Check that the type is originating from the same descriptor,
            # otherwise it's an error.
            if not descriptor is type.descriptor:
                msg = "Type with the same name is already defined:"
                raise Error(msg, type.loc)
        if not isinstance(type, RecordType):
            raise Error("Expected record type but got:", type)
        check(type, ctx)
    return type


@check.register(EntityType)
def _(type, ctx: QuerySchemaContext):
    assert isinstance(ctx, QuerySchemaContext)
    assert isinstance(ctx.parent, TypeSchemaContext)
    assert ctx.table is not None

    # As EntityType type corresponds to a database table we can just check that
    # the type is used in the context of the same table it was instantiated
    # before.
    if ctx.table is not type.table:
        raise Error(
            f"Type '{type.name}' represents database table '{type.table}'"
            f" but was used in the context of query which results in table"
            f" '{ctx.table}'"
        )


@check.register(RecordType)
def _(type, ctx: QuerySchemaContext):
    assert isinstance(ctx, QuerySchemaContext)
    assert isinstance(ctx.parent, TypeSchemaContext)
    # We need to make sure we can construct all fields of the type in the
    # current context too! Then check that those fields constructed are
    # identical to the ones we have too.
    next_ctx = TypeSchemaContext(
        name=type.name, parent=ctx, loc=type.descriptor.loc
    )
    for name, field in type.fields.items():
        this_field = construct(field.descriptor, next_ctx, name)
        # TODO: raise Error instead
        assert this_field == field


@construct.register(desc.List)
def _(descriptor, ctx):
    return ListType(construct(descriptor.type, ctx))


@construct.register(desc.NonNull)
def _(descriptor, ctx):
    return NonNullType(construct(descriptor.type, ctx))


@construct.register(desc.Enum)
def _(descriptor, ctx):
    type = ctx.root.types.get(descriptor.name)
    if type is None:
        type = EnumType(descriptor=descriptor)
    else:
        if not isinstance(type, EnumType):
            raise Error(f"Type {descriptor.name} is not an enum type")
        if type.descriptor is not descriptor:
            raise Error(f"Type {descriptor.name} is already defined")

    return type


@construct.register(desc.Scalar)
def _(descriptor, ctx):
    type = ctx.root.types.get(descriptor.name)
    if type is None:
        raise Error(f"No type with name {descriptor.name} defined")
    if not isinstance(type, ScalarType):
        raise Error(f"Type {descriptor.name} is not a scalar type")
    return type


@construct.register(desc.Compute)
def _(descriptor, ctx, name):

    with code_location.context(
        descriptor.loc, desc="While configuring computation:"
    ):
        ctx = ComputeSchemaContext(parent=ctx, loc=descriptor.loc)
        type = construct(descriptor.type, ctx)
        named_type = find_named_type(type)
        if named_type.name not in ctx.root.types:
            ctx.root.types[named_type.name] = named_type

        params = {}
        for param_name, param in descriptor.params.items():
            params[param_name] = construct(param, ctx)

        return ComputedField(descriptor=descriptor, type=type, params=params)


@construct.register(desc.Query)
def _(descriptor, ctx, name):
    assert isinstance(ctx, TypeSchemaContext)

    with code_location.context(
        descriptor.loc, desc="While configuring query:"
    ):

        params = {}
        for param_name, param in descriptor.params.items():
            if param.type is None:
                raise Error("Cannot use param without type:", param.name)
            params[param_name] = construct(param, ctx)

        state = RexBindingState()

        vars = {}
        for param_name, param in params.items():
            if not is_query_input_type(param.type):
                raise Error(
                    f"Unsupported query argument type `{param_name} : {param.type}`:",
                    param.loc,
                )
            vars[param_name] = state.bind_cast(
                param.type.domain, [LiteralSyntax(None)]
            )

        # Bring the context into binding state
        if isinstance(ctx.parent, QuerySchemaContext):
            state.push_scope(ctx.parent.output.binding)

        # Finally produce binding
        with state.with_vars(vars):
            output = state(descriptor.query.syn)

            # Try to bind filters (if they are specified via queries)
            state.push_scope(output.binding)
            for filter in descriptor.filters:
                if isinstance(filter, desc.FilterOfQuery):
                    state(filter.query.syn)
            state.pop_scope()

        def base(binding):
            if isinstance(binding, (LocateBinding, ClipBinding)):
                return base(binding.seed)
            elif isinstance(binding, (DefineBinding,)):
                return base(binding.base)
            else:
                return binding

        # Probe the kind of output
        probe = base(output.binding)
        selection_binding = unwrap(probe, SelectionBinding, is_deep=True)
        table_binding = unwrap(probe, TableBinding, is_deep=True)

        if selection_binding:
            # This means the query results in a record (has `some {...}` syntax
            # at the end.
            if descriptor.type is None:
                msg = (
                    f"Query results in a record but no type is provided,"
                    f" please specify it like this:"
                )
                raise Error(msg, "query(..., type=TYPE)")

            ctx = QuerySchemaContext(
                parent=ctx, output=output, table=None, loc=descriptor.loc
            )
            type = construct(descriptor.type, ctx)

        elif table_binding:

            if descriptor.type is None:
                msg = (
                    f"Query results in an entity (table '{table_binding.table}')"
                    f" but no type is provided, please specify it like this:"
                )
                raise Error(msg, "query(..., type=TYPE)")

            ctx = QuerySchemaContext(
                parent=ctx,
                output=output,
                table=table_binding.table,
                loc=descriptor.loc,
            )
            type = construct(descriptor.type, ctx)
        else:
            # Neither a table nor selection, a scalar then!
            # TODO: Confirm with @xi
            if descriptor.type is None:
                type = type_from_domain(ctx, output.domain)
                if type is None:
                    msg = (
                        f"Unable to infer query type automatically for"
                        f" database type '{output.domain}', please specify it:"
                    )
                    raise Error(msg, "query(..., type=TYPE)")
            else:
                type = descriptor.type
                ctx = QuerySchemaContext(
                    parent=ctx, output=output, table=None, loc=descriptor.loc
                )
                type = construct(type, ctx)

            table = None

        if descriptor.paginate and not output.plural:
            raise Error(
                "cannot define paginated query field for a non plural output"
            )

        if not output.optional:
            type = NonNullType(type)
        if output.plural:
            type = ListType(type)

        named_type = find_named_type(type)
        if named_type.name not in ctx.root.types:
            ctx.root.types[named_type.name] = named_type

        return QueryField(
            descriptor=descriptor,
            optional=output.optional,
            plural=output.plural,
            type=type,
            params=params,
        )


@construct.register(desc.Argument)
def _(descriptor, ctx):
    type = construct(descriptor.type, ctx.root)
    return descriptor.with_type(type)


@construct.register(desc.ComputedParam)
def _(descriptor, ctx):
    if descriptor.type is not None:
        type = construct(descriptor.type, ctx.root)
        return descriptor.with_type(type)
    else:
        return descriptor
