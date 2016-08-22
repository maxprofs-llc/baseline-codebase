"""

    rex.action.wizard
    =================

    This module provides :class:`Wizard` widget which is used to render and
    orchestrate actions.

    :copyright: 2015, Prometheus Research, LLC

"""

import hashlib
import urlparse
import cgi

from webob import Response
from webob.exc import HTTPMethodNotAllowed

from cached_property import cached_property

from rex.core import (
    get_packages, autoreload,
    Record,
    Validate, Error, locate, guard,
    OneOfVal, RecordVal, IntVal, MaybeVal,
    AnyVal, StrVal, MapVal, SeqVal, StrVal, RecordVal, ChoiceVal)
from rex.widget import Widget, Field, responder
from rex.widget.transitionable import as_transitionable
from rex.widget.validate import DeferredVal, Deferred
from rex.widget.util import product_to_pojo
from rex.web import route
from rex.port import Port

from .action import ActionBase, ActionVal, _format_Action
from .validate import (
    DomainVal,
    ActionMapVal,
    ActionReferenceVal, LocalActionReference, GlobalActionReference)
from . import typing
from . import instruction
from . import introspection

__all__ = ('WizardBase', 'WizardWidgetBase')


validate_entity = RecordVal(
    ('type', StrVal()),
    ('id', StrVal()))

validate_context = MapVal(
    StrVal(),
    OneOfVal(validate_entity, AnyVal()))

validate_req = MapVal(
    StrVal(),
    validate_context)


def is_entity(obj):
    """ Check if ``obj`` is being an entity."""
    return isinstance(obj, validate_entity.record_type)


class WizardWidgetBase(Widget):
    """ Base class for widgets which render wizards."""

    path = Field(
        DeferredVal(),
        doc="""
        Wizard path specified as a tree of possible transitions between actions.
        """)

    actions = Field(
        DeferredVal(ActionMapVal()),
        transitionable=False,
        doc="""
        Wizard actions.
        """)

    initial_context = Field(
        MapVal(StrVal(), AnyVal()), default=None,
        doc="""
        Initial context.
        """)

    states = Field(
        DomainVal('action-scoped'), default=None,
        transitionable=False,
        doc="""
        State definitions for entities inside the context.
        """)

    def __init__(self, **values):
        super(WizardWidgetBase, self).__init__(**values)
        self._constructed_actions = {}
        if isinstance(self.actions, Deferred):
            with self.domain:
                self.actions = self.actions.resolve()
        if isinstance(self.path, Deferred):
            validate_path = instruction.PathVal(
                self.uid,
                self._resolve_action
            )
            self.path = self.path.resolve(validate_path)

    def _resolve_action(self, ref):
        if not ref in self._constructed_actions:
            action = resolve_action_reference(
                ref,
                actions=self.actions,
                package=self.package,
                domain=self.domain,
            )
            if isinstance(action, WizardBase):
                action.included = True
            self.states = self.domain.merge(action.domain)
            self._constructed_actions[ref] = action
        return self._constructed_actions[ref]

    @responder
    def data(self, req):

        if not req.method == 'POST':
            raise HTTPMethodNotAllowed()

        def is_entity(v):
            return isinstance(v, validate_entity.record_type)

        def param_def(name):
            return {'parameter': name, 'default': None}

        def refetch(entity, params=None):
            params = params or {}
            params_defs = [param_def(name) for name in params
                           if not name.lower() == 'user']
            params_bind = {k: v.id if is_entity(v) else v
                           for k, v in params.items()
                           if not k.lower() == 'user'}
            port = Port(params_defs + [{'entity': entity.type, 'select': []}])
            port = typing.annotate_port(self.states, port)
            product = port.produce((u'*', entity.id), **params_bind)
            data = product_to_pojo(product)[entity.type]
            return data[0] if data else None

        data = validate_req(req.json_body)

        update = {}
        for id, context in data.items():
            next_context = {}
            for k, v in context.items():
                if is_entity(v):
                    next_context[k] = refetch(v, params=context)
                else:
                    next_context[k] = v
            update[id] = next_context

        return Response(json=update)

    @property
    def domain(self):
        return self.states or typing.Domain.current()

    def typecheck(self, context_type=None):
        if context_type is None:
            if self.initial_context:
                context_type = typing.RecordType([
                    typing.RowType(k, typing.anytype)
                    for k in self.initial_context])
            else:
                input, _ = self.context_types
                context_type = input

        for inst in self.path.then:
            self._typecheck(inst, context_type, [])

    def context(self):
        input_nodes = self.path.then
        output_nodes = []

        def _find_output_nodes(inst):
            if not inst.then and not isinstance(inst, instruction.Repeat):
                output_nodes.append(inst)

        instruction.visit(self.path, _find_output_nodes)

        input = typing.intersect_record_types([
            node.action_instance.context_types.input
            for node in input_nodes
            if isinstance(node, instruction.Execute)
        ])
        output = typing.intersect_record_types([
            node.action_instance.context_types.output
            for node in output_nodes
            if isinstance(node, instruction.Execute)
        ])

        return input, output

    def _typecheck_execute(self, inst, context_type, path, recurse=True):
        with guard('While parsing:', locate(inst)):
            action = self._resolve_action(inst.action)
            if action is None:
                raise Error('Unknown action found:', inst.action)
            input, output = action.context_types
            try:
                action.typecheck(context_type)
            except typing.KindsDoNotMatch as err:
                error = Error('Unification error:', 'type kinds do not match')
                error.wrap('One type is %s:' % \
                            _type_repr(err.kind_a), err.type_a)
                error.wrap('Another type is %s:' % \
                            _type_repr(err.kind_b), err.type_b)
                error = _wrap_unification_error(
                        error, context_type, path, inst.action)
                raise error
            except typing.InvalidRowTypeUsage:
                error = Error('Row types are only valid within a record types')
                error = _wrap_unification_error(
                        error, context_type, path, inst.action)
                raise error
            except typing.UnknownKind as err:
                error = Error('Unification error:', 'unknown kinds')
                error.wrap('One type of kind %s' % \
                            err.kind_a, err.type_a)
                error.wrap('Another type of kind %s' % \
                            err.kind_b, err.type_b)
                error = _wrap_unification_error(
                        error, context_type, path, inst.action)
                raise error
            except typing.RecordTypeMissingKey as err:
                error = Error(
                    'Action "%s" cannot be used here:' % inst.action,
                    'Context is missing "%s"' % err.type)
                error = _wrap_unification_error(
                        error, context_type, path, inst.action)
                raise error
            except typing.RowTypeMismatch as err:
                error = Error(
                    'Action "%s" cannot be used here:' % inst.action,
                    'Context has "%s" but expected to have "%s"' % (
                        err.type_b, err.type_a))
                error = _wrap_unification_error(
                        error, context_type, path, inst.action)
                raise error
            except typing.UnificationError as err:
                error = Error('Type unification error:', err)
                error = _wrap_unification_error(
                        error, context_type, path, inst.action)
                raise error

        next_context_type = typing.RecordType.empty()
        next_context_type.rows.update(context_type.rows)
        next_context_type.rows.update(output.rows)

        if recurse and inst.then:
            return [
                pair
                for next_instruction in inst.then
                for pair in self._typecheck(
                    next_instruction, next_context_type, path + [inst.action])
            ]
        else:
            return [(inst, next_context_type)]

    def _typecheck_repeat(self, inst, context_type, path, recurse=True):
        end_types = [
            pair
            for repeat_inst in inst.repeat
            for pair in self._typecheck(
                repeat_inst, context_type, path + ['<repeat loop>'])
        ]

        actions = [self._resolve_action(item.action) for item in inst.repeat]
        if None in actions:
            raise Error('Unknown action found', inst.repeat)

        repeat_invariant = typing.intersect_record_types([
            action.context_types.input
            for action, repeat_inst in zip(actions, inst.repeat)
            if isinstance(repeat_inst, instruction.Execute)
        ])
        next_context_type = typing.RecordType.empty()
        next_context_type.rows.update(context_type.rows)
        next_context_type.rows.update(repeat_invariant.rows)

        for end_instruction, end_type in end_types:
            with guard('While parsing:', locate(end_instruction)):
                try:
                    typing.unify(next_context_type, end_type)
                except typing.RecordTypeMissingKey as err:
                    error = Error(
                        'Repeat ends with a type which is incompatible with its beginning:',
                        'Missing "%s"' % err.type)
                    raise error
                except typing.RowTypeMismatch as err:
                    error = Error(
                        'Repeat ends with a type which is incompatible with its beginning:',
                        'Has "%s" but expected to have "%s"' % (
                            err.type_b, err.type_a))
                    raise error
                except typing.UnificationError as err:
                    error = Error('Type unification error:', err)
                    error = _wrap_unification_error(error, context_type, path, inst.action)
                    raise error

        if inst.then:
            return [
                pair
                for next_instruction in inst.then
                for pair in self._typecheck(next_instruction, next_context_type, path + ['<repeat then>'])
            ]
        else:
            return [(inst, next_context_type)]

    def _typecheck_replace(self, inst, context_type, path, recurse=True):
        path = path + ['<replace %s>' % inst.replace]
        self._typecheck(
            inst.instruction, context_type, path, recurse=False)
        return []

    def _typecheck(self, inst, context_type, path, recurse=True):
        if isinstance(inst, instruction.Execute):
            return self._typecheck_execute(
                inst, context_type, path, recurse=recurse)
        elif isinstance(inst, instruction.Replace):
            return self._typecheck_replace(
                inst, context_type, path, recurse=recurse)
        elif isinstance(inst, instruction.Repeat):
            return self._typecheck_repeat(
                inst, context_type, path, recurse=recurse)
        elif isinstance(inst, instruction.Start):
            return [pair
                    for item in inst.then
                    for pair in self._typecheck(item, context_type, path)]

def _wrap_unification_error(error, context_type, path, action):
    if not context_type.rows:
        context_repr = '<empty context>'
    else:
        context_repr = sorted(context_type.rows.items())
        context_repr = ['%s: %s' % (k, v.type.key) for k, v in context_repr]
        context_repr = '\n'.join(context_repr)
    error.wrap('Context:', context_repr)
    error.wrap('While type checking action at path:', ' -> '.join(path + [action]))
    return error


def _type_repr(kind):
    if hasattr(kind, 'type_name') and kind.type_name is not NotImplemented:
        return kind.type_name
    else:
        return repr(kind)


local_action_ref_val = ActionReferenceVal(reference_type=LocalActionReference)


def resolve_action_reference(ref, actions=None, package=None, domain=None):
    """ Resolve action reference to action instance.

    :param ref: Action reference
    :keyword actions: Local actions bindings
    :keyword package: Current package
    :keyword domain: Current domain
    :returns: Action instance for a reference
    """
    # Prevent circular imports
    from .map import ActionRenderer

    action = None

    actions = actions or {}
    domain = domain or typing.Domain.current()

    ref = local_action_ref_val(ref)

    if not ref.id in actions:
        raise Error('Found unknown action reference:', ref.id)

    action = actions[ref.id]

    if isinstance(action, GlobalActionReference):
        global_ref = action
        if not global_ref.package:
            if not package:
                raise Error(
                    'Package name is missing, use pkg:path syntax',
                    global_ref)
            handler = route('%s:%s' % (package.name, global_ref.id))
        else:
            return load_action(global_ref)

        if handler is None:
            raise Error(
                'Cannot resolve global action reference:',
                global_ref)
        elif not isinstance(handler, ActionRenderer):
            raise Error(
                'Action reference resolves to handler of a non-action type:',
                global_ref)
        else:
            action = handler.action.__validated_clone__(id=ref.id)

    action = action.with_domain(action.domain.merge(domain))
    return action


@autoreload
def load_action(ref, open=open):
    packages = get_packages()
    with guard('While loading action:', ref):
        if ref.package not in packages:
            raise Error('Invalid package name:', ref.package)
        package = packages[ref.package]
        if not package.exists(ref.id):
            raise Error('Invalid path:', ref)
        filename = package.abspath(ref.id)
        with open(filename) as stream:
            validate = ActionVal(id=ref.id)
            return validate.parse(stream, open=open)


class WizardBase(WizardWidgetBase, ActionBase):
    """ Base class for wizards."""

    def __init__(self, *args, **kwargs):
        super(WizardBase, self).__init__(*args, **kwargs)
        self.included = False

    class Configuration(ActionBase.Configuration):

        def _apply_override(self, wizard, override):
            if isinstance(override, Deferred):
                override = override.resolve(ActionMapVal(action_map=wizard._constructed_actions))
            actions = dict(wizard._constructed_actions)
            for k, v in override.items():
                if not k in actions:
                    raise Error('Unknown action override:', k)
                if isinstance(v, ActionBase):
                    actions[k] = v
                else:
                    for v in v:
                        actions[k] = v(actions[k])
            path = instruction.override(wizard.path, actions)
            return wizard.__validated_clone__(path=path, actions=actions)

    Introspection = introspection.WizardIntrospection

    @property
    def domain(self):
        return self.states or typing.Domain.current()

    def with_domain(self, domain):
        actions = {
            ref: action.with_domain(domain)
            for ref, action in self._constructed_actions.items()}
        wizard = self.__validated_clone__(__domain=domain)
        wizard._constructed_actions = actions
        return wizard

    def refine_input(self, input):
        path = self.path.__clone__(then=[
            inst.__clone__(action_instance=inst.action_instance.refine_input(input))
            for inst in self.path.then
        ])
        return self.__validated_clone__(path=path)


class Wizard(WizardBase):
    """ Wizard which renders the last active action on an entire screen."""

    name = 'wizard'
    js_type = 'rex-action/lib/wizard/Wizard'


def _collect_actions(wizard):
    actions = {}
    # Check if actions are constructed and if not then force them to be
    # constructed by typechecking. This is needed to make sure things work after
    # reloads.
    if not wizard._constructed_actions:
        wizard.typecheck()
    for key, action in wizard._constructed_actions.items():
        key = '%s@%s' % (wizard.uid, key)
        key = hashlib.md5(key).hexdigest()
        actions[key] = action
        if isinstance(action, WizardBase):
            actions.update(_collect_actions(action))
    return actions


@as_transitionable(WizardBase, tag='widget')
def _format_Wizard(wizard, req, path): # pylint: disable=invalid-name
    js_type, props = _format_Action(wizard, req, path)
    if not wizard.included:
        props['actions'] = _collect_actions(wizard)
    return js_type, props
