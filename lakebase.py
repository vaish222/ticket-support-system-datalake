"""
Lakebase (Databricks-managed Postgres) connection helper.

Connects using service principal authentication.
No OAuth tokens or secrets required.
"""

import os
from contextlib import contextmanager

import psycopg2
from databricks.sdk import WorkspaceClient
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine

_w = WorkspaceClient()

# Database configuration
ENDPOINT_PATH = "projects/ticket-support-system/branches/production/endpoints/primary"
DATABASE = os.environ.get("LAKEBASE_DATABASE", "databricks_postgres")


def _get_connection_params() -> dict:
    """Get connection parameters for Lakebase using service principal."""
    # Get endpoint host
    ep = _w.postgres.get_endpoint(name=ENDPOINT_PATH)
    host = ep.status.hosts.host
    
    # Get service principal username
    try:
        current_user = _w.current_user.me()
        username = current_user.user_name
    except:
        # Fallback for Databricks Apps service principal
        username = "app-1lvsgr ticket-system-app-assignment1"
    
    return {
        "host": host,
        "port": 5432,
        "database": DATABASE,
        "user": username,
        "sslmode": "require"
    }


def _lakebase_url() -> str:
    """Build Lakebase connection URL using service principal."""
    params = _get_connection_params()
    return f"postgresql://{params['user']}@{params['host']}:{params['port']}/{params['database']}?sslmode={params['sslmode']}"


@contextmanager
def get_connection():
    """Yield a raw psycopg2 connection with a RealDictCursor factory."""
    params = _get_connection_params()
    conn = psycopg2.connect(**params, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def get_engine():
    """Return a SQLAlchemy engine for Lakebase."""
    return create_engine(_lakebase_url())


def run_query(sql: str, params: tuple | dict | None = None) -> list[dict]:
    """Run a read query against Lakebase and return rows as list[dict]."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def run_write(sql: str, params: tuple | dict | None = None) -> int:
    """Run an INSERT/UPDATE/DELETE against Lakebase, return affected row count."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount
