"""Serialize read/retain/write in the same SQLite transaction."""

def begin_write(conn):
    if not conn.in_transaction:
        conn.execute('BEGIN IMMEDIATE')
