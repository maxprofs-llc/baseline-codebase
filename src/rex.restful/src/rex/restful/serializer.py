#
# Copyright (c) 2013, Prometheus Research, LLC
#

import json
import re

from datetime import datetime, date, time
from decimal import Decimal

import yaml

from dateutil.parser import parse as parse_date

from rex.core import cached, Extension


__all__ = (
    'Serializer',
    'JsonSerializer',
    'YamlSerializer',
    'marshall_htsql_result',
)


class Serializer(Extension):
    """
    This is an Extension that allows developers to implement additional data
    formatting/encoding methods for their APIs to support.
    """

    #: The string that identifies the Serializer when passed to the "format"
    #: querystring parameter. Must be specified by concrete classes.
    format_string = None

    #: The MIME type that identifies the format/encoding the Serializer. It is
    #: used when checking the incoming Content-Type for compatibility, and it
    #: is sent in the Content-Type of the response. Must be specified by
    #: concrete classes.
    mime_type = None

    @classmethod
    def signature(cls):
        return cls.mime_type

    @classmethod
    @cached
    def mapped_format(cls):
        """
        Returns mapping of format identifiers to the Serializer implementation
        that supports them.

        :rtype: dict
        """

        mapping = {}
        for ext in cls.all():
            assert ext.format_string not in mapping, \
                'duplicate format string: %s' % ext.format_string
            mapping[ext.format_string] = ext
        return mapping

    @classmethod
    @cached
    def get_for_mime_type(cls, mime_type):
        """
        Retrieves the Serializer implementation that supports the specified
        MIME type. If an implementation cannot be found, ``None`` is returned.

        :param mime_type: the MIME type to retrieve
        :type mime_type: string
        :rtype: Serializer
        """

        mime_type = mime_type.split(';')[0]
        return cls.mapped().get(mime_type)

    @classmethod
    @cached
    def get_for_format(cls, fmt):
        """
        Retrieves the Serializer implementation that supports the specified
        format identifier. If an implementation cannot be found, ``None`` is
        returned.

        :param fmt: the format identifier to retreive
        :type fmt: string
        :rtype: Serializer
        """

        return cls.mapped_format().get(fmt)

    @classmethod
    def enabled(cls):
        return cls.format_string is not None and cls.mime_type is not None

    @classmethod
    def sanitize(cls):
        if cls.enabled():
            assert cls.serialize != Serializer.serialize, \
                'abstract method %s.serialize()' % cls
            assert cls.deserialize != Serializer.deserialize, \
                'abstract method %s.deserialize()' % cls

    def __init__(self, **kwargs):
        pass

    def serialize(self, value):
        """
        Encodes/Formats the data from the result of the API for transmission
        to the client.

        Must be implemented by concrete classes.

        :param value:
            the outgoing data that is to be serialized; typically, this is a
            Python ``dict``, ``list``, or ``tuple``
        :rtype: string
        """

        raise NotImplementedError()

    def deserialize(self, value):
        """
        Decodes the data from the client for use in the API methods.

        Must be implemented by concrete classes.

        :param value: the incoming data that is to be deserialized
        :type value:
            an object that acts as both a string and a file-like object
        :returns: the decoded object
        """

        raise NotImplementedError()


class RestfulJSONEncoder(json.JSONEncoder):
    # pylint: disable=method-hidden,arguments-differ
    def default(self, obj):
        if isinstance(obj, datetime):
            parts = obj.utctimetuple()
            return '%d-%02d-%02dT%02d:%02d:%02d.%sZ' % (
                parts.tm_year,
                parts.tm_mon,
                parts.tm_mday,
                parts.tm_hour,
                parts.tm_min,
                parts.tm_sec,
                ('%06d' % obj.microsecond)[:-3],
            )

        if isinstance(obj, (date, time)):
            return obj.isoformat()

        if isinstance(obj, Decimal):
            return float(obj)

        if isinstance(obj, set):
            return list(obj)

        return super(RestfulJSONEncoder, self).default(obj)


RE_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
RE_TIME = re.compile(r'^\d{2}:\d{2}:\d{2}$')
RE_DATETIME = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z)?$')


def get_date_or_string(value):
    if RE_DATETIME.match(value):
        try:
            return parse_date(value, ignoretz=True)
        except ValueError:  # pragma: no cover
            pass

    elif RE_DATE.match(value):
        try:
            return parse_date(value).date()
        except ValueError:  # pragma: no cover
            pass

    elif RE_TIME.match(value):
        try:
            return parse_date(value).time()
        except ValueError:  # pragma: no cover
            pass

    return value


# Adapted from http://stackoverflow.com/a/3235787
def restful_json_decoder(value):
    if isinstance(value, list):
        pairs = enumerate(value)
    elif isinstance(value, dict):
        pairs = list(value.items())

    results = []
    for key, val in pairs:
        if isinstance(val, str):
            val = get_date_or_string(val)

        elif isinstance(val, (dict, list)):
            val = restful_json_decoder(val)

        results.append((key, val))

    if isinstance(value, list):
        return [result[1] for result in results]

    elif isinstance(value, dict):
        return dict(results)


class JsonSerializer(Serializer):
    """
    An implementation of Serializer that supports JSON-encoded structures.
    """

    #:
    format_string = 'json'

    #:
    mime_type = 'application/json'

    def __init__(self, deserialize_datetimes=True, **kwargs):
        super(JsonSerializer, self).__init__(**kwargs)
        self.deserialize_datetimes = deserialize_datetimes

    def serialize(self, value):
        return json.dumps(value, cls=RestfulJSONEncoder)

    def deserialize(self, value):
        object_hook = None
        if self.deserialize_datetimes:
            object_hook = restful_json_decoder
        return json.loads(value, object_hook=object_hook)


class YamlSerializer(Serializer):
    """
    An implementation of Serializer that supports YAML-encoded structures.
    """

    #:
    format_string = 'yaml'

    #:
    mime_type = 'application/x-yaml'

    def __init__(self, deserialize_datetimes=True, **kwargs):
        super(YamlSerializer, self).__init__(**kwargs)
        self.deserialize_datetimes = deserialize_datetimes

    def serialize(self, value):
        return yaml.dump(value, Dumper=RestfulYamlDumper, allow_unicode=True, default_flow_style=None)

    def deserialize(self, value):
        # TODO: deserialize '12:34:56' into datetime.time()
        loader = yaml.SafeLoader
        if not self.deserialize_datetimes:
            loader = StringedDatesYamlLoader
        return yaml.load(value, Loader=loader)  # noqa: B506


class RestfulYamlDumper(yaml.SafeDumper):
    def decimal_representer(self, data):
        return self.represent_scalar('tag:yaml.org,2002:float', str(data))

    def time_representer(self, data):
        return self.represent_scalar('tag:yaml.org,2002:str', data.isoformat())

    def set_representer(self, data):
        return self.represent_sequence('tag:yaml.org,2002:seq', list(data))


RestfulYamlDumper.add_representer(
    Decimal,
    RestfulYamlDumper.decimal_representer,
)
RestfulYamlDumper.add_representer(
    time,
    RestfulYamlDumper.time_representer,
)
RestfulYamlDumper.add_representer(
    set,
    RestfulYamlDumper.set_representer,
)


class StringedDatesYamlLoader(yaml.SafeLoader):
    def timestamp_constructor(self, node):
        return self.construct_scalar(node)


StringedDatesYamlLoader.add_constructor(
    'tag:yaml.org,2002:timestamp',
    StringedDatesYamlLoader.timestamp_constructor,
)


def marshall_htsql_result(result):
    """
    Marshalls an HTSQL Product or Record into a simple Python list or
    dictionary so that it can be more easily handled by the built-in
    rex.restful serializers.

    :param result: the HTSQL query result to marshall
    :type result: htsql.core.domain.Product or htsql.core.domain.Record
    :returns: list or dictionary
    """

    if result.__class__.__module__ == 'htsql.core.domain' \
            and result.__class__.__name__ == 'Product':
        return [
            marshall_htsql_result(rec)
            for rec in result.data
        ]

    if result.__class__.__base__.__module__ == 'htsql.core.domain' \
            and result.__class__.__base__.__name__ == 'Record':
        return dict(list(zip(
            result.__fields__,
            [marshall_htsql_result(col) for col in result],
        )))

    if result.__class__.__module__ == 'htsql.core.domain' \
            and result.__class__.__name__ == 'ID':
        return str(result)

    if isinstance(result, list):
        return [
            marshall_htsql_result(rec)
            for rec in result
        ]

    return result

