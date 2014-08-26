"""

    rex.widget.state.graph
    ======================

    Data structures for representing a whole application state and computations
    over them.

    :copyright: 2014, Prometheus Research, LLC

"""

from collections import namedtuple, MutableMapping, Mapping
from rex.core import AnyVal, Error
from ..logging import getLogger


log = getLogger(__name__)


class StateGraph(Mapping):
    """ Represents immutable graph of states with dependencies between.

    Instances of :class:`StateGraph` implement :class:`collections.Mapping`
    abstract base class.

    :param initial: Intial state
    :type initial: :class:`collections.Mapping`
    """

    def __init__(self, initial=None):
        self.storage = {}
        self.dependencies = {}
        self.dependents = {}

        if initial is not None:
            _merge_state_into(self, initial)

    def __contains__(self, state_id):
        return state_id in self.storage

    def __iter__(self):
        return iter(self.storage)

    def __len__(self):
        return len(self.storage)

    def __getitem__(self, state_id):
        if ':' in state_id:
            state_id = state_id.split(':', 1)[0]
        return self.storage[state_id]

    def __str__(self):
        return "%s(storage=%s, dependents=%s)" % (
            self.__class__.__name__, self.storage, self.dependents)

    __repr__ = __str__

    def get_value(self, ref):
        """ Dereference state reference to a value.

        :param ref: state reference
        :type ref: str | :class:`Reference`
        """
        if not isinstance(ref, Reference):
            ref = Reference(ref)
        try:
            value = self.storage[ref.id].value
            if value is unknown:
                raise LookupError("value %s is unknown" % (ref,))
            for part in ref.path:
                if value is None:
                    return None
                value = value.get(part)
        except KeyError:
            if ref.id in self.storage:
                raise LookupError(
                    "cannot dereference '%s' reference with value '%r'" % (
                        ref, self.storage[ref.id].value))
            else:
                raise LookupError("cannot dereference '%s' reference" % (ref,))
        else:
            return value

    def merge(self, state):
        result = self.__class__(self)
        _merge_state_into(result, state)
        return result


class MutableStateGraph(StateGraph, MutableMapping):
    """ A mutable version of state graph.

    Instances of :class:`MutableStateGraph` implement
    :class:`collections.MutableMapping` abstract base class.
    """

    def add(self, *args, **kwargs):
        """ Shortuct for adding new state to a graph.

        For arguments see :class:`State`.
        """
        st = State(*args, **kwargs)
        self[st.id] = st

    def set(self, state_id, value):
        """ Update state by ``state_id`` with a new ``value``."""
        self[state_id] = self[state_id]._replace(value=value)

    def set_many(self, updates):
        """ Update many states at once."""
        for state_id, value in updates.items():
            self.set(state_id, value)

    def immutable(self):
        """ Return an immutable version of the state graph."""
        return StateGraph(self)

    def __setitem__(self, state_id, st):
        self.storage[state_id] = st
        self.dependencies[state_id] = st.dependencies
        self.dependents.setdefault(state_id, [])

        for dep in st.dependencies:
            dependents = self.dependents.setdefault(dep.id, [])
            inverse_dep = Dep(state_id, reset_only=dep.reset_only)
            if not inverse_dep in dependents:
                dependents.append(inverse_dep)

    def __delitem__(self, _state_id):
        raise NotImplementedError("not implemented")


class StateGraphComputation(Mapping):
    """ Computation over state graph.

    Instances of :class:`StateGraphComputation` implement
    class:`collections.Mapping` abstract base class.

    :attr input: input state graph
    :keyword output: resulted graph with computed state
    :keyword dirty: a set of dirtied state ids
    :keyword values: a set of precomputed values
    :keyword user: user
    """

    def __init__(self, input, output=None, dirty=None, values=None, user=None):
        self.input = input
        self.output = output or MutableStateGraph()
        self.dirty = set() if not dirty else set(dirty)
        self.user = user

        self._completed = False

        if self.user is not None:
            self.output['USER'] = State('USER', value=self.user, is_writable=False)

        if values is not None:
            for state_id, value in values.items():
                self.output[state_id] = self.input[state_id]._replace(value=value)

    def compute(self, id, defer=False):
        """ Force computation of state with id ``id``."""
        reset = False
        st = self.input[id]
        if not defer and st.defer:
            st = st._replace(defer=None)
        log.debug('computing: %s', id)
        is_active = st.is_active(self)
        if st.computator is not None:
            value = st.computator(st.widget, st, self, dirty=self.dirty, is_active=is_active)
        elif st.value is not unknown:
            value = st.value
        else:
            value = Reset(st.default)
        if isinstance(value, Reset):
            value = value.value
            reset = True
        if st.value != value:
            self.dirty.add(id)
        log.debug('computed:  %s, reset status: %s', id, reset)
        self.output[st.id] = st._replace(value=value)
        return reset

    def is_computed(self, id):
        """ Check if state with id ``id`` is already computed."""
        return id in self.output and self.output[id].value is not unknown

    def get_output(self, dirty_only=False):
        """ Get computed application state.

        :keyword dirty_only: If output should contain only changed states
                             (default: ``False``)
        """
        if self._completed:
            raise RuntimeError(
                'computation cannot provide its output more than once')
        self._completed = True

        if dirty_only:
            return StateGraph({
                id: state for id, state
                in self.output.items()
                if id in self.dirty
            })
        else:
            result = self.output.immutable()
            result = result.merge({
                id: state for id, state
                in self.input.items()
                if not id in result
            })
            return result

    def __iter__(self):
        return iter(self.output)

    def __len__(self):
        return len(self.output)

    def __getitem__(self, ref):
        if not isinstance(ref, Reference):
            ref = Reference(ref)

        if self.is_computed(ref.id):
            return self.output.get_value(ref)

        print self.input.keys()
        if not ref.id in self.input:
            raise Error('invalid reference: %s' % (ref,))

        self.compute(ref.id)

        return self.output.get_value(ref)


def _merge_state_into(dst, src):
    for state_id, st in src.items():
        dst.storage[state_id] = st
        dst.dependencies[state_id] = st.dependencies

        for dep in st.dependencies:
            dependents = dst.dependents.setdefault(dep.id, [])
            inverse_dep = Dep(state_id, reset_only=dep.reset_only)
            if not inverse_dep in dependents:
                dependents.append(inverse_dep)


class Unknown(object):

    tag = '__unknown__'

    def __str__(self):
        return "Unknown()"

    __repr__ = __str__


#: A state value which is used as a placeholder while actual value isn't yet
#: computed.
unknown = Unknown()


_Reference = namedtuple('Reference', ['id', 'path'])

class Reference(_Reference):
    """ A reference to state and a path inside its value."""

    __slots__ = ()

    def __new__(cls, state_id, path=None):
        path = path or []
        if ':' in state_id:
            _state_id, _path = state_id.split(':', 1)
            return _Reference.__new__(cls, _state_id, _path.split('.') + path)
        else:
            return _Reference.__new__(cls, state_id, path)

    def __str__(self):
        return "Reference('%s:%s')" % (self.id, '.'.join(self.path))

    __repr__ = __str__


_StateID = namedtuple('StateID', ['parts'])

class StateID(_StateID):

    DELIMITER = '/'

    def __new__(cls, *state_id):
        if len(state_id) == 1:
            if isinstance(state_id[0], cls):
                return state_id[0]
            if isinstance(state_id[0], basestring):
                state_id = state_id[0].split(cls.DELIMITER)
        return _StateID.__new__(cls, tuple(state_id))

    def __str__(self):
        return "StateID('%s')" % self.DELIMITER.join(self.parts)

    __repr__ = __str__


_State = namedtuple('State', [
    'id',
    'widget',
    'computator',
    'validator',
    'is_active',
    'defer',
    'value',
    'default',
    'dependencies',
    'persistence',
    'is_writable',
    'alias'
])


class State(_State):
    """ Represents a single atom of application state.

    :attr id: state identifier
    :attr widget: widget state is bound to
    :attr computator: state computator
    :attr validator: state value validator
    :attr is_active: function which determines is state should be computed
    :attr defer: tag for a group of deferred state computation (or None is state
                 is not deferred)
    :attr value: current value (unknown if it is not yet computed)
    :attr default: default value
    :attr dependencies: a list of state dependencies
    :attr persistence: the strategy regarding if state should be persisted
                       across state changes
    :attr is_writable: if state is read-write
    :attr alias: state alias
    """

    PERSISTENT = 'persistent'
    EPHEMERAL = 'ephemeral'
    INVISIBLE = 'invisible'

    __slots__ = ()

    def __new__(cls, id, widget=None, computator=None, validator=AnyVal,
            is_active=None, value=unknown, default=None, dependencies=None,
            persistence=PERSISTENT, is_writable=True, defer=None, alias=None):
        if dependencies is None:
            dependencies = []
        dependencies = [Dep(dep) for dep in dependencies]
        return _State.__new__(
            cls,
            id=id,
            widget=widget,
            computator=computator,
            validator=validator,
            value=value,
            default=default,
            dependencies=dependencies,
            is_active=is_active or (lambda graph: True),
            defer=defer,
            persistence=persistence,
            is_writable=is_writable,
            alias=alias)


_Dep = namedtuple('Dep', ['id', 'reset_only'])


class Dep(_Dep):
    """ Represent dependency between states.
    
    :attr id: state identifier
    :attr reset_only: If ``True`` then state is only recomputed when the state
                      it depends on recomputed with :class:`Reset` marker.
    """

    __slots__ = ()

    def __new__(cls, state_id, reset_only=None):
        if isinstance(state_id, Dep):
            if reset_only is None:
                return state_id
            else:
                return state_id._replace(reset_only=reset_only)
        return _Dep.__new__(cls, state_id, reset_only=reset_only or False)

    def absolutize(self, prefix):
        if '/' in self.id:
            return self
        else:
            return self._replace(id='%s/%s' % (prefix, self.id))


_Reset = namedtuple('Reset', ['value'])


class Reset(_Reset):
    """ A special marker for state computations which instructs to recompute
    states which dependencies marked with ``reset_only``."""

    __slots__ = ()


def compute(graph, values=None, user=None, defer=False):
    """ Compute entire state graph.

    :param graph: Application state
    :param values: Known values to be merged into application state graph
    :param user: Current user
    :param defer: Allow state marked with `defer` tag to be deferred
    """
    computation = StateGraphComputation(graph, values=values, user=user)

    for state_id in computation.input:
        if not computation.is_computed(state_id):
            computation.compute(state_id, defer=defer)

    return computation.get_output()


def compute_update(graph, origins, user=None):
    """ Compute state graph update which were originated from ``origins``."""
    computation = StateGraphComputation(graph, dirty=origins, user=user)

    def _compute(state_id, recompute_deps=True):
        if computation.is_computed(state_id):
            return

        reset = computation.compute(state_id)

        if recompute_deps or state_id in origins:
            for dep in computation.input.dependents.get(state_id, []):
                st = computation.input[dep.id]
                if not dep.reset_only or reset \
                   and (st.state_id in origins or st.is_writable):
                    _compute(
                        dep.id,
                        recompute_deps=not reset or not dep.reset_only)

    for state_id in cause_effect_sort(computation.input, origins):
        _compute(state_id)

    return computation.get_output(dirty_only=True)


def cause_effect_sort(graph, ids):
    """ Sort ``ids`` topologically according to ``graph`` to respect
    cause-effect relationship."""
    result = []
    seen = set()

    # start with states which have no deps
    queue = [s for s in graph.values() if not s.dependencies]

    while queue:
        cur = queue.pop()
        if cur.id in seen:
            continue

        # check if we have deps we didn't see before
        dependencies = [
            graph[dep.id] for dep in cur.dependencies
            if dep.id not in seen and dep.id in graph]
        if dependencies:
            queue = [cur] + dependencies + queue
            continue

        # mark it as seen and append to the result
        seen.add(cur.id)
        if cur.id in ids:
            result.append(cur.id)

        # proceed with states which depend on the current state
        dependents = [
            graph[dep.id] for dep in graph.dependents.get(cur.id, [])
            if dep.id not in seen]
        if dependents:
            queue = dependents + queue

    return result
