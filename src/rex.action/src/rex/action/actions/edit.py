"""

    rex.action.actions.edit
    =======================

    :copyright: 2015, Prometheus Research, LLC

"""

from rex.core import StrVal
from rex.port import Port
from rex.widget import Field, undefined

from ..typing import RecordTypeVal, RecordType
from .form_action import FormAction

__all__ = ('Edit',)


class Edit(FormAction):
    """ Edit an entity.


    Example action declaration (``action.yaml``)::

        - type: edit
          id: edit-individual
          entity: individual

    The set of fields will be inferred automatically for a given ``entity``.

    To configure a specified set of fields use ``fields`` parameter::

        - type: edit
          id: edit-individual
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

    name = 'edit'
    js_type = 'rex-action/lib/actions/Edit'

    class Introspection(FormAction.Introspection):
        info_js_type = 'rex-action/lib/inspect/EditActionInfo'
        detailed_info_js_type = 'rex-action/lib/inspect/EditDetailedActionInfo'


    submit_button = Field(
        StrVal(), default=undefined,
        doc="""
        Text for submit button.
        """)

    input = Field(
        RecordTypeVal(), default=RecordType.empty())

    def context(self):
        input = self.input if self.input.rows else RecordType([self.entity])
        return input, RecordType([self.entity])

    def bind_port(self):
        return {'*': ContextBinding([self.entity.name], is_join=False)}

