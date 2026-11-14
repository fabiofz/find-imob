"""Connections shared by local SQLite stores and the hosted PostgreSQL database."""
from contextlib import contextmanager
import os
import sqlite3


def database_url():
    return os.environ.get('DATABASE_URL', '').strip()


def is_cloud():
    return bool(database_url())


class PostgresConnection:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, parameters=()):
        # Application statements use SQLite-style placeholders and contain no
        # literal question marks. Values are always bound by the driver.
        return self.connection.execute(statement.replace('?', '%s'), parameters)

    def executemany(self, statement, parameters):
        with self.connection.cursor() as cursor:
            cursor.executemany(statement.replace('?', '%s'), parameters)

    def commit(self):
        self.connection.commit()


@contextmanager
def connect(path=None, *, autocommit=False):
    if is_cloud():
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=15) as db:
            yield PostgresConnection(db)
    else:
        db = sqlite3.connect(path, timeout=15, isolation_level=None if autocommit else 'DEFERRED')
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=15000')
        try:
            with db:
                yield db
        finally:
            db.close()


def integrity_errors():
    if is_cloud():
        from psycopg import IntegrityError
        return (sqlite3.IntegrityError, IntegrityError)
    return (sqlite3.IntegrityError,)
