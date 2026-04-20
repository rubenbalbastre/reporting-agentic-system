import os

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Return a PostgreSQL connection configured to yield dict-like rows."""
    database_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
