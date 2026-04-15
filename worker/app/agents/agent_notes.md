**Notes:**

* The database is PostgreSQL.
* Use `DATABASE_URL` from the environment for database access.
* When loading SQL into pandas (`read_sql_query` / `read_sql`), use a SQLAlchemy engine/connection (for example `sqlalchemy.create_engine(DATABASE_URL)`) instead of passing a raw DBAPI connection.
* You may still use `psycopg2` directly for non-pandas PostgreSQL operations.
            
