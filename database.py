"""Small database adapter: SQLite for local work, PostgreSQL in production."""
import sqlite3


class Database:
    def __init__(self, target):
        self.is_postgres = target.startswith(('postgres://', 'postgresql://'))
        if self.is_postgres:
            import psycopg
            from psycopg.rows import dict_row
            # Supavisor transaction pooling cannot use prepared statements.
            self.connection = psycopg.connect(target, row_factory=dict_row, prepare_threshold=None)
        else:
            self.connection = sqlite3.connect(target, timeout=10)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute('PRAGMA foreign_keys=ON')

    def _sql(self, query):
        return query.replace('?', '%s') if self.is_postgres else query

    def execute(self, query, params=()):
        return self.connection.execute(self._sql(query), params)

    def executescript(self, script):
        if self.is_postgres:
            raise RuntimeError('Production schema changes must use a reviewed migration.')
        return self.connection.executescript(script)

    def insert_id(self, query, params):
        if self.is_postgres:
            return self.execute(query + ' RETURNING id', params).fetchone()['id']
        return self.execute(query, params).lastrowid

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()

