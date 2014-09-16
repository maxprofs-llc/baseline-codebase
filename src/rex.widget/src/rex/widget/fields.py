"""

    rex.widget.state.fields
    =======================

    :copyright: 2014, Prometheus Research, LLC

"""

import functools
import urlparse
from collections import namedtuple
from rex.core import (
    Validate, Error,
    MaybeVal, MapVal, SeqVal, OneOfVal, BoolVal, StrVal, IntVal,
    RecordVal, RecordField)
from .state import State, Dep, Reference, unknown
from .computator import (
    InitialValue,
    EntityComputator, CollectionComputator, PaginatedCollectionComputator)
from .logging import getLogger
from .util import cached_property


class Field(object):
    """ Widget field definition.

    :param validator: Validator
    :keyword default: Default value
    :keyword name: Name of the field
    """

    # we maintain order as a global counter which is used to assign ordering to
    # field instances
    order = 0

    def __new__(cls, *args, **kwargs):
        # increment global counter
        cls.order += 1
        self = object.__new__(cls, *args, **kwargs)
        # assign current order value on an instance to define ordering between
        # all Field instances
        self.order = cls.order
        return self

    def __init__(self, validator, default=NotImplemented, name=None):
        if isinstance(validator, type):
            validator = validator()
        self.validator = validator
        self.default = default
        # name will be defined by Widget metaclass
        self.name = name

        # TODO: remove lines below after state refactor
        if hasattr(validator, 'default'):
            self.default = validator.default

    def __get__(self, widget, widget_cls):
        if widget is None:
            return self
        return widget.values[self.name]

    @cached_property
    def record_field(self):
        """ Create record field validator.

        This is used to construct validator of the whol widget (via
        :class:`rex.core.RecordVal`).
        """
        return RecordField(self.name, self.validator, self.default)


class StateFieldBase(Field):
    """ Base class for state fields."""

    def describe(self, name, value, widget):
        """ Describe state."""
        raise NotImplemented()


class StateField(StateFieldBase):
    """ Definition of a widget's stateful field.

    :param validator: Validator
    :param default: Default value

    Other params are passed through to :class:`State` constructor.
    """

    def __init__(self, validator, default=NotImplemented, dependencies=None,
            deserializer=None, **params):
        super(StateField, self).__init__(validator, default=default)
        if self.default is NotImplemented:
            self.default = unknown
        self.validator = MaybeVal(self.validator)
        self.deserializer = deserializer
        self.params = params
        self.dependencies = dependencies or []

    def get_dependencies(self, widget):
        dependencies = self.dependencies
        if hasattr(dependencies, '__call__'):
            dependencies = dependencies(widget)
        return [Dep(dep).absolutize(widget.id) for dep in dependencies]

    def set_dependencies(self, dependencies):
        """ Set dependencies for the state.

        This is helper method which is intented to be used as a decorator::

            class MyWidget(Widget):

                value = StateField(...)

                @value.set_dependencies
                def value_dependencies(self, widget):
                    return [...]

        """
        self.dependencies = dependencies

    def set_deserializer(self, deserializer):
        """ Set deserializer for the state.

        This is helper method which is intented to be used as a decorator::

            class MyWidget(Widget):

                value = StateField(...)

                @value.set_deserializer
                def value_deserializer(self, widget, value):
                    return ...

        """
        self.deserializer = deserializer

    def validate(self, widget, value):
        if self.deserializer:
            value = self.deserializer(widget, value)
        value = self.validator(value)
        return value

    def describe(self, name, value, widget):
        st = State(
            id="%s/%s" % (widget.id, name),
            widget=widget,
            dependencies=self.get_dependencies(widget),
            validator=functools.partial(self.validate, widget),
            value=value,
            **self.params)
        return [(name, st)]


class DataSpecVal(Validate):

    refs_val = MapVal(StrVal(), OneOfVal(StrVal(), SeqVal(StrVal())))

    data_spec = RecordVal(
        RecordField('url', StrVal()),
        RecordField('refs', refs_val, default={}),
        RecordField('defer', OneOfVal(StrVal(), BoolVal()), default=None))

    data_spec_with_shorthand = OneOfVal(StrVal(), data_spec)

    def __call__(self, data):
        data = self.data_spec_with_shorthand(data)
        if isinstance(data, basestring):
            data = self.data_spec({'url': data})
        for k, v in data.refs.items():
            if not isinstance(v, list):
                data.refs[k] = [v]
            data.refs[k] = tuple(Reference(r) for r in data.refs[k])
        return data


class DataField(StateFieldBase):

    computator_factory = NotImplemented

    def __init__(self, include_meta=False, default=NotImplemented):
        super(DataField, self).__init__(DataSpecVal(), default=default)
        self.include_meta = include_meta

    def describe(self, name, spec, widget):
        if spec is None:
            return []
        state_id = "%s/%s" % (widget.id, name)
        computator = self.computator_factory(spec.url, spec.refs, self.include_meta)
        dependencies = [r.id for refs in spec.refs.values() for r in refs]
        st = State(
            id=state_id,
            widget=widget,
            computator=computator,
            dependencies=dependencies,
            is_writable=False,
            defer=spec.defer)
        return [(name, st)]


class CollectionField(DataField):

    computator_factory = CollectionComputator


class EntityField(DataField):

    computator_factory = EntityComputator


class PaginatedCollectionField(DataField):
    """ A reference to a collection which provides pagination mechanism."""

    def _extract_sort_state(self, spec):
        url = urlparse.urlparse(spec.url)
        for k, v in urlparse.parse_qs(url.query).items():
            if not k[-5:] == ':sort':
                continue
            _entity_name, field_name = k[:-5].split('.', 1)
            return ('+' if v[0] == 'asc' else '-') + field_name
        return unknown

    def describe(self, name, spec, widget):
        if spec is None:
            return []
        state_id = "%s/%s" % (widget.id, name)
        pagination_state_id = "%s/%s/pagination" % (widget.id, name)
        sort_state_id = "%s/%s/sort" % (widget.id, name)

        dependencies = [r.id for refs in spec.refs.values() for r in refs]

        refs = dict(spec.refs)
        refs.update({
            "top": (Reference("%s:top" % pagination_state_id),),
            "skip": (Reference("%s:skip" % pagination_state_id),),
            "sort": (Reference("%s" % sort_state_id),),
        })


        return [
            (name,
                State(
                    state_id,
                    widget=widget,
                    computator=PaginatedCollectionComputator(
                        pagination_state_id,
                        spec.url,
                        refs=refs,
                        include_meta=self.include_meta),
                    dependencies=dependencies + [
                        pagination_state_id,
                        sort_state_id],
                    is_writable=False,
                    defer=spec.defer)),
            ("%sPagination" % name,
                State(
                    pagination_state_id,
                    widget=widget,
                    computator=InitialValue({"top": 100, "skip": 0}, reset_on_changes=True),
                    validator=MaybeVal(MapVal(StrVal, IntVal)),
                    dependencies=dependencies + [sort_state_id],
                    persistence=State.INVISIBLE,
                    is_writable=True)),
            ("%sSort" % name,
                State(
                    sort_state_id,
                    value=self._extract_sort_state(spec),
                    widget=widget,
                    validator=MaybeVal(StrVal()),
                    dependencies=dependencies,
                    is_writable=True)),
        ]
