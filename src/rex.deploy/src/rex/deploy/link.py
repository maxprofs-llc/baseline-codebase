#
# Copyright (c) 2013, Prometheus Research, LLC
#


from rex.core import Error, BoolVal
from .fact import Fact, LabelVal, QLabelVal
from .sql import (mangle, sql_add_column, sql_drop_column,
        sql_add_foreign_key_constraint)


class LinkFact(Fact):
    """
    Describes a link between two tables.

    `table_label`: ``unicode``
        The name of the origin table.
    `label`: ``unicode``
        The name of the link.
    `target_table_label`: ``unicode`` or ``None``
        The name of the target table.  Must be ``None``
        if ``is_present`` is not set.
    `is_required`: ``bool`` or ``None``
        Indicates if ``NULL`` values are not allowed.  Must be ``None``
        if ``is_present`` is not set.
    `is_present`: ``bool``
        Indicates whether the link exists.

    YAML record has the following fields:

    `link`: ``<label>`` or ``<table_label>.<label>``
        Either the link name or the table and the link names separated
        by a period.
    `of`: ``<table_label>``
        The name of the origin table.  If omitted, the table name must be
        specified in the ``link`` field.
    `to`: ``<target_table_label>``
        The name of the target table.  If omitted, assumed to coincide
        with the link name.
    `required`: ``true`` (default) or ``false``
        Indicates if the ``NULL`` values are not allowed.
    `present`: ``true`` (default) or ``false``
        Indicates whether the link exists.

    Deploying when ``is_present`` is on:

        Ensures that table ``<table_label>`` has a column ``<label>_id``
        and a ``FOREIGN KEY`` constraint from ``<table_label>.<label>_id``
        to ``<target_table_label>.id``.  If ``is_required`` is set,
        the column should have a ``NOT NULL`` constraint.

        It is an error if table ``<table_label>`` or ``<target_table_label>``
        does not exist.

    Deploying when ``is_present`` is off:

        Ensures that table ``<table_label>`` does not have column
        ``<label>_id``.  If such a column exists, it is deleted.

        It is *not* an error if table ``<table_label>`` does not exist.
    """

    fields = [
            ('link', QLabelVal),
            ('of', LabelVal, None),
            ('to', LabelVal, None),
            ('required', BoolVal, None),
            ('present', BoolVal, True),
    ]

    @classmethod
    def build(cls, driver, spec):
        if u'.' in spec.link:
            table_label, label = spec.link.split(u'.')
            if spec.of is not None and spec.of != table_label:
                raise Error("Got mismatched table names:",
                            ", ".join((table_label, spec.of)))
        else:
            label = spec.link
            table_label = spec.of
            if spec.of is None:
                raise Error("Got missing table name")
        target_table_label = spec.to
        is_required = spec.required
        is_present = spec.present
        if is_present:
            if target_table_label is None:
                target_table_label = label
            if is_required is None:
                is_required = True
        else:
            if target_table_label is not None:
                raise Error("Got unexpected clause:", "to")
            if is_required is not None:
                raise Error("Got unexpected clause:", "required")
        return cls(table_label, label, target_table_label,
                   is_required=is_required, is_present=is_present)

    def __init__(self, table_label, label, target_table_label=None,
                 is_required=None, is_present=True):
        assert isinstance(table_label, unicode) and len(table_label) > 0
        assert isinstance(label, unicode) and len(label) > 0
        assert isinstance(is_present, bool)
        if is_present:
            assert (isinstance(target_table_label, unicode)
                    and len(target_table_label) > 0)
            assert isinstance(is_required, bool)
        else:
            assert target_table_label is None
            assert is_required is None
        self.table_label = table_label
        self.label = label
        self.target_table_label = target_table_label
        self.is_required = is_required
        self.is_present = is_present
        self.table_name = mangle(table_label)
        self.name = mangle(label, u'id')
        if is_present:
            self.target_table_name = mangle(target_table_label)
            self.constraint_name = mangle([table_label, label], u'fk')
        else:
            self.target_table_name = None
            self.constraint_name = None

    def __repr__(self):
        args = []
        args.append(repr(self.table_label))
        args.append(repr(self.label))
        if self.target_table_label is not None:
            args.append(repr(self.target_table_label))
        if self.is_required is not None:
            args.append("is_required=%r" % self.is_required)
        if not self.is_present:
            args.append("is_present=%r" % self.is_present)
        return "%s(%s)" % (self.__class__.__name__, ", ".join(args))

    def __call__(self, driver):
        if self.is_present:
            return self.create(driver)
        else:
            return self.drop(driver)

    def create(self, driver):
        # Ensures that the link is present.
        schema = driver.get_schema()
        if self.table_name not in schema:
            raise Error("Detected missing table:", self.table_name)
        table = schema[self.table_name]
        if self.target_table_name not in schema:
            raise Error("Detected missing table:", self.target_table_name)
        target_table = schema[self.target_table_name]
        if u'id' not in target_table:
            raise Error("Detected missing column:", "id")
        target_column = target_table[u'id']
        # Create the link column if it does not exist.
        # FIXME: check if a non-link column with the same label exists?
        if self.name not in table:
            if driver.is_locked:
                raise Error("Detected missing column:", self.name)
            driver.submit(sql_add_column(
                    self.table_name, self.name, target_column.type.name,
                    self.is_required))
            table.add_column(self.name, target_column.type, self.is_required)
        column = table[self.name]
        # Verify the column type and `NOT NULL` constraint.
        if column.type != target_column.type:
            raise Error("Detected column with mismatched type:", column)
        if column.is_not_null != self.is_required:
            raise Error("Detected column with mismatched"
                        " NOT NULL constraint:", column)
        # Create a `FOREIGN KEY` constraint if necessary.
        if not any(foreign_key
                   for foreign_key in table.foreign_keys
                   if list(foreign_key) == [(column, target_column)]):
            if driver.is_locked:
                raise Error("Detected column with missing"
                            " FOREIGN KEY constraint:", column)
            driver.submit(sql_add_foreign_key_constraint(
                    self.table_name, self.constraint_name, [self.name],
                    self.target_table_name, [u'id']))
            table.add_foreign_key(self.constraint_name, [column],
                                  target_table, [target_column])

    def drop(self, driver):
        # Ensures that the link is absent.
        schema = driver.get_schema()
        if self.table_name not in schema:
            return
        table = schema[self.table_name]
        if self.name not in table:
            return
        column = table[self.name]
        if driver.is_locked:
            raise Error("Detected unexpected column:", column)
        # Drop the link.
        driver.submit(sql_drop_column(self.table_name, self.name))
        column.remove()


