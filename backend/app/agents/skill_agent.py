import os
import requests
from agents import Agent, function_tool
from opentelemetry.propagate import inject

from app.agents.prompts import build_skill_agent_instructions


def build_skill_agent(skill_session_id: str, workspace_path: str) -> Agent:
    @function_tool
    def call_skill_code_worker(content: str) -> str:
        if not workspace_path:
            return "Skill code worker request failed: workspace_path is required for skill flows"
        worker_url = os.getenv("ARTIFACT_WORKER_URL", "http://worker:5000")
        endpoint = f"{worker_url.rstrip('/')}/invoke"
        headers: dict[str, str] = {}
        inject(headers)
        try:
            response = requests.post(
                endpoint,
                json={
                    "query": content,
                    "session_id": skill_session_id,
                    "workspace_path": workspace_path,
                    "task_type": "skill",
                },
                headers=headers,
                timeout=300,
            )
            response.raise_for_status()
            return response.json().get("result", "")
        except requests.RequestException as exc:
            return f"Skill code worker request failed: {exc}"

    return Agent(
        name="skill_agent",
        instructions=build_skill_agent_instructions(),
        model="gpt-5.4-mini",
        tools=[call_skill_code_worker],
    )
