#
# Copyright (c) 2013, Prometheus Research, LLC
#


from rex.core import (LatentRex, get_rex, Extension, Validate, UStrVal,
        OneOrSeqVal, RecordVal, UnionVal, Error, guard, Location, locate,
        set_location)
from .introspect import introspect
import sys
import psycopg2
import yaml


class FactVal(Validate):
    # Converts a mapping to a `Fact` record.

    def __call__(self, data):
        if isinstance(data, Fact):
            return data
        union_val = UnionVal([(fact_type.key, fact_type.validate)
                              for fact_type in Fact.all()])
        return union_val(data)

    def construct(self, loader, node):
        union_val = UnionVal([(fact_type.key, fact_type.validate)
                              for fact_type in Fact.all()])
        return union_val.construct(loader, node)


class LabelVal(UStrVal):
    # An entity label.

    pattern = r'[a-z_][0-9a-z_]*'


class QLabelVal(UStrVal):
    # An entity label with an optional qualifier.

    pattern = r'[a-z_][0-9a-z_]*([.][a-z_][0-9a-z_]*)?'


class TitleVal(UStrVal):
    # Entity title.

    pattern = r'\S(.*\S)?'


class PairVal(Validate):
    # A `key: value` pair.

    def __init__(self, validate_key=None, validate_value=None):
        if isinstance(validate_key, type):
            validate_key = validate_key()
        if isinstance(validate_value, type):
            validate_value = validate_value()
        self.validate_key = validate_key
        self.validate_value = validate_value

    def __call__(self, data):
        with guard("Got:", repr(data)):
            if isinstance(data, tuple):
                if len(data) != 2:
                    raise Error("Expected a pair")
                key, value = data
            elif isinstance(data, dict):
                if len(data) != 1:
                    raise Error("Expected a pair")
                [(key, value)] = data.items()
            else:
                key = data
                value = None
        if self.validate_key is not None:
            with guard("While validating pair key:", repr(key)):
                key = self.validate_key(key)
        if self.validate_value is not None:
            with guard("While validating pair value for key:", repr(key)):
                value = self.validate_value(value)
        return (key, value)

    def construct(self, loader, node):
        if isinstance(node, yaml.ScalarNode):
            key_node = node
            value_node = yaml.ScalarNode(u'tag:yaml.org,2002:null', u"",
                                         node.start_mark, node.end_mark, u'')
        elif (isinstance(node, yaml.MappingNode) and
              node.tag == u'tag:yaml.org,2002:map' and
              len(node.value) == 1):
            [(key_node, value_node)] = node.value
        else:
            error = Error("Expected a pair")
            error.wrap("Got:", node.value
                               if isinstance(node, yaml.ScalarNode)
                               else "a %s" % node.id)
            error.wrap("While parsing:", Location.from_node(node))
            raise error
        with loader.validating(self.validate_key):
            key = loader.construct_object(key_node, deep=True)
        with loader.validating(self.validate_value):
            value = loader.construct_object(value_node, deep=True)
        return (key, value)

    def __repr__(self):
        args = []
        if self.validate_key is not None or self.validate_value is not None:
            args.append(str(self.validate_key))
        if self.validate_value is not None:
            args.append(str(self.validate_value))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(args))


def label_to_title(label):
    """
    Makes a title out of an entity label.
    """
    return label.replace(u'_', u' ').title()


class Driver(object):
    """
    Deploys database facts.

    `connection`
        Open connection to a PostgreSQL database.
    `logging`: ``bool`` or a function.
        If ``True``, prints progress and debug logs to stdout.

        A function must have the following signature::

            def logging(level, msg, *args, **kwds):
                ...

        Here, ``level`` is the logging level, ``msg`` is a format
        string, ``args`` and ``kwds`` are parameters for the format
        string.
    """

    validate = OneOrSeqVal(FactVal())

    #: Logging level for progress reports generated by :func:`deploy()`.
    LOG_PROGRESS = 'progress'
    #: Logging level for displaying timing information.
    LOG_TIMING = 'timing'
    #: Logging level for SQL execution.
    LOG_SQL = 'sql'

    def __init__(self, connection, logging=False):
        self.connection = connection
        self.logging = logging
        self.catalog = None
        #: Current working directory.  Use to resolve relative paths
        #: when parsing YAML records.
        self.cwd = None
        #: Indicates whether the driver is locked.  When the driver
        #: is locked, mutating operations are not allowed.
        self.is_locked = False

    def chdir(self, directory):
        """Sets the current working directory."""
        self.cwd = directory

    def lock(self):
        """Locks the driver."""
        self.is_locked = True

    def unlock(self):
        """Unlocks the driver."""
        self.is_locked = False

    def reset(self):
        """Resets the locking state and cached catalog mirror."""
        self.catalog = None
        self.is_locked = False

    def commit(self):
        """Commits the current transaction."""
        self.connection.commit()

    def rollback(self):
        """Rolls back the current transaction."""
        self.connection.rollback()

    def close(self):
        """Closes the database connection."""
        self.connection.close()

    def parse(self, stream):
        """
        Parses the given YAML string or file and returns a fact or
        a list of facts.
        """
        if isinstance(stream, (str, unicode)) or hasattr(stream, 'read'):
            spec = self.validate.parse(stream)
        else:
            spec = self.validate(stream)
        if isinstance(spec, list):
            return [self.build(item) for item in spec]
        else:
            return self.build(spec)

    def build(self, spec):
        """
        Converts a raw YAML record to a :class:`Fact` instance.
        """
        if isinstance(spec, Fact):
            return spec
        for fact_type in Fact.all():
            if isinstance(spec, fact_type.validate.record_type):
                with guard("While parsing %s fact:" % fact_type.key,
                           locate(spec) or spec):
                    fact = fact_type.build(self, spec)
                set_location(fact, spec)
                return fact
        assert False, "unknown fact record: %s" % spec

    def log(self, level, msg, *args, **kwds):
        # Logs information of the given level.
        if not self.logging:
            return
        if self.logging is True:
            if args or kwds:
                msg = msg.format(*args, **kwds)
            print msg
        else:
            self.logging(level, msg, *args, **kwds)

    def log_progress(self, msg, *args, **kwds):
        # Logs progress report.
        return self.log(self.LOG_PROGRESS, msg, *args, **kwds)

    def log_timing(self, msg, *args, **kwds):
        # Logs timing statistics.
        return self.log(self.LOG_TIMING, msg, *args, **kwds)

    def log_sql(self, msg, *args, **kwds):
        # Logs executed SQL.
        return self.log(self.LOG_SQL, msg, *args, **kwds)

    def get_catalog(self):
        """
        Returns the image of the database catalog.
        """
        if self.catalog is None:
            self.catalog = introspect(self.connection)
        return self.catalog

    def get_schema(self):
        """
        Returns the image of the schema used for deployment.
        """
        return self.get_catalog()[u"public"]

    def submit(self, sql):
        """
        Executes the given SQL expression; returns the result.
        """
        cursor = self.connection.cursor()
        try:
            self.log_sql("{}", sql)
            cursor.execute(sql)
            if cursor.description is not None:
                return cursor.fetchall()
        except psycopg2.Error, exc:
            error = Error("Got an error from the database driver:", exc)
            error.wrap("While executing SQL:", sql)
            raise error
        finally:
            cursor.close()

    def __call__(self, facts, is_locked=None):
        """
        Deploys the given facts.

        `facts`
            A fact or a list of facts to deploy.  One of the following:

            * a string or a file in YAML format;
            * a dictionary or a list of dictionaries;
            * a :class:`Fact` instance or a list of :class:`Fact` instances.

        `is_locked`
            If not ``None``, locks or unlocks the driver for the period
            of deploying the given facts.
        """
        facts = self.parse(facts)
        if not isinstance(facts, list):
            facts = [facts]
        # Set new lock status.
        if is_locked is not None:
            self.is_locked, is_locked = is_locked, self.is_locked
        try:
            # Apply the facts.
            for fact in facts:
                try:
                    fact(self)
                except Error, error:
                    if not self.is_locked:
                        message = "While deploying %s fact:" % fact.key
                    else:
                        message = "While validating %s fact:" % fact.key
                    location = locate(fact) or fact
                    error.wrap(message, location)
                    raise
        finally:
            # Restore original lock status.
            if is_locked is not None:
                self.is_locked, is_locked = is_locked, self.is_locked

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.connection.dsn)


class Fact(Extension):
    """
    Describes state of the database.
    """

    #: List of fields of a YAML record describing the fact.  Subclasses
    #: should set this value.
    fields = []
    #: The name of the field used to recognize the YAML record.  If not set,
    #: the first field from `fields` list is used.
    key = None
    #: Validator for YAML records.  If not set, generated from ``fields``.
    validate = None

    @classmethod
    def all(cls):
        # Gets all `Fact` implementations.
        if not get_rex:
            # Allow it to work even when there is no active Rex application.
            with LatentRex('rex.deploy'):
                return super(Fact, cls).all()
        else:
            return super(Fact, cls).all()

    @classmethod
    def sanitize(cls):
        # Prepares the fact validator.
        if cls.__dict__.get('fields'):
            if 'key' not in cls.__dict__:
                cls.key = cls.fields[0][0]
            if 'validate' not in cls.__dict__:
                cls.validate = RecordVal(cls.fields)

    @classmethod
    def enabled(cls):
        return bool(cls.fields)

    @classmethod
    def build(cls, driver, spec):
        """
        Generates a :class:`Fact` instance from the given YAML record.

        Must be overriden in subclasses.
        """
        raise NotImplementedError("%s.__call__()" % self.__class__.__name__)

    def __call__(self, driver):
        """
        Deploys the fact using the given deployment driver.

        Must be overriden in subclasses.
        """
        raise NotImplementedError("%s.__call__()" % self.__class__.__name__)

    def __repr__(self):
        return "%s()" % self.__class__.__name__


