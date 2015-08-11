"""

    rex.action.actions.make
    =======================

    :copyright: 2015, Prometheus Research, LLC

"""

from collections import OrderedDict

from cached_property import cached_property
from webob.exc import HTTPBadRequest

from rex.db import Query
from rex.core import MaybeVal, SeqVal, StrVal, MapVal, AnyVal, OMapVal
from rex.port import Port
from rex.widget import Field, FormFieldsetVal, responder, PortURL, QueryURL, undefined
from rex.widget import formfield, dataspec

from ..action import Action
from ..typing import RowTypeVal, RecordTypeVal, RecordType, annotate_port
from ..validate import RexDBVal, SyntaxVal

__all__ = ('Make',)


class Make(Action):
    """ Make an entity.

    This is an action which renders a form to create a new entity.

    Example action declaration (``action.yaml``)::

        - type: make
          id: make-individual
          entity: individual

    The set of fields will be inferred automatically for a given ``entity``.

    To configure a specified set of fields use ``fields`` parameter::

        - type: make
          id: make-individual
          entity: individual
          fields:
          - code
          - identity.sex
          - identity.givenname
            label: First Name
          - identity.surname
            label: Last Name

    Fields can be declared as a key path within the record, see ``code`` and
    ``identity.sex`` fields above (in this case label and other info will be
    inferred from schema) or completely with label and other parameters.
    """

    name = 'make'
    js_type = 'rex-action/lib/Actions/Make'

    entity = Field(
        RowTypeVal(),
        doc="""
        Name of a table in database.
        """)

    db = Field(
        RexDBVal(), default=None,
        transitionable=False,
        doc="""
        Database to use.
        """)

    fields = Field(
        MaybeVal(FormFieldsetVal()), default=None,
        doc="""
        A list of fields to show.

        If not specified then it will be generated automatically based on the
        data schema.
        """)

    value = Field(
        MapVal(StrVal(), AnyVal()), default={},
        doc="""
        An initial value.

        It could reference data from the current context via ``$name``
        references::

            study: $study
            individual: $individual

        """)

    submit_button = Field(
        StrVal(), default=undefined,
        doc="""
        Text for submit button.
        """)

    query = Field(
        SyntaxVal(), default=None, transitionable=False,
        doc="""
        Optional query which is used to persist data in database.
        """)

    input = Field(
        RecordTypeVal(), default=RecordType.empty())

    def __init__(self, **values):
        super(Make, self).__init__(**values)
        if self.fields is None:
            self.values['fields'] = formfield.from_port(self.port)
        else:
            self.values['fields'] = formfield.enrich(self.fields, self.port)
        self.values['use_query'] = self.query is not None

    @cached_property
    def port(self):
        if self.fields is None:
            port = Port(self.entity.type.name, db=self.db)
        else:
            value_fields = _value_to_fieldset(self.value).fields
            value_fields = formfield.enrich(value_fields, Port(self.entity.type.name, db=self.db))
            port = formfield.to_port(self.entity.type.name, value_fields + self.fields, db=self.db)
        return annotate_port(self.domain, port)

    def _construct_data_spec(self, url):
        return dataspec.EntitySpec(url, {})

    @responder(wrap=_construct_data_spec, url_type=PortURL)
    def data(self, req):
        if not self.query:
            return self.port(req)
        raise HTTPBadRequest('port is not allowed in this configuration')

    @responder(wrap=_construct_data_spec, url_type=QueryURL)
    def data_query(self, req):
        if self.query:
            query = Query(self.query, self.db)
            query.parameters = {}
            for f in self.fields:
                query.parameters[f.value_key[0]] = None
            return query(req)
        raise HTTPBadRequest('query is not allowed in this configuration')

    def context(self):
        return self.input, self.domain.record(self.entity)


def _value_to_fieldset(value, _key=None):
    _key = _key or ['__root__']
    if isinstance(value, dict):
        return formfield.Fieldset(
            value_key=_key,
            fields=[_value_to_fieldset(v, _key=[k]) for k, v in value.items()])
    elif isinstance(value, list):
        merged = {}
        for item in value:
            merged.update(item)
        return formfield.List(
            value_key=_key,
            fields=[_value_to_fieldset(v, _key=[k]) for k, v in merged.items()])
    else:
        return formfield.StringFormField(value_key=_key)
