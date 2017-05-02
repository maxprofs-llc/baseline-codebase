"""

    rex.action.action
    =================

    This module provides :class:`Action` class which is used to describe actions
    within an application.

    :copyright: 2015, Prometheus Research, LLC

"""

from collections import namedtuple, OrderedDict
import hashlib

import yaml
from cached_property import cached_property

from rex.core import (
    get_settings,
    Location, locate, set_location,
    cached, guard,
    Error, Validate,
    autoreload, get_packages,
    RecordVal, MaybeVal,
    ChoiceVal, StrVal, IntVal, SeqVal, MapVal, OMapVal, OneOfVal, AnyVal)
from rex.widget import (
    Widget, WidgetVal, Field, computed_field,
    RSTVal,
    undefined, as_transitionable, TransitionableRecord)
from rex.widget.widget import _format_Widget
from rex.widget.util import add_mapping_key, pop_mapping_key, IconVal
from rex.widget.validate import DeferredVal, Deferred

from . import typing
from .validate import is_string_node

__all__ = ('ActionBase', 'Action', 'ActionVal')


class ActionMeta(Widget.__metaclass__):

    def __new__(mcs, name, bases, attrs):
        if 'name' in attrs:
            attrs['name'] = _action_sig(attrs['name'])
        cls = Widget.__metaclass__.__new__(mcs, name, bases, attrs)
        return cls


class _action_sig(namedtuple('Action', ['name'])):

    def __hash__(self):
        return hash((self.__class__.__name__, self.name))


class ContextTypes(TransitionableRecord):
    __transit_tag__ = 'map'

    fields = ('input', 'output')


class ActionBase(Widget):

    __metaclass__ = ActionMeta

    id = Field(
        StrVal(),
        default=undefined,
        doc="""
        **Deprecated**. Do not use
        """)

    icon = Field(
        IconVal(), default=undefined,
        doc="""
        Action icon
        """)

    title = Field(
        StrVal(), default=undefined,
        doc="""
        Action title (`String`)
        """)

    doc = Field(
        StrVal(), default=undefined,
        transitionable=False,
        doc="""
        Action doc string (`ReST String`)

        Used to generated the documentation.
        """)

    help = Field(
        RSTVal(), default=undefined,
        doc="""
        Help text (`ReST String`)

        Provide helpful information here. This will be displayed when user
        click the 'Help' button.
        """)

    width = Field(
        IntVal(), default=undefined,
        doc="""
        **Deprecated**. Do not use.
        """)

    kind = Field(
        ChoiceVal('normal', 'success', 'danger'), default=undefined,
        doc="""
        Kind of the action (`normal`, `success`, `danger`)

        Used for styling action and its action buttons accordingly. For
        example, actions of kind `danger` will have corresponding buttons
        colored red in toolbars.
        """)

    def __init__(self, **values):
        self.source_location = None
        self.uid = values.get('id') or id(self)
        self._domain = values.pop('__domain', typing.Domain.current())
        self._context_types = None
        super(ActionBase, self).__init__(**values)

    @property
    def domain(self):
        return self._domain

    @computed_field
    def settings(self, req):
        settings = get_settings().rex_action
        return {
            'includePageBreadcrumbItem': settings.include_page_breadcrumb_item,
        }

    def _clone_values(self, values):
        next_values = {}
        next_values.update({
            k: v
            for k, v in self.values.items()
            if k not in ('__domain',) or k in self._fields})
        next_values.update(values)
        if 'package' not in next_values:
            next_values.update({'package': self.package})
        if '__domain' not in next_values:
            next_values.update({'__domain': self.domain})
        return next_values

    def __clone__(self, **values):
        action = self.__class__(**self._clone_values(values))
        action.uid = self.uid
        return action

    def __validated_clone__(self, **values):
        action = self.validated(**self._clone_values(values))
        action.uid = self.uid
        return action

    def with_domain(self, domain):
        """ Override typing domain."""
        return self.__validated_clone__(__domain=domain)

    @cached_property
    def context_types(self):
        if self._context_types:
            return self._context_types
        input, output = self.context()
        if isinstance(input, dict):
            input = self.domain.record(**input)
        if isinstance(output, dict):
            output = self.domain.record(**output)
        if not isinstance(input, typing.Type):
            raise Error(
                'Action "%s" specified incorrect input type:'\
                % self.name.name, input)
        if not isinstance(output, typing.Type):
            raise Error(
                'Action "%s" specified incorrect output type:'\
                % self.name.name, output)
        return ContextTypes(input, output)

    def context(self):
        """ Compute context specification for an action.

        Should return a pair of context inputs and conext outputs.

        By default it just returns values of ``input`` and ``output`` fields but
        subclasses could override this to provide automatically inferred context
        specification.
        """
        raise NotImplementedError('%s.context()' % self.__class__.__name__)

    def typecheck(self, context_type=None):
        raise NotImplementedError('%s.typecheck()' % self.__class__.__name__)

    @classmethod
    def parse(cls, value):
        validate = ActionVal(action_class=cls)
        if isinstance(value, basestring) or hasattr(value, 'read'):
            return validate.parse(value)
        else:
            raise Error('Cannot parse an action from:', repr(value))

    NOT_DOCUMENTED = 'Action is not documented'

    @classmethod
    def document_header(cls):
        return unicode(cls.name.name)


class Action(ActionBase):

    class Configuration(ActionBase.Configuration):

        _no_override_sentinel = object()

        @cached_property
        def _override_validator(self):
            fields = [
                (field.name, field.validate, self._no_override_sentinel)
                for field in self.fields.values()
                if field.name not in ('id',)
            ]
            return RecordVal(fields)

        def _apply_override(self, action, override):
            if isinstance(override, basestring):
                override = self._override_validator.parse(override)
            elif isinstance(override, Deferred):
                override = override.resolve(self._override_validator)
            else:
                override = self._override_validator(override)
            override = {k: v for k, v in override._asdict().items()
                        if v is not self._no_override_sentinel}
            return self.override(action, override)

        def override(self, action, override):
            return action.__validated_clone__(**override)

    def typecheck(self, context_type=None):
        if context_type is None:
            context_type = self.context_types.input
        typing.unify(self.context_types.input, context_type)



@as_transitionable(ActionBase, tag='widget')
def _format_Action(action, req, path): # pylint: disable=invalid-name
    package_name, symbol_name, props = _format_Widget(action, req, path)
    props['context_types'] = {
        'input': action.context_types[0],
        'output': action.context_types[1],
    }
    return package_name, symbol_name, props


class ActionVal(Validate):
    """ Validator for actions."""

    _validate_pre = MapVal(StrVal(), AnyVal())
    _validate_type = StrVal()
    _validate_id = StrVal()

    def __init__(self,
            action_class=Action,
            action_base=None,
            package=None,
            id=None):
        self.action_base = action_base
        self.action_class = action_class
        self.package = package
        self.id = id

    def __hash__(self):
        return hash((
            self.action_base,
            self.action_class,
            self.package,
            self.id
        ))

    def construct(self, loader, node):
        if not isinstance(node, yaml.MappingNode):
            value = super(ActionVal, self).construct(loader, node)
            return self(value)

        loc = Location.from_node(node)

        with guard("While parsing:", loc):

            type_node, node = pop_mapping_key(node, 'type')

            if type_node and not is_string_node(type_node):
                with loader.validating(ActionVal()):
                    action_base = loader.construct_object(type_node, deep=True)
                override_spec = DeferredVal().construct(loader, node)
                return override(action_base, override_spec)

            if not type_node and self.action_base:
                override_spec = DeferredVal().construct(loader, node)
                return override(self.action_base, override_spec)

            if self.action_class is not Action:
                action_class = self.action_class
            elif not type_node:
                raise Error('no action "type" specified')
            elif is_string_node(type_node):
                with guard("While parsing:", Location.from_node(type_node)):
                    action_type = self._validate_type.construct(loader, type_node)
                    action_sig = _action_sig(action_type)
                    if action_sig not in ActionBase.mapped():
                        raise Error('unknown action type specified:', action_type)
                action_class = ActionBase.mapped()[action_sig]

        widget_val = WidgetVal(package=self.package, widget_class=action_class)

        if not any(k == 'id' for k, v in node.value):
            if self.id:
                node = add_mapping_key(node, 'id', self.id)
            else:
                id = '%s:%d' % (loc.filename, loc.line)
                id = hashlib.md5(id).hexdigest()
                node = add_mapping_key(node, 'id', id)

        action = widget_val.construct(loader, node)
        return action

    def __call__(self, value):
        if isinstance(value, self.action_class):
            return value
        value = dict(self._validate_pre(value))
        action_type = value.pop('type', NotImplemented)
        if action_type is NotImplemented:
            raise Error('no action "type" specified')
        action_type = self._validate_type(action_type)
        action_sig = _action_sig(action_type)
        if action_sig not in ActionBase.mapped():
            raise Error('unknown action type specified:', action_type)
        action_class = ActionBase.mapped()[action_sig]
        if not issubclass(action_class, self.action_class):
            raise Error('action must be an instance of:', self.action_class)
        value = {k: v for (k, v) in value.items() if k != 'type'}
        validate = WidgetVal(package=self.package, widget_class=action_class).validate_values
        value = validate(action_class, value)
        value['package'] = self.package
        return action_class._configuration(action_class, value)


def override(action, values):
    return action._configuration._apply_override(action, values)
