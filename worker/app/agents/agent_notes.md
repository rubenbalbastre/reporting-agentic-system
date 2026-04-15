**Notes:**

* The database is PostgreSQL.
* Use `DATABASE_URL` from the environment for database access.
* When loading SQL into pandas (`read_sql_query` / `read_sql`), use a SQLAlchemy engine/connection (for example `sqlalchemy.create_engine(DATABASE_URL)`) instead of passing a raw DBAPI connection.
* You may still use `psycopg2` directly for non-pandas PostgreSQL operations.
* For matplotlib categorical charts (for example `plt.bar(category, value)`), always clean plotting columns first:
  - Fill null categories with `"Unknown"` and cast category labels to `str`.
  - Convert metric columns with `pd.to_numeric(..., errors="coerce").fillna(0.0)`.
  - Validate expected columns exist and fail with a clear error if they are missing/empty after cleaning.
* Never call `datetime.utcnow()`; use timezone-aware UTC timestamps instead (for example `datetime.now(timezone.utc)`).
* When writing report markdown with figures, always include markdown image references (not HTML) and prefer `/reports/{report_id}/files/<filename>` paths.
            
