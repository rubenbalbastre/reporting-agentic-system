import os
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

import app.main as main_module


def _apply_schema(pool: ConnectionPool) -> None:
    schema_path = Path(__file__).resolve().parents[2] / "infra" / "postgres" / "app_schema.sql"
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_path.read_text())
        conn.commit()


@pytest.fixture
def integration_pool():
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/reporting"),
    )
    test_pool = ConnectionPool(conninfo=db_url, kwargs={"row_factory": dict_row})
    main_module.pool = test_pool
    yield test_pool
    test_pool.close()


@pytest.mark.integration
def test_create_message_persists_user_and_assistant_messages(integration_pool: ConnectionPool):
    _apply_schema(integration_pool)
    client = TestClient(main_module.app)

    report_title = f"integration-{uuid4().hex[:8]}"
    create_report_res = client.post("/api/reports", json={"title": report_title})
    assert create_report_res.status_code == 201
    report_id = create_report_res.json()["id"]

    create_message_res = client.post(
        f"/api/reports/{report_id}/messages",
        json={"content": "Please summarize this report."},
    )
    assert create_message_res.status_code == 201
    payload = create_message_res.json()
    assert "messages" in payload
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "user"
    assert payload["messages"][1]["role"] == "assistant"

    with integration_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.role, m.content
                FROM messages m
                JOIN conversations c ON c.id = m.conversation_id
                WHERE c.report_id = %s
                ORDER BY m.id ASC;
                """,
                (report_id,),
            )
            rows = cur.fetchall()
            cur.execute("DELETE FROM reports WHERE id = %s;", (report_id,))
        conn.commit()

    assert len(rows) >= 2
    assert rows[0]["role"] == "user"
    assert rows[1]["role"] == "assistant"
