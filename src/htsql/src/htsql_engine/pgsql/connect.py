#
# Copyright (c) 2006-2011, Prometheus Research, LLC
# See `LICENSE` for license information, `AUTHORS` for the list of authors.
#


"""
:mod:`htsql_engine.pgsql.connect`
=================================

This module implements the connection adapter for PostgreSQL.
"""


from htsql.connect import Connect, DBError, NormalizeError
from htsql.context import context
import psycopg2, psycopg2.extensions


class PGSQLError(DBError):
    """
    Raised when a database error occurred.
    """


class ConnectPGSQL(Connect):
    """
    Implementation of the connection adapter for PostgreSQL.
    """

    def open(self):
        # Prepare and execute the `psycopg2.connect()` call.
        db = context.app.htsql.db
        parameters = {}
        parameters['database'] = db.database
        if db.host is not None:
            parameters['host'] = db.host
        if db.port is not None:
            parameters['port'] = db.port
        if db.username is not None:
            parameters['user'] = db.username
        if db.password is not None:
            parameters['password'] = db.password
        connection = psycopg2.connect(**parameters)

        # Enable autocommit.
        if self.with_autocommit:
            connection.set_isolation_level(
                    psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        return connection


class NormalizePGSQLError(NormalizeError):

    def __call__(self):
        # If we got a DBAPI exception, generate our own error.
        if isinstance(self.error, psycopg2.Error):
            message = str(self.error)
            error = PGSQLError(message)
            return error

        # Otherwise, let the superclass return `None`.
        return super(NormalizePGSQLError, self).__call__()


