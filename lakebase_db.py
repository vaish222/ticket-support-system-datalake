"""
Lakebase database connection module for the support ticket system.
Handles connection pooling using native password authentication.
"""

import os
import base64
import psycopg2
from psycopg2 import pool
from databricks.sdk import WorkspaceClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_w = WorkspaceClient()
_connection_pool = None

# Secret configuration
SECRET_SCOPE = os.environ.get("LAKEBASE_SECRET_SCOPE", "database")
SECRET_KEY = os.environ.get("LAKEBASE_SECRET_KEY", "lakebase-url")


def _get_lakebase_url():
    """Fetch the Lakebase connection URL from Databricks secrets."""
    secret = _w.secrets.get_secret(scope=SECRET_SCOPE, key=SECRET_KEY)
    return base64.b64decode(secret.value).decode("utf-8")


def get_connection_pool():
    """Get or create a connection pool to Lakebase."""
    global _connection_pool
    
    if _connection_pool is None:
        lakebase_url = _get_lakebase_url()
        
        logger.info("Creating connection pool to Lakebase")
        
        # Create pool using the connection URL (includes username and password)
        _connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=lakebase_url
        )
    
    return _connection_pool


def get_connection():
    """Get a connection from the pool."""
    pool = get_connection_pool()
    return pool.getconn()


def release_connection(conn):
    """Return a connection to the pool."""
    pool = get_connection_pool()
    pool.putconn(conn)


def run_query(query, params=None):
    """Execute a SELECT query and return results as a list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    finally:
        release_connection(conn)


def run_write(query, params=None):
    """Execute a write query (INSERT, UPDATE, DELETE) and commit."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def run_write_returning(query, params=None):
    """Execute a write query with RETURNING clause and return the result."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            conn.commit()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            row = cur.fetchone()
            return dict(zip(columns, row)) if row else None
    except Exception as e:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def ensure_schema():
    """Create the database schema if it doesn't exist."""
    logger.info("Ensuring database schema exists...")
    
    schema_sql = """
    -- Create tickets table
    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id SERIAL PRIMARY KEY,
        title VARCHAR(500) NOT NULL,
        status VARCHAR(50) NOT NULL DEFAULT 'open',
        created_by VARCHAR(255) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    
    -- Create ticket_messages table with foreign key
    CREATE TABLE IF NOT EXISTS ticket_messages (
        message_id SERIAL PRIMARY KEY,
        ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
        message_text TEXT NOT NULL,
        author VARCHAR(255) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    
    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
    CREATE INDEX IF NOT EXISTS idx_tickets_created_by ON tickets(created_by);
    CREATE INDEX IF NOT EXISTS idx_messages_ticket_id ON ticket_messages(ticket_id);
    CREATE INDEX IF NOT EXISTS idx_messages_created_at ON ticket_messages(created_at DESC);
    """
    
    run_write(schema_sql)
    logger.info("Database schema ready")