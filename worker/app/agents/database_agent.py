from pathlib import Path
from pydantic import BaseModel, Field
from agents import Agent, function_tool
from dotenv import load_dotenv
import os
import psycopg2
from psycopg2 import sql
from collections import defaultdict
from app.agents.prompts import build_database_agent_instructions


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    return psycopg2.connect(database_url)


@function_tool
def get_database_schema(
    include_primary_keys: bool = False,
    include_column_types: bool = True,
    include_nullable: bool = False,
    include_defaults: bool = False,
):
    """
    Extracts schema information from a PostgreSQL database.
    By default, returns a compact view to reduce token usage like:
    {table_name: [{"name": "column_a", "type": "text"}, ...]}

    Use flags to include more details when needed.
    """
    include_any_column_metadata = include_column_types or include_nullable or include_defaults
    schema = defaultdict(list)
    detailed_schema = defaultdict(lambda: {"columns": [], "primary_key": []})

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if include_any_column_metadata:
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

                for table, col, dtype, nullable, default in cur.fetchall():
                    column_info = {"name": col}
                    if include_column_types:
                        column_info["type"] = dtype
                    if include_nullable:
                        column_info["nullable"] = nullable == "YES"
                    if include_defaults:
                        column_info["default"] = default
                    detailed_schema[table]["columns"].append(column_info)
            else:
                cur.execute("""
                    SELECT
                        table_name,
                        column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position;
                """)

                for table, col in cur.fetchall():
                    schema[table].append(col)

            if include_primary_keys:
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
                    if include_any_column_metadata:
                        detailed_schema[table]["primary_key"].append(col)
                    else:
                        if table not in detailed_schema:
                            detailed_schema[table] = {"columns": [], "primary_key": []}
                            detailed_schema[table]["columns"] = schema.get(table, [])
                        detailed_schema[table]["primary_key"].append(col)

    if include_any_column_metadata or include_primary_keys:
        if not include_any_column_metadata:
            for table, cols in schema.items():
                if table not in detailed_schema:
                    detailed_schema[table] = {"columns": cols, "primary_key": []}
        return dict(detailed_schema)

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
        instructions=build_database_agent_instructions(),
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
        load_dotenv(Path(__file__).resolve().parents[3] / ".env.local")
        
    agent = build_database_agent()
    result = asyncio.run(Runner.run(agent, "Can you answer questions about total sales by product category in the last month?"))
    print(result.final_output)
