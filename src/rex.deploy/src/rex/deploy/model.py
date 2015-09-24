#
# Copyright (c) 2013, Prometheus Research, LLC
#


from rex.core import Record, Error, Extension, LatentRex, get_rex
from .fact import Fact, FactVal, LabelVal, TitleVal, label_to_title
from .meta import uncomment
from .sql import (mangle, sql_value, sql_name, sql_cast,
        plpgsql_primary_key_procedure, plpgsql_integer_random_key,
        plpgsql_text_random_key, plpgsql_integer_offset_key,
        plpgsql_text_offset_key)
from .image import (TableImage, ColumnImage, UniqueKeyImage, CASCADE,
        SET_DEFAULT, BEFORE, INSERT)
import datetime
import weakref
import json
from htsql.core.domain import (UntypedDomain, BooleanDomain, IntegerDomain,
        DecimalDomain, FloatDomain, TextDomain, DateDomain, TimeDomain,
        DateTimeDomain, EnumDomain)
from htsql_rex_deploy.domain import JSONDomain


class Signal(object):
    # Notifies a dependent about a change in the master.

    __slot__ = ('before', 'after', 'modify', 'erase',
                'before_modify', 'before_erase', 'after_modify', 'after_erase')

    def __init__(self, before=False, after=False, modify=False, erase=False):
        assert before != after
        assert modify != erase
        self.before = before
        self.after = after
        self.modify = modify
        self.erase = erase
        self.before_modify = before and modify
        self.before_erase = before and erase
        self.after_modify = after and modify
        self.after_erase = after and erase


class Model(Extension):
    # Represents high-level entities: tables, fields, identities.

    __slots__ = ('owner', 'image')

    properties = None
    is_table = False
    is_column = False
    is_link = False
    is_identity = False
    is_constraint = False

    @classmethod
    def sanitize(cls):
        # Generates a `State` record class from `properties`.
        if cls.__dict__.get('properties'):
            cls.State = Record.make(None, cls.properties)

    @classmethod
    def enabled(cls):
        return (cls.properties is not None)

    @classmethod
    def all(cls):
        if not get_rex:
            # Allow it to work even when there is no active Rex application.
            with LatentRex('rex.deploy'):
                return super(Model, cls).all()
        else:
            return super(Model, cls).all()

    def __init__(self, schema, image):
        self.owner = weakref.ref(schema)
        self.image = image
        schema.attach(self)

    def __nonzero__(self):
        # Is the entity still alive?
        return hasattr(self, 'image')

    @property
    def schema(self):
        # The schema model.
        return self.owner()

    def state(self):
        # The current set of properties.
        return self.State(**dict((property, getattr(self, property))
                                 for property in self.properties))

    def dependents(self):
        # Entities that gets deleted when this object is deleted.
        return []

    def modify(self, **kwds):
        # Alters the entity state.
        old = self.state()
        new = old.__clone__(**kwds)
        # Notify the dependent entities.
        dependents = self.dependents()
        signal = Signal(before=True, modify=True)
        for dependent in dependents:
            if dependent:
                dependent.do_react(self, signal, old, new)
        # Update the object.
        self.do_modify(**vars(new))
        for key, value in kwds.items():
            setattr(self, key, value)
        # Notify the dependent entities after update.
        signal = Signal(after=True, modify=True)
        for dependent in dependents:
            if dependent:
                dependent.do_react(self, signal, old, new)

    def erase(self):
        # Removes the entity.
        old = self.state()
        # Notify the dependent objects.
        dependents = self.dependents()
        signal = Signal(before=True, erase=True)
        for dependent in dependents:
            if dependent:
                dependent.do_react(self, signal, old, None)
        # Kill the entity.
        self.do_erase()
        self.remove()
        # Notify and kill the dependent entities.
        signal = Signal(after=True, erase=True)
        for dependent in dependents:
            if dependent:
                dependent.do_react(self, signal, old, None)

    def remove(self):
        # Kills the entity.
        self.schema.detach(self)
        # Destroy all fields to make sure the object is never used again.
        for cls in self.__class__.__mro__:
            if hasattr(cls, '__slots__'):
                for slot in cls.__slots__:
                    if not (slot.startswith('__') and slot.endswith('__')):
                        delattr(self, slot)

    @classmethod
    def recognizes(self, schema, image):
        raise NotImplementedError()

    def do_modify(self, **kwds):
        raise NotImplementedError()

    def do_erase(self):
        raise NotImplementedError()

    def do_react(self, master, signal, old, new):
        raise NotImplementedError()


class ModelSchema(object):

    __slots__ = (
            'driver', 'image', 'system_image', 'image_to_entity',
            '__weakref__')

    def __init__(self, driver):
        # Catalog and database connection.
        self.driver = driver
        # The `public` schema.
        self.image = driver.get_schema()
        # The `pg_catalog` schema.
        self.system_image = driver.get_system_schema()
        # Maps database objects to entities.
        self.image_to_entity = {}

    def attach(self, entity):
        # Associates a database object with an entity.
        self.image_to_entity[entity.image] = entity

    def detach(self, entity):
        # Breaks association between a database object and an entity.
        del self.image_to_entity[entity.image]

    def __call__(self, image):
        # Returns an entity associated with a database object.
        try:
            return self.image_to_entity[image]
        except KeyError:
            pass
        if image is None:
            return None
        # Check if any of the entities recognizes the database object.
        candidates = []
        for ModelClass in Model.all():
            if ModelClass.recognizes(self, image):
                candidates = [Candidate
                              for Candidate in candidates
                              if not issubclass(Candidate, ModelClass)]
                if not any([issubclass(ModelClass, Candidate)
                            for Candidate in candidates]):
                    candidates.append(ModelClass)
        assert len(candidates) <= 1
        if candidates:
            [ModelClass] = candidates
            return ModelClass(self, image)

    def tables(self):
        tables = []
        for table_image in self.image.tables:
            if u'id' not in table_image:
                continue
            table = self(table_image)
            if table:
                tables.append(table)
        return tables

    def table(self, label):
        return TableModel.find(self, label)

    def build_table(self, **kwds):
        return TableModel.do_build(self, **kwds)


class ConstraintModel(Model):
    # Wraps some constraint on the database.

    __slots__ = ()

    is_constraint = True


class TableModel(Model):
    # Wraps a database table.

    __slots__ = (
            'id_image', 'uk_image', 'seq_image',
            'label', 'is_reliable', 'title')

    is_table = True

    properties = ['label', 'is_reliable', 'title']

    class names(object):
        # Derives names for database objects and the table title.

        __slots__ = ('label', 'title', 'name', 'uk_name', 'seq_name')

        def __init__(self, label):
            self.label = label
            self.title = label_to_title(label)
            self.name = mangle(label)
            self.uk_name = mangle(label, u'uk')
            self.seq_name = mangle(label, u'seq')

    @classmethod
    def recognizes(cls, schema, image):
        # Verifies if the database object is a table.
        if not isinstance(image, TableImage):
            return False
        # We expect the table belongs to the `public` schema.
        if image.schema is not schema.image:
            return False
        return True

    @classmethod
    def find(cls, schema, label):
        # Finds a table by name.
        names = cls.names(label)
        image = schema.image.tables.get(names.name)
        return schema(image)

    @classmethod
    def do_build(cls, schema, label, is_reliable=True, title=None):
        # Builds a table.
        # Create a table with `id int4` column.
        names = cls.names(label)
        int4_image = schema.system_image.types[u'int4']
        definitions = [(u'id', int4_image, True, None)]
        is_unlogged = (not is_reliable)
        image = schema.image.create_table(
                names.name, definitions, is_unlogged=is_unlogged)
        id_image = image[u'id']
        # Create a sequence on the `id` column.
        schema.image.create_sequence(names.seq_name, id_image)
        # Create a surrogate key constraint.
        image.create_unique_key(names.uk_name, [id_image])
        # Save the label and the title if necessary.
        saved_label = label if label != names.name else None
        saved_title = title if title != names.title else None
        meta = uncomment(image)
        if meta.update(label=saved_label, title=saved_title):
            image.alter_comment(meta.dump())
        return cls(schema, image)

    def __init__(self, schema, image):
        super(TableModel, self).__init__(schema, image)
        assert isinstance(image, TableImage)
        # Extract entity properties.
        meta = uncomment(image)
        self.label = meta.label or image.name
        self.is_reliable = (not image.is_unlogged)
        self.title = meta.title
        if not (u'id' in image and image[u'id'].unique_keys):
            raise Error("Discovered table without surrogate key:", self.label)
        # Surrogate key column.
        self.id_image = image[u'id']
        # Surrogate key constraint.
        self.uk_image = next(iter(self.id_image.unique_keys))
        # Sequence on the `id` column.
        self.seq_image = next(iter(self.id_image.sequences), None)

    def do_modify(self, label, is_reliable, title):
        # Updates the state of the table entity.
        # Refresh names.
        names = self.names(label)
        self.image.alter_name(names.name)
        if self.seq_image:
            self.seq_image.alter_name(names.seq_name)
        if self.uk_image:
            self.uk_image.alter_name(names.uk_name)
        # Cannot change the `UNLOGGED` mode.
        if self.is_reliable != is_reliable:
            raise Error("Discovered table with mismatched"
                        " reliability mode:", label)
        # Update saved label and title.
        meta = uncomment(self.image)
        saved_label = label if label != names.name else None
        saved_title = title if title != names.title else None
        if meta.update(label=saved_label, title=saved_title):
            self.image.alter_comment(meta.dump())

    def do_erase(self):
        # Drops the entity.
        if self.image:
            self.image.drop()

    def fields(self):
        # List of columns and links.
        fields = []
        for column_image in self.image.columns:
            field = self.schema(column_image)
            if field:
                fields.append(field)
        return fields

    def identity(self):
        # Table identity.
        return self.schema(self.image.primary_key)

    def constraints(self, ModelClass=None):
        constraints = []
        for trigger_image in self.image.triggers:
            if trigger_image.comment is not None:
                constraint = self.schema(trigger_image)
                if ModelClass is None or isinstance(constraint, ModelClass):
                    constraints.append(constraint)
        return constraints

    def constraint(self, ModelClass):
        constraints = self.constraints(ModelClass)
        return constraints[0] if constraints else None

    def dependents(self):
        # List of dependent entities.
        dependents = []
        # Links referring to the table.
        for foreign_key_image in self.image.referring_foreign_keys:
            if foreign_key_image.origin is not foreign_key_image.target:
                for column_image in foreign_key_image.origin_columns:
                    field = self.schema(column_image)
                    if field:
                        dependents.append(field)
        # Columns and links.
        for column_image in self.image.columns:
            field = self.schema(column_image)
            if field:
                dependents.append(field)
        # The identity.
        identity = self.schema(self.image.primary_key)
        if identity:
            dependents.append(identity)
        # Constraints.
        for trigger_image in self.image.triggers:
            if trigger_image.comment is not None:
                constraint = self.schema(trigger_image)
                if constraint:
                    dependents.append(constraint)
        return dependents

    def column(self, label):
        # Column by name.
        return ColumnModel.find(self, label)

    def link(self, label):
        # Link by name.
        return LinkModel.find(self, label)

    def build_column(self, **kwds):
        # Creates a new column.
        return ColumnModel.do_build(self, **kwds)

    def build_link(self, **kwds):
        # Creates a new link.
        return LinkModel.do_build(self, **kwds)

    def build_identity(self, **kwds):
        # Creates table identity.
        return IdentityModel.do_build(self, **kwds)

    def move_after(self, field, other_fields):
        # Move a field after the given set of fields.
        position = field.image.position
        for other_field in other_fields:
            if other_field.image.position > position:
                field.image.alter_position(len(field.image.table.columns)-1)
                break


class ColumnModel(Model):
    # Wraps a database column.

    __slots__ = (
            'uk_image', 'enum_image',
            'table', 'label', 'type', 'default',
            'is_required', 'is_unique', 'title')

    is_column = True

    properties = [
            'table', 'label', 'type', 'default',
            'is_required', 'is_unique', 'title']

    class names(object):
        # Derives name for the column and auxiliary objects.

        __slots__ = (
                'table_label', 'label', 'title',
                'name', 'enum_name', 'uk_name')

        def __init__(self, table_label, label):
            self.table_label = table_label
            self.label = label
            self.title = label_to_title(label)
            self.name = mangle(label)
            self.enum_name = mangle([table_label, label], u'enum')
            self.uk_name = mangle([table_label, label], u'uk')

    class data(object):
        # Derives auxiliary objects associated with the type and default value.

        __slots__ = ('type', 'name', 'enumerators',
                     'domain', 'default', 'value')

        # HTSQL name -> SQL name.
        TYPE_MAP = {
                u"boolean": u"bool",
                u"integer": u"int4",
                u"decimal": u"numeric",
                u"float": u"float8",
                u"text": u"text",
                u"date": u"date",
                u"time": u"time",
                u"datetime": u"timestamp",
                u"json": u"json",
        }

        # SQL type name -> HTSQL name.
        REVERSE_TYPE_MAP = dict((sql_name, htsql_name)
                                for htsql_name, sql_name in TYPE_MAP.items())

        # HTSQL name -> HTSQL domain.
        DOMAIN_MAP = {
                u'boolean': BooleanDomain(),
                u'integer': IntegerDomain(),
                u'decimal': DecimalDomain(),
                u'float': FloatDomain(),
                u'text': TextDomain(),
                u'date': DateDomain(),
                u'time': TimeDomain(),
                u'datetime': DateTimeDomain(),
                u'json': JSONDomain(),
        }

        # Special `default` values.
        VALUE_MAP = {
                "today()": datetime.date.today,
                "now()": datetime.datetime.now,
        }

        # Valid type conversions.
        CAST_MAP = {
            u'boolean': set([u'integer', u'text']),
            u'integer': set([u'boolean', u'decimal', u'float', u'text']),
            u'decimal': set([u'integer', u'float', u'text']),
            u'float': set([u'integer', u'decimal', u'text']),
            u'text': set([u'boolean', u'integer', u'decimal', u'float',
                          u'date', u'time', u'datetime', u'json']),
            u'date': set([u'text', u'datetime']),
            u'time': set([u'text']),
            u'datetime': set([u'text', u'date', u'time']),
            u'json': set([u'text']),
        }

        def __init__(self, type, default):
            self.type = type
            if isinstance(type, list):
                self.name = None
                self.enumerators = type
                self.domain = EnumDomain(type)
            else:
                self.name = self.TYPE_MAP[type]
                self.enumerators = None
                self.domain = self.DOMAIN_MAP[type]
            # Normalize the default value as a string (or `None`).
            if isinstance(default, str):
                default = default.decode('utf-8', 'replace')
            if not isinstance(default, unicode):
                default = self.domain.dump(default)
            self.default = default
            # Default value serialized in SQL.
            value = default
            try:
                value = self.domain.parse(default)
            except ValueError:
                pass
            if type != u'text' and isinstance(value, (str, unicode)):
                value = self.VALUE_MAP.get(value, value)
            if type == u'json' and value is not None:
                value = json.dumps(value, sort_keys=True)
            if value is not None:
                value = sql_value(value)
            self.value = value

    @classmethod
    def recognizes(cls, schema, image):
        # Verifies if a database object forms a valid column entity.
        # We expect a column without foreign keys.
        if not isinstance(image, ColumnImage) or image.foreign_keys:
            return False
        # Skip the surrogate key.
        if image.name == u'id':
            return False
        # The table must be valid too.
        if not TableModel.recognizes(schema, image.table):
            return False
        return True

    @classmethod
    def find(cls, table, label):
        # Finds a column by name.
        schema = table.schema
        names = cls.names(table.label, label)
        image = table.image.columns.get(names.name)
        if cls.recognizes(schema, image):
            return schema(image)

    @classmethod
    def do_build(cls, table, label, type, default=None,
                 is_required=True, is_unique=False, title=None):
        # Creates a new column with the given properties.
        schema = table.schema
        names = cls.names(table.label, label)
        data = cls.data(type, default)
        # Determine the column type, create an ENUM type if necessary.
        if data.enumerators is not None:
            type_image = schema.image.create_enum_type(
                    names.enum_name, data.enumerators)
        else:
            type_image = schema.system_image.types[data.name]
        # Create the column.
        image = table.image.create_column(
                names.name, type_image, is_required, data.value)
        # Create the `UNIQUE` constraint.
        if is_unique:
            table.image.create_unique_key(
                    names.uk_name, [image], False)
        # Save the original label, title and default value.
        meta = uncomment(image)
        saved_label = label if label != names.name else None
        saved_title = title if title != names.title else None
        saved_default = data.default
        if meta.update(label=saved_label, title=saved_title,
                       default=saved_default):
            image.alter_comment(meta.dump())
        return cls(schema, image)

    def __init__(self, schema, image):
        super(ColumnModel, self).__init__(schema, image)
        # Extract entity properties.
        self.table = schema(image.table)
        assert self.table is not None
        meta = uncomment(image)
        self.label = meta.label or image.name
        # Reconstruct the column type and the default value.
        if not ((image.type.is_enum and image.type.schema is schema.image) or
                (image.type.name in self.data.REVERSE_TYPE_MAP and
                    image.type.schema is schema.system_image)):
            raise Error("Discovered column of unrecognized type:", self.label)
        if image.type.is_enum:
            self.type = image.type.labels
            self.enum_image = image.type
        else:
            self.type = self.data.REVERSE_TYPE_MAP[image.type.name]
            self.enum_image = None
        data = self.data(self.type, meta.default)
        self.default = data.default
        try:
            self.default = data.domain.parse(self.default)
        except ValueError:
            pass
        self.is_required = image.is_not_null
        self.is_unique = (len(image.unique_keys) > 0)
        self.uk_image = next(iter(image.unique_keys), None)
        self.title = meta.title

    def do_modify(self, table, label, type, default,
                  is_required, is_unique, title):
        # Updates the state of the column entity.
        assert table is self.table
        names = self.names(table.label, label)
        # Refresh names.
        self.image.alter_name(names.name)
        if self.enum_image:
            self.enum_image.alter_name(names.enum_name)
        if self.uk_image:
            self.uk_image.alter_name(names.uk_name)
        # Update the type and the default value.
        meta = uncomment(self.image)
        data = self.data(type, default)
        if type != self.type:
            self._convert(names, data)
            #raise Error("Discovered column with mismatched type:", label)
        else:
            if data.default != meta.default:
                self.image.alter_default(data.value)
        # Update other constraints.
        self.image.alter_is_not_null(is_required)
        if is_unique and not self.uk_image:
            self.uk_image = table.image.create_unique_key(
                    names.uk_name, [self.image], False)
        elif not is_unique and self.uk_image:
            self.uk_image.drop()
        # Save the label, the title and the default value.
        saved_label = label if label != names.name else None
        saved_title = title if title != names.title else None
        saved_default = data.default
        if meta.update(label=saved_label, title=saved_title,
                       default=saved_default):
            self.image.alter_comment(meta.dump())

    def _convert(self, names, data):
        # Converts the column data type.
        schema = self.table.schema
        old_data = self.data(self.type, self.default)
        has_cast = False
        if old_data.enumerators is None and data.enumerators is None:
            has_cast = (data.type in old_data.CAST_MAP[old_data.type])
        elif old_data.enumerators is None:
            has_cast = (old_data.type == u'text')
        elif data.enumerators is None:
            has_cast = (data.type == u'text')
        else:
            has_cast = True
        if not has_cast:
            raise Error("Cannot convert column of type %s to %s:"
                        % (old_data.domain, data.domain), names.label)
        self.image.alter_default(None)
        if old_data.enumerators is None and data.enumerators is None:
            type_image = self.table.schema.system_image.types[data.name]
            expression = sql_cast(sql_name(self.image.name), type_image.name)
            self.image.alter_type(type_image, expression)
        elif old_data.enumerators is None:
            self.enum_image = self.table.schema.image.create_enum_type(
                    names.enum_name, data.enumerators)
            expression = sql_cast(sql_name(self.image.name), names.enum_name)
            self.image.alter_type(self.enum_image, expression)
        elif data.enumerators is None:
            type_image = schema.system_image.types[data.name]
            expression = sql_cast(sql_name(self.image.name), type_image.name)
            self.image.alter_type(type_image, expression)
            self.enum_image.drop()
        else:
            new_enum_image = schema.image.create_enum_type(
                    u"?", data.enumerators)
            expression = sql_cast(
                    sql_cast(sql_name(self.image.name), u"text"), u"?")
            self.image.alter_type(new_enum_image, expression)
            self.enum_image.drop()
            self.enum_image = new_enum_image
            self.enum_image.alter_name(names.enum_name)
        self.image.alter_default(data.value)

    def do_erase(self):
        # Deletes the column and auxiliary objects.
        if self.image:
            self.image.drop()
        if self.enum_image:
            self.enum_image.drop()

    def do_react(self, master, signal, old, new):
        # Reacts on changes of the parent table.
        assert master is self.table
        # After the table is renamed, refresh the names.
        if signal.after_modify and old.label != new.label:
            names = self.names(new.label, self.label)
            if self.enum_image:
                self.enum_image.alter_name(names.enum_name)
            if self.uk_image:
                self.uk_image.alter_name(names.uk_name)
        # After the table is deleted, delete the `ENUM` type.
        if signal.after_erase:
            if self.enum_image:
                self.enum_image.drop()
            self.remove()

    def dependents(self):
        # Column dependencies.
        dependents = []
        # The table identity if the column belongs to the primary key.
        if self.image in (self.image.table.primary_key or []):
            identity = self.schema(self.image.table.primary_key)
            if identity:
                dependents.append(identity)
        # Also add all table constraints.
        for trigger_image in self.image.table.triggers:
            if trigger_image.comment is not None:
                constraint = self.schema(trigger_image)
                if constraint:
                    dependents.append(constraint)
        return dependents


class LinkModel(Model):
    # Represents a column with a foreign key constraint.

    __slots__ = (
            'fk_image', 'uk_image', 'index_image',
            'table', 'label', 'target_table',
            'is_required', 'is_unique', 'title')

    is_link = True

    properties = [
            'table', 'label', 'target_table',
            'is_required', 'is_unique', 'title']

    class names(object):
        # Derives name for the column and auxiliary objects.

        __slots__ = ('table_label', 'label', 'title',
                     'name', 'fk_name', 'uk_name')

        def __init__(self, table_label, label):
            self.table_label = table_label
            self.label = label
            self.title = label_to_title(label)
            self.name = mangle(label, u'id')
            self.fk_name = mangle([table_label, label], u'fk')
            self.uk_name = mangle([table_label, label], u'uk')

    @staticmethod
    def name_to_label(name):
        # Derives the link label from the column name.
        if name.endswith(u'_id'):
            name = name[:-2].rstrip(u'_')
        return name

    @classmethod
    def recognizes(cls, schema, image):
        # Verifies if a database object forms a valid link entity.
        # We expect a column with a foreign key.
        if not (isinstance(image, ColumnImage) and image.foreign_keys):
            return False
        # Skip the surrogate key.
        if image.name == u'id':
            return False
        # The table must be valid too.
        if not TableModel.recognizes(schema, image.table):
            return False
        return True

    @classmethod
    def find(cls, table, label):
        # Finds a link by name.
        schema = table.schema
        names = cls.names(table.label, label)
        image = table.image.columns.get(names.name)
        if cls.recognizes(schema, image):
            return schema(image)

    @classmethod
    def do_build(cls, table, label, target_table,
                 is_required=True, is_unique=False, title=None):
        # Creates a new link with the given properties.
        schema = table.schema
        names = cls.names(table.label, label)
        # Create the column and the foreign key constraint.
        type_image = target_table.id_image.type
        image = table.image.create_column(
                names.name, type_image, is_required)
        table.image.create_foreign_key(
                names.fk_name, [image],
                target_table.image, [target_table.id_image],
                on_delete=SET_DEFAULT)
        # Create a `UNIQUE` constraint or an index.
        if is_unique:
            table.image.create_unique_key(
                    names.uk_name, [image], False)
        else:
            schema.image.create_index(
                    names.fk_name, table.image, [image])
        # Save the original label and title.
        meta = uncomment(image)
        saved_label = label if label != cls.name_to_label(names.name) else None
        saved_title = title if title != names.title else None
        if meta.update(label=saved_label, title=saved_title):
            image.alter_comment(meta.dump())
        return cls(schema, image)

    def __init__(self, schema, image):
        super(LinkModel, self).__init__(schema, image)
        # Extract link properties.
        self.table = schema(image.table)
        assert self.table is not None
        meta = uncomment(image)
        self.label = meta.label or self.name_to_label(image.name)
        self.fk_image = next(iter(image.foreign_keys))
        self.index_image = schema.image.indexes.get(self.fk_image.name)
        self.target_table = schema(self.fk_image.target)
        if not self.target_table:
            raise Error("Discovered link with unrecognized target:", self.label)
        self.is_required = image.is_not_null
        self.is_unique = (len(image.unique_keys) > 0)
        self.uk_image = next(iter(image.unique_keys), None)
        self.title = meta.title

    def do_modify(self, table, label, target_table,
                  is_required, is_unique, title):
        # Updates the state of the link entity.
        assert table is self.table
        if target_table is not self.target_table:
            raise Error("Discovered link with mismatched target:", label)
        # Refresh names.
        names = self.names(table.label, label)
        self.image.alter_name(names.name)
        self.fk_image.alter_name(names.fk_name)
        if self.index_image:
            self.index_image.alter_name(names.fk_name)
        if self.uk_image:
            self.uk_image.alter_name(names.uk_name)
        # Update other constraints.
        self.image.alter_is_not_null(is_required)
        if is_unique:
            if self.index_image:
                self.index_image.drop()
            if not self.uk_image:
                self.uk_image = table.image.create_unique_key(
                        names.uk_name, [self.image], False)
        else:
            if self.uk_image:
                self.uk_image.drop()
            if not self.index_image:
                self.index_image = table.schema.image.create_index(
                        names.fk_name, table.image, [self.image])
        # Save the label and the title.
        meta = uncomment(self.image)
        saved_label = label if label != self.name_to_label(names.name) else None
        saved_title = title if title != names.title else None
        if meta.update(label=saved_label, title=saved_title):
            self.image.alter_comment(meta.dump())

    def do_erase(self):
        # Delete the link.
        if self.image:
            self.image.drop()

    def do_react(self, master, signal, old, new):
        # Reacts on changes of the origin and target tables.
        if master is self.target_table:
            # When the target table is about to be deleted, delete the link.
            if master is not self.table and signal.before_erase:
                self.erase()
                return
            # When the target is renamed and the target name coincides with
            # the link name, rename the link.
            if signal.after_modify and self.label == old.label != new.label:
                self.modify(label=new.label)
        if master is self.table:
            # After the table is renamed, refresh the names.
            if signal.after_modify and old.label != new.label:
                names = self.names(new.label, self.label)
                if self.fk_image:
                    self.fk_image.alter_name(names.fk_name)
                if self.index_image:
                    self.index_image.alter_name(names.fk_name)
                if self.uk_image:
                    self.uk_image.alter_name(names.uk_name)
        if signal.after_erase:
            self.remove()

    def dependents(self):
        # Entities that depend on the link.
        dependents = []
        # Add the identity if the link belongs to it.
        if self.image in (self.image.table.primary_key or []):
            identity = self.schema(self.image.table.primary_key)
            if identity:
                dependents.append(identity)
        # Also add all table constraints.
        for trigger_image in self.image.table.triggers:
            if trigger_image.comment is not None:
                constraint = self.schema(trigger_image)
                if constraint:
                    dependents.append(constraint)
        return dependents


class IdentityModel(Model):
    # Wraps the primary key.

    __slots__ = (
            'trigger_image', 'procedure_image',
            'table', 'fields', 'generators')

    is_identity = True

    properties = ['table', 'fields', 'generators']

    class names(object):
        # Derives name for the constraint and auxiliary objects.

        __slots__ = ('label', 'name')

        def __init__(self, label):
            self.label = label
            self.name = mangle(label, u'pk')

    @classmethod
    def recognizes(cls, schema, image):
        # Verifies if a database object is a valid identity.
        if not (isinstance(image, UniqueKeyImage) and image.is_primary):
            return False
        if not TableModel.recognizes(schema, image.origin):
            return False
        return True

    @classmethod
    def do_build(cls, table, fields, generators=None):
        # Creates the table identity from the given fields.
        if generators is None:
            generators = [None]*len(fields)
        # All fields must be NOT NULL constraint.
        for field in fields:
            if not field.is_required:
                raise Error("Discovered nullable field:", field.label)
        # Create the `PRIMARY KEY` constraint.
        schema = table.schema
        names = cls.names(table.label)
        image = table.image.create_primary_key(
                names.name, [field.image for field in fields])
        # For identity links, set `ON DELETE CASCADE`.
        for field in fields:
            for fk_image in field.image.foreign_keys:
                fk_image.alter_on_delete(CASCADE)
        # Build the generator trigger.
        source = cls._generate(table.image, generators)
        if source:
            type_image = schema.system_image.types[u'trigger']
            procedure_image = schema.image.create_procedure(
                    names.name, [], type_image, source)
            trigger_image = table.image.create_trigger(
                    names.name, BEFORE, INSERT,
                    procedure_image, [])
            meta = uncomment(image)
            meta.update(generators=generators)
            image.alter_comment(meta.dump())
        return cls(schema, image)

    def __init__(self, schema, image):
        super(IdentityModel, self).__init__(schema, image)
        # Extract entity properties.
        self.table = schema(image.origin)
        assert self.table is not None
        self.fields = [schema(column_image)
                       for column_image in image.origin_columns]
        self.trigger_image = image.origin.triggers.get(image.name)
        self.procedure_image = None
        if self.trigger_image:
            self.procedure_image = self.trigger_image.procedure
        meta = uncomment(image)
        self.generators = meta.generators or [None]*len(self.fields)

    def do_modify(self, table, fields, generators):
        # Updates the identity properties.
        if generators is None:
            generators = [None]*len(fields)
        schema = self.table.schema
        assert table is self.table
        names = self.names(self.table.label)
        # Rebuild the constraint with new columns.
        if self.fields != fields:
            # For links that no longer belong to the identity,
            # set `ON DELETE SET DEFAULT`.
            for field in self.fields:
                if field in fields:
                    continue
                for fk_image in field.image.foreign_keys:
                    fk_image.alter_on_delete(SET_DEFAULT)
            # Make sure all fields have `NOT NULL` constraint.
            for field in fields:
                if not field.is_required:
                    raise Error("Discovered nullable field:", field.label)
            # Rebuild the constraint.
            self.image.drop()
            self.image = table.image.create_primary_key(
                    names.name, [field.image for field in fields])
            # For all identity links, set `ON DELETE CASCADE`.
            for field in fields:
                for fk_image in field.image.foreign_keys:
                    fk_image.alter_on_delete(CASCADE)
        # Rebuild or drop the trigger if necessary.
        source = self._generate(table.image, generators)
        if source:
            if not self.procedure_image:
                type_image = schema.system_image.types[u'trigger']
                self.procedure_image = schema.image.create_procedure(
                        names.name, [], type_image, source)
            else:
                self.procedure_image.alter_source(source)
            if not self.trigger_image:
                trigger_image = table.image.create_trigger(
                        names.name, BEFORE, INSERT,
                        self.procedure_image, [])
        else:
            if self.trigger_image:
                self.trigger_image.drop()
            if self.procedure_image:
                self.procedure_image.drop()
        meta = uncomment(self.image)
        if not any(generator is not None for generator in generators):
            generators = None
        if meta.update(generators=generators):
            self.image.alter_comment(meta.dump())

    def do_erase(self):
        # Deletes the identity.
        # Drop the constraint and the trigger.
        if self.image:
            self.image.drop()
        if self.trigger_image:
            self.trigger_image.drop()
        if self.procedure_image:
            self.procedure_image.drop()
        # For links, set `ON DELETE SET DEFAULT`.
        for field in self.fields:
            if field and field.image:
                for fk_image in field.image.foreign_keys:
                    fk_image.alter_on_delete(SET_DEFAULT)

    def do_react(self, master, signal, old, new):
        # Reacts on changes in the master table or one of the identity fields.
        # When a column loses `NOT NULL` constraint, delete the identity.
        if master in self.fields:
            if signal.before_modify and not new.is_required:
                self.erase()
                return
        # If any name changes, see if we need to rename the constraint
        # and rebuild the trigger.
        if signal.after_modify and old.label != new.label:
            names = self.names(self.table.label)
            self.image.alter_name(names.name)
            if self.procedure_image:
                self.procedure_image.alter_name(names.name)
            if self.trigger_image:
                self.trigger_image.alter_name(names.name)
            source = self._generate(self.table.image, self.generators)
            if source:
                self.procedure_image.alter_source(source)
        # If a generated column changed its type, drop the generator.
        if (signal.after_modify and master in self.fields and
                master.is_column and old.type != new.type):
            index = self.fields.index(master)
            if self.generators[index] is not None:
                self.modify(generators=None)

        # After the constraint is delete, clear the trigger and the procedure.
        if signal.after_erase:
            if self.trigger_image:
                self.trigger_image.drop()
            if self.procedure_image:
                self.procedure_image.drop()
            self.remove()

    @classmethod
    def _make_offset_key(cls, table, column):
        # Builds code for autogenerated offset primary key.
        basis_columns = table.primary_key.origin_columns
        index = basis_columns.index(column)
        basis_columns = basis_columns[:index]
        basis_names = [basis_column.name for basis_column in basis_columns]
        is_link = len(column.foreign_keys) > 0
        type_qname = (column.type.schema.name, column.type.name)
        if type_qname == (u'pg_catalog', u'int4') and not is_link:
            return plpgsql_integer_offset_key(
                    table.name, column.name, basis_names)
        elif type_qname == (u'pg_catalog', u'text') and not is_link:
            return plpgsql_text_offset_key(
                    table.name, column.name, basis_names)
        else:
            raise Error("Expected an integer or text column:", column)

    @classmethod
    def _make_random_key(cls, table, column):
        # Builds code for autogenerated random primary key.
        is_link = len(column.foreign_keys) > 0
        type_qname = (column.type.schema.name, column.type.name)
        if type_qname == (u'pg_catalog', u'int4') and not is_link:
            return plpgsql_integer_random_key(table.name, column.name)
        elif type_qname == (u'pg_catalog', u'text') and not is_link:
            return plpgsql_text_random_key(table.name, column.name)
        else:
            raise Error("Expected an integer or text column:", column)

    @classmethod
    def _generate(cls, table, generators):
        # Builds stored procedure for autogenerated identity.
        source = []
        for column, generator in zip(table.primary_key, generators):
            if generator == u'offset':
                source.append(cls._make_offset_key(table, column))
            elif generator == u'random':
                source.append(cls._make_random_key(table, column))
        if not source:
            return None
        return plpgsql_primary_key_procedure(*source)


def model(driver):
    return ModelSchema(driver)


