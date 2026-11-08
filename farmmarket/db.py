"""MySQL access: pooled connections, parameterised queries and atomic transactions.

Every statement in the application uses %s placeholders, never string formatting of user input.
Connections use READ COMMITTED so that row locks (SELECT ... FOR UPDATE) fully serialise
competing allocations and deliveries on the same lot or request.
"""
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import mysql.connector
from mysql.connector import pooling

from . import config
from .errors import DatabaseUnavailable

_pool: pooling.MySQLConnectionPool | None = None


def _make_pool() -> pooling.MySQLConnectionPool:
    return pooling.MySQLConnectionPool(
        pool_name="farm_market_pool",
        pool_size=10,
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        connection_timeout=5,
    )


def reset_pool() -> None:
    """Forget the pool (used by tests and after a failed connection)."""
    global _pool
    _pool = None


def _connection():
    global _pool
    try:
        if _pool is None:
            _pool = _make_pool()
        conn = _pool.get_connection()
        conn.ping(reconnect=True, attempts=2, delay=0)
        cur = conn.cursor()
        cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        cur.close()
        return conn
    except mysql.connector.Error as exc:
        _pool = None
        raise DatabaseUnavailable(
            "The database is not reachable. Check that MySQL is running and that the "
            "settings in the .env file are correct."
        ) from exc


def check_connection() -> bool:
    """True when the database answers; used by the GUI start-up check."""
    try:
        conn = _connection()
        conn.close()
        return True
    except DatabaseUnavailable:
        return False


def query(sql: str, params: Sequence[Any] = ()) -> list[dict]:
    """Run a read-only statement and return all rows as dictionaries."""
    conn = _connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close()
        conn.commit()
        return rows
    finally:
        conn.close()


def query_one(sql: str, params: Sequence[Any] = ()) -> dict | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute_autocommit(sql: str, params: Sequence[Any] = ()) -> int:
    """Single statement committed immediately (used for audit rows that must survive a rollback)."""
    conn = _connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(params))
        conn.commit()
        last = cur.lastrowid
        cur.close()
        return last
    finally:
        conn.close()


@contextmanager
def transaction() -> Iterator[Any]:
    """Atomic unit of work. Everything inside commits together or not at all."""
    conn = _connection()
    cur = None
    try:
        conn.rollback()
        conn.start_transaction(isolation_level="READ COMMITTED")
        cur = conn.cursor(dictionary=True)
        yield cur
        conn.commit()
    except BaseException:
        try:
            conn.rollback()
        except mysql.connector.Error:
            pass
        raise
    finally:
        if cur is not None:
            try:
                cur.close()
            except mysql.connector.Error:
                pass
        conn.close()


def fetch_all(cur, sql: str, params: Sequence[Any] = ()) -> list[dict]:
    cur.execute(sql, tuple(params))
    return cur.fetchall()


def fetch_one(cur, sql: str, params: Sequence[Any] = ()) -> dict | None:
    cur.execute(sql, tuple(params))
    return cur.fetchone()
