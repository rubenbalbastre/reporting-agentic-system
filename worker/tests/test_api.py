from fastapi.testclient import TestClient
import pytest
from app.main import app


@pytest.mark.integration
def test_invoke_artifact_worker():
    with TestClient(app) as client:

        response = client.post("/invoke/", json={
            "query": "Write a Python script that prints the current date and time."
        })
        assert response.status_code == 200

