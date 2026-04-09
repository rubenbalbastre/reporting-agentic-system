from pathlib import Path
from pydantic import BaseModel, Field
from agents import Agent, function_tool
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2 import sql
from collections import defaultdict


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(database_url)


@function_tool
def get_database_schema():
    """
    Extracts schema information from a PostgreSQL database.

    Args:
        conn: psycopg2 connection object

    Returns:
        dict: {
            table_name: {
                "columns": [
                    {
                        "name": column_name,
                        "type": data_type,
                        "nullable": bool,
                        "default": default_value
                    },
                    ...
                ],
                "primary_key": [col1, col2, ...]
            },
            ...
        }
    """

    schema = defaultdict(lambda: {"columns": [], "primary_key": []})

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # --- Get columns ---
            cur.execute("""
                SELECT
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """)

            for row in cur.fetchall():
                table, col, dtype, nullable, default = row
                schema[table]["columns"].append({
                    "name": col,
                    "type": dtype,
                    "nullable": nullable == "YES",
                    "default": default
                })

            # --- Get primary keys ---
            cur.execute("""
                SELECT
                    tc.table_name,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_schema = 'public';
            """)

            for table, col in cur.fetchall():
                schema[table]["primary_key"].append(col)

    return dict(schema)


@function_tool
def get_unique_values(table: str, column: str, limit: int = 20):
    query = sql.SQL(
        """
        SELECT {column}, COUNT(*) as count
        FROM {table}
        GROUP BY {column}
        ORDER BY count DESC
        LIMIT %s;
        """
    ).format(
        table=sql.Identifier(table),
        column=sql.Identifier(column),
    )
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            return cur.fetchall()


@function_tool
def get_column_stats(table: str, column: str):
    query = sql.SQL(
        """
        SELECT
            MIN({column}),
            MAX({column}),
            AVG({column}),
            STDDEV({column})
        FROM {table};
        """
    ).format(
        table=sql.Identifier(table),
        column=sql.Identifier(column),
    )
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()
        

@function_tool
def preview_table(table: str, limit: int = 10):
    query = sql.SQL("SELECT * FROM {table} LIMIT %s;").format(
        table=sql.Identifier(table),
    )
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (limit,))
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    return {"columns": cols, "rows": rows}


class RelevantItem(BaseModel):
    table_name: str
    columns: list[str]


class DataBaseInspection(BaseModel):
    question_can_be_answered_with_db: bool
    relevant_items: list[RelevantItem] = Field(default_factory=list)
    reason: str
    pseudo_query: str


def build_database_agent() -> Agent:

    database_agent = Agent(
        name="database_agent",
        instructions="You must think if the user's question can be answered by querying the database. If it can, you should generate SQL queries based on the user's question. You should only respond with the SQL query and nothing else.",
        model="gpt-5.4-nano",
        output_type=DataBaseInspection,
        tools=[
            get_database_schema,
            get_unique_values,
            get_column_stats,
            preview_table,
        ]
    )

    return database_agent


if __name__ == "__main__":
    from agents import Runner
    import asyncio
    if os.getenv("APP_ENV") != "docker":
        load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")
        
    agent = build_database_agent()
    result = asyncio.run(Runner.run(agent, "Can you answer questions about total sales by product category in the last month?"))
    print(result.final_output)
