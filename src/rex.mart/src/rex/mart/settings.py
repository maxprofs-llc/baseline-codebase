#
# Copyright (c) 2015, Prometheus Research, LLC
#


from rex.core import Setting, StrVal, MaybeVal, Error, IntVal, BoolVal
from rex.db import DBVal, GatewaysSetting, HTSQLExtensionsSetting


__all__ = (
    'MartHostingClusterSetting',
    'MartNamePrefixSetting',
    'MartHtsqlExtensionsSetting',
    'MartEtlHtsqlGatewaysSetting',
    'MartEtlHtsqlExtensionsSetting',
    'MartMaxColumnsSetting',
    'MartAllowRuntimeCreationSetting',
    'MartRuntimeCreationQueueSetting',
)


class MartHostingClusterSetting(Setting):
    """
    Specifies the connection string used to access the database system where
    the Mart databases will be located.

    If not specified, the database system that houses the management database
    will be use to store the Marts.

    NOTE: Although this setting will require that you provide a database name
    as part of the connection string, it will not be used.
    """

    name = 'mart_hosting_cluster'
    default = None

    # pylint: disable=no-self-use
    def validate(self, value):
        value = DBVal()(value)
        if value.engine != 'pgsql':
            raise Error(
                'Only PostgreSQL systems can host Marts'
            )
        return value


class MartNamePrefixSetting(Setting):
    """
    Specifies a prefix that will be applied to the names of all Mart databases
    created by this application instance.

    If not specified, defaults to ``mart_``.
    """

    name = 'mart_name_prefix'
    validate = MaybeVal(StrVal(r'^[a-z0-9_]+$'))
    default = 'mart_'


class MartHtsqlExtensionsSetting(HTSQLExtensionsSetting):
    """
    Specifies any additional HTSQL extensions that will be enabled for the
    Mart HTSQL instances that are retrieved via the tools in this package.

    The ``rex_deploy`` and ``tweak.meta`` extensions will **always** be
    enabled, regardless of whether or not they are listed in this setting.
    """

    name = 'mart_htsql_extensions'
    default = {}


class MartEtlHtsqlGatewaysSetting(GatewaysSetting):
    """
    Specifies the HTSQL gateway configurations that will be made available for
    use during the execution of HTSQL ETL scripts.

    One gateway named ``rexdb`` will always be made available, and it will
    point to the management database.
    """

    name = 'mart_etl_htsql_gateways'


class MartEtlHtsqlExtensionsSetting(HTSQLExtensionsSetting):
    """
    Specifies any additional HTSQL extensions that will be enabled for the
    execution of HTSQL ETL sripts.

    The ``rex_deploy``, ``tweak.etl``, and ``tweak.gateway`` extensions will
    **always** be enabled, regardless of whether or not they are listed in this
    setting.

    If not specified, this setting will only enable the ``tweak.meta``
    extension.
    """

    name = 'mart_etl_htsql_extensions'
    default = {
        'tweak.meta': {},
    }


class MartMaxColumnsSetting(Setting):
    """
    Specifies the maximum number of columns an Assessment-based table can have.

    If not specified, defaults to 1000.
    """

    name = 'mart_max_columns'
    validate = IntVal(min_bound=1)
    default = 1000


class MartAllowRuntimeCreationSetting(Setting):
    """
    Specifies whether or not to allow users to request the creation of Marts at
    runtime.

    If not specified, defaults to ``False``.
    """

    name = 'mart_allow_runtime_creation'
    validate = BoolVal()
    default = False


class MartRuntimeCreationQueueSetting(Setting):
    """
    Specifies the rex.asynctask queue to drop messages in when Mart creation
    requests are received.

    If not specified, defaults to ``rexmart_create``.
    """

    name = 'mart_runtime_creation_queue'
    validate = StrVal()
    default = 'rexmart_create'

