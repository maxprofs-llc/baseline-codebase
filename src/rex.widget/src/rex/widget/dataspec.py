"""

    rex.widget.dataspec
    ===================

    :copyright: 2015, Prometheus Research, LLC

"""

from rex.core import Validate, StrVal, RecordVal, MapVal, AnyVal, OneOfVal
from rex.web import route as resolve_handler

from .url import PortURL, QueryURL, URL
from .transitionable import TransitionableRecord

__all__ = (
    'CollectionSpecVal', 'EntitySpecVal', 'CollectionSpec', 'EntitySpec',
    'PropBinding', 'StateBinding')


class DataSpec(TransitionableRecord):

    fields = ('route', 'params')

    def __transit_format__(self, req, path):
        if isinstance(self.route, basestring):
            route = self.route
            if self.route.startswith('/'):
                package = req.environ['rex.package']
                route = '%s:%s' % (package, route)
            handler = resolve_handler(route)
            if hasattr(handler, 'port'):
                return PortURL(route), self.params
            else:
                return QueryURL(route), self.params
        return self.route, self.params


class CollectionSpec(DataSpec):
    """ A specification for a collection dataset."""

    __transit_tag__ = 'collection'


class EntitySpec(DataSpec):
    """ A specification for an entity dataset."""

    __transit_tag__ = 'entity'


class Binding(TransitionableRecord):

    fields = ('name',)


class PropBinding(Binding):

    __transit_tag__ = 'propbinding'


class StateBinding(Binding):

    __transit_tag__ = 'statebinding'


class DataSpecVal(Validate):
    """ Base class for validators for data specifications."""

    spec_type = NotImplemented

    _validate_shortcut = StrVal()
    _validate_full = RecordVal(
        ('route', StrVal()),
        ('params', MapVal(StrVal(), AnyVal())),
    )
    _validate = OneOfVal(_validate_shortcut, _validate_full)

    def __call__(self, value):
        if isinstance(value, self.spec_type):
            return value
        value = self._validate(value)
        if isinstance(value, basestring):
            value = self._validate_full.record_type(route=value, params={})
        return self.spec_type(route=value.route, params=value.params)


class CollectionSpecVal(DataSpecVal):
    """ Validator for :class:`CollectionSpec` values.

    See :ref:`Data Specifications guide <guide-dataspec>` for more info on its
    usage.
    """

    spec_type = CollectionSpec


class EntitySpecVal(DataSpecVal):
    """ Validator for :class:`EntitySpec` values.

    See :ref:`Data Specifications guide <guide-dataspec>` for more info on its
    usage.
    """

    spec_type = EntitySpec
