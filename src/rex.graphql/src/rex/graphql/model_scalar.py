"""

    rex.graphql.model_scalar
    ========================

    Scalars for GraphQL type system.

    :copyright: 2019-present Prometheus Research, LLC

"""

import datetime
import decimal

from graphql import error, type
from htsql_rex_deploy import domain as domain_extra
from htsql.core import domain
from rex.query.query import LiteralSyntax

from . import model


def raise_error(msg):
    def raises(*args, **kwargs):
        raise error.GraphQLError(msg)

    return raises


string_type = model.ScalarType(
    name="String",
    serialize=type.scalars.coerce_string,
    parse_value=type.scalars.coerce_string,
    parse_literal=type.scalars.parse_string_literal,
    domain=domain.TextDomain(),
)


int_type = model.ScalarType(
    name="Int",
    serialize=type.scalars.coerce_int,
    parse_value=type.scalars.coerce_int,
    parse_literal=type.scalars.parse_int_literal,
    domain=domain.IntegerDomain(),
)


float_type = model.ScalarType(
    name="Float",
    serialize=type.scalars.coerce_float,
    parse_value=type.scalars.coerce_float,
    parse_literal=type.scalars.parse_float_literal,
    domain=domain.FloatDomain(),
)


boolean_type = model.ScalarType(
    name="Boolean",
    serialize=bool,
    parse_value=bool,
    parse_literal=type.scalars.parse_boolean_literal,
    domain=domain.BooleanDomain(),
)


id_type = model.ScalarType(
    name="ID",
    serialize=type.scalars.coerce_str,
    parse_value=type.scalars.coerce_str,
    parse_literal=type.scalars.parse_id_literal,
    domain=domain.TextDomain(),
)


json_type = model.ScalarType(
    name="JSON",
    serialize=lambda v: v,
    parse_value=raise_error("unable to parse JSON value"),
    parse_literal=raise_error("unable to parse JSON value"),
    domain=None,  # TODO: domain_extra.JSONDomain()
)

ISO_FORMAT_DATE = "%Y-%m-%d"


def serialize_date(v):
    return v.strftime(ISO_FORMAT_DATE)


def parse_date_value(v):
    try:
        return datetime.datetime.strptime(v, ISO_FORMAT_DATE).date()
    except ValueError:
        return None


def parse_date_literal(ast):
    v = type.scalars.parse_string_literal(ast)
    if v is None:
        return None
    return parse_date_value(v)


date_type = model.ScalarType(
    name="Date",
    serialize=serialize_date,
    parse_value=parse_date_value,
    parse_literal=parse_date_literal,
    domain=domain.DateDomain(),
)


ISO_FORMAT_DATETIME = "%Y-%m-%dT%H:%M:%S"


def serialize_datetime(v):
    return v.strftime(ISO_FORMAT_DATETIME)


def parse_datetime_value(v):
    try:
        return datetime.datetime.strptime(v, ISO_FORMAT_DATETIME)
    except ValueError:
        return None


def parse_datetime_literal(ast):
    v = type.scalars.parse_string_literal(ast)
    if v is None:
        return None
    return parse_datetime_value(v)


datetime_type = model.ScalarType(
    name="Datetime",
    serialize=serialize_datetime,
    parse_value=parse_datetime_value,
    parse_literal=parse_datetime_literal,
    domain=domain.DateTimeDomain(),
)


def serialize_decimal(v):
    return str(v)


def parse_decimal_value(v):
    return decimal.Decimal(v)


def parse_decimal_literal(ast):
    v = type.scalars.parse_string_literal(ast)
    if v is None:
        return None
    return parse_decimal_value(v)


decimal_type = model.ScalarType(
    name="Decimal",
    serialize=serialize_decimal,
    parse_value=parse_decimal_value,
    parse_literal=parse_decimal_literal,
    domain=domain.DecimalDomain(),
)
