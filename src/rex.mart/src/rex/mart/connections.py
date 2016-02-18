#
# Copyright (c) 2015, Prometheus Research, LLC
#


from contextlib import contextmanager

from htsql.core.connect import connect

from rex.core import get_settings
from rex.db import get_db, RexHTSQL
from rex.deploy import Cluster

from .config import get_hosting_db_uri, get_management_db_uri


__all__ = (
    'get_management_db',
    'get_hosting_cluster',
    'get_mart_db',
    'get_mart_etl_db',
    'get_sql_connection',
)


def get_management_db():
    """
    Returns an HTSQL instance connected to the management database.

    :rtype: rex.db.RexHTSQL
    """

    return get_db()


def get_hosting_cluster():
    """
    Returns a Cluster instance connected to the hosting database system.

    :rtype: rex.deploy.Cluster
    """

    return Cluster(get_hosting_db_uri())


def get_mart_db(name, extensions=None):
    """
    Returns an HTSQL instance connected to the specified Mart database.

    :param name: the name of the Mart database to connect to
    :type name: str
    :param extensions:
        the HTSQL extensions to enable/configure, in addition to those defined
        by the ``mart_htsql_extension`` setting
    :type extensions: dict
    :rtype: rex.db.RexHTSQL
    """

    uri = get_hosting_db_uri().clone(database=str(name))

    ext = {}
    ext.update(get_settings().mart_htsql_extensions)
    ext.update({
        'rex_deploy': {},
        'tweak.meta': {},
    })
    if isinstance(extensions, dict):
        ext.update(extensions)

    return RexHTSQL(uri, ext)


def get_mart_etl_db(name, extensions=None):
    """
    Returns an HTSQL instance connected to the specified Mart database. This
    instance is configured specifically for use in the ETL phases of Mart
    creation.

    :param name: the name of the Mart database to connect to
    :type name: str
    :param extensions:
        the HTSQL extensions to enable/configure, in addition to those defined
        by the ``mart_etl_htsql_extension`` setting
    :type extensions: dict
    :rtype: rex.db.RexHTSQL
    """

    uri = get_hosting_db_uri().clone(database=str(name))

    gateways = {}
    gateways.update(get_settings().mart_etl_htsql_gateways)
    gateways.update({
        'rexdb': get_management_db_uri(),
    })

    ext = {}
    ext.update(get_settings().mart_etl_htsql_extensions)
    ext.update({
        'rex_deploy': {},
        'tweak.etl': {},
        'tweak.gateway': {
            'gateways': gateways,
        },
    })
    if isinstance(extensions, dict):
        ext.update(extensions)

    return RexHTSQL(uri, ext)


@contextmanager
def get_sql_connection(htsql, autocommit=True):
    """
    Returns a DBAPI connection object connected to the same database as the
    specified HTSQL instance.

    :param htsql: the HTSQL instance to base the connection on
    :type htsql: htsql.HTSQL
    :param autocommit:
        whether or not to enable autocommit; if not specified, defaults to True
    :type autocommit: bool
    :rtype: psycopg2.connection
    """

    with htsql:
        sql = connect(with_autocommit=autocommit)
        try:
            yield sql
        finally:
            sql.close()

