#
# Copyright (c) 2016, Prometheus Research, LLC
#


from webob.exc import HTTPMethodNotAllowed, HTTPBadRequest

from rex.action import typing
from rex.core import StrVal
from rex.widget import formfield, FormFieldsetVal, responder, PortURL, Field, \
    RSTVal

from .base import MartAction, MART_TYPE
from .filter import MartIntroAction
from .tool import MartTool


__all__ = (
    'DictionaryIntroAction',
    'DictionaryPickTableMartAction',
    'DictionaryPickTableColumnMartAction',
    'DictionaryPickColumnMartAction',
    'DictionaryPickEnumerationMartAction',
    'DictionaryViewTableMartAction',
    'DictionaryViewColumnMartAction',
)


class DictionaryMartTool(MartTool):
    name = 'dictionary'

    @classmethod
    def is_enabled_for_mart(cls, mart):
        for processor in mart.definition.get('processors', []):
            if processor['id'] == 'datadictionary':
                return True
        return False


DEFAULT_INTRO_TEXT = RSTVal()("""
This tool allows you to explore the columns and tables that are contained
within this RexMart database.

Use the buttons above to begin exploring.
""")


class DictionaryIntroAction(MartIntroAction):
    """
    The primary entry point for the Data Dictionary tool.
    """

    name = 'mart-dictionary'
    tool = 'dictionary'

    def __init__(self, **values):
        super(DictionaryIntroAction, self).__init__(**values)
        if not self.title:
            self.title = 'Data Dictionary'
        if not self.icon:
            self.icon = 'book'
        if not self.text:
            self.text = DEFAULT_INTRO_TEXT


class DictionaryPickMartAction(MartAction):
    fields = Field(
        FormFieldsetVal(),
        default=None,
        doc='The fields of the object to display'
    )

    search = Field(
        StrVal(),
        default=None,
        doc='The HTSQL expression to use when searching'
    )

    table = Field(
        StrVal(),
        default=None,
        doc='The name of the table containing the records'
    )

    def get_port_parameters(self):
        # pylint: disable=no-self-use
        return {}

    def get_port_mask(self):
        # pylint: disable=no-self-use
        return None

    @responder(url_type=PortURL)
    def data(self, request):
        if request.method == 'POST':
            # These are marts, we only want read operations.
            raise HTTPMethodNotAllowed()

        mart = self.get_mart(request)
        if not mart:
            raise HTTPBadRequest('Specified mart does not exist')
        mart_db = self.get_mart_db(mart)

        filters = []
        if self.search:
            filters.append(
                '__search__($search) := %s' % (self.search,)
            )

        port = formfield.to_port(
            entity=self.table,
            fields=self.fields,
            filters=filters,
            parameters=self.get_port_parameters(),
            mask=self.get_port_mask(),
            db=mart_db,
        )

        return port(request)


class DictionaryPickTableMartAction(DictionaryPickMartAction):
    """
    Displays the tables recorded in the Data Dictionary so the user can select
    one to see more information.
    """

    name = 'mart-dictionary-tables'
    js_type = 'rex-mart-actions', 'DictionaryPickTable'

    def __init__(self, **values):
        super(DictionaryPickTableMartAction, self).__init__(**values)
        if not self.fields:
            self.fields = FormFieldsetVal().parse("""
            - value_key: name
              label: Name
            - value_key: title
              label: Title
            - value_key: description
              label: Description
            """)
        if not self.search:
            self.search = 'name~$search|ft_matches(title, $search)' \
                '|ft_matches(description, $search)'
        if not self.table:
            self.table = 'datadictionary_table'

    def context(self):
        return {'mart': MART_TYPE}, {'mart_table': typing.string}


class DictionaryPickTableColumnMartAction(DictionaryPickMartAction):
    """
    Displays the columns of a specific table in the Data Dictionary so the user
    can select one to see more information.
    """

    name = 'mart-dictionary-table-columns'
    js_type = 'rex-mart-actions', 'DictionaryPickTableColumn'

    def __init__(self, **values):
        super(DictionaryPickTableColumnMartAction, self).__init__(**values)
        if not self.fields:
            self.fields = FormFieldsetVal().parse("""
            - value_key: name
              label: Name
            - value_key: datatype
              label: Data Type
            - value_key: title
              label: Title
            - value_key: description
              label: Description
            - value_key: source
              label: Source
            - value_key: link
              label: Linked Table
            """)
        if not self.search:
            self.search = 'name~$search|ft_matches(title, $search)' \
                '|ft_matches(description, $search)' \
                '|ft_matches(source, $search)|datatype~$search'
        if not self.table:
            self.table = 'datadictionary_column'

    def get_port_parameters(self):
        return {
            'mart_table': None,
        }

    def get_port_mask(self):
        return 'table=$mart_table'

    def context(self):
        ictx = {
            'mart': MART_TYPE,
            'mart_table': typing.string,
        }
        octx = {
            'mart_column': typing.string,
        }
        return ictx, octx


class DictionaryPickColumnMartAction(DictionaryPickMartAction):
    """
    Displays the columns in the Data Dictionary so the user can select one to
    see more information.
    """

    name = 'mart-dictionary-columns'
    js_type = 'rex-mart-actions', 'DictionaryPickColumn'

    def __init__(self, **values):
        super(DictionaryPickColumnMartAction, self).__init__(**values)
        if not self.fields:
            self.fields = FormFieldsetVal().parse("""
            - value_key: table_name
              label: Table
              type: calculation
              expression: table.name
            - value_key: name
              label: Name
            - value_key: datatype
              label: Data Type
            - value_key: title
              label: Title
            - value_key: description
              label: Description
            - value_key: source
              label: Source
            - value_key: link
              label: Linked Table
            """)
        if not self.search:
            self.search = 'name~$search|ft_matches(title, $search)' \
                '|ft_matches(description, $search)' \
                '|ft_matches(source, $search)|table.name~$search' \
                '|datatype~$search'
        if not self.table:
            self.table = 'datadictionary_column'

    def context(self):
        return {'mart': MART_TYPE}, {'mart_column': typing.string}


class DictionaryViewTableMartAction(DictionaryPickTableMartAction):
    """
    Displays the details about a table in the Data Dictionary.
    """

    name = 'mart-dictionary-table-details'
    js_type = 'rex-mart-actions', 'DictionaryViewTable'

    def __init__(self, **values):
        fields = values.get('fields', None)
        super(DictionaryViewTableMartAction, self).__init__(**values)
        if not fields:
            self.fields = FormFieldsetVal().parse("""
            - value_key: name
              label: Name
            - value_key: title
              label: Title
            - value_key: description
              label: Description
            - value_key: num_columns
              label: Columns
              type: calculation
              expression: count(datadictionary_column)
            """)

    def context(self):
        ictx = {
            'mart': MART_TYPE,
            'mart_table': typing.string,
        }
        octx = {}
        return ictx, octx


class DictionaryViewColumnMartAction(DictionaryPickColumnMartAction):
    """
    Displays the details about a column in the Data Dictionary.
    """

    name = 'mart-dictionary-column-details'
    js_type = 'rex-mart-actions', 'DictionaryViewColumn'

    def __init__(self, **values):
        fields = values.get('fields', None)
        super(DictionaryViewColumnMartAction, self).__init__(**values)
        if not fields:
            self.fields = FormFieldsetVal().parse("""
            - value_key: table_name
              label: Table
              type: calculation
              expression: table.name
            - value_key: name
              label: Name
            - value_key: datatype
              label: Data Type
            - value_key: link
              label: Linked Table
            - value_key: title
              label: Title
            - value_key: description
              label: Description
            - value_key: source
              label: Source
            - value_key: enumerations
              label: Enumerations
              type: calculation
              expression: count(datadictionary_enumeration)
            """)

    def context(self):
        ictx = {
            'mart': MART_TYPE,
            'mart_column': typing.string,
        }
        octx = {}
        return ictx, octx


class DictionaryPickEnumerationMartAction(DictionaryPickMartAction):
    """
    Displays the enumerations of a specific column in the Data Dictionary so
    the user can select one to see more information.
    """

    name = 'mart-dictionary-enumerations'
    js_type = 'rex-mart-actions', 'DictionaryPickEnumeration'

    def __init__(self, **values):
        super(DictionaryPickEnumerationMartAction, self).__init__(**values)
        if not self.fields:
            self.fields = FormFieldsetVal().parse("""
            - value_key: name
              label: Name
            - value_key: description
              label: Description
            """)
        if not self.search:
            self.search = 'name~$search'
        if not self.table:
            self.table = 'datadictionary_enumeration'

    def get_port_parameters(self):
        return {
            'mart_column': None,
        }

    def get_port_mask(self):
        return 'column=$mart_column'

    def context(self):
        ictx = {
            'mart': MART_TYPE,
            'mart_column': typing.string,
        }
        octx = {
            'mart_enumeration': typing.string,
        }
        return ictx, octx

