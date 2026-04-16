import os
import requests
from agents import Agent, function_tool
from opentelemetry.propagate import inject
from app.agents.report_agent import build_report_agent
from app.agents.prompts import build_main_agent_instructions


def build_main_agent(report_id: int) -> Agent:
    @function_tool
    def call_artifact_worker(content: str) -> str:
        worker_url = os.getenv("ARTIFACT_WORKER_URL", "http://worker:5000")
        endpoint = f"{worker_url.rstrip('/')}/invoke"
        headers: dict[str, str] = {}
        inject(headers)
        try:
            response = requests.post(
                endpoint,
                json={"query": content, "report_id": report_id},
                headers=headers,
                timeout=300,
            )
            response.raise_for_status()
            return response.json().get("result", "")
        except requests.RequestException as exc:
            return f"Artifact worker request failed: {exc}"

    agent = Agent(
        name="main_agent",
        instructions=build_main_agent_instructions(),
        model="gpt-5.4-mini",
        tools=[
            build_report_agent(report_id=report_id).as_tool(
                tool_name="report_agent",
                tool_description="Tool to generate reports based on the user's question and results from the artifact worker."
            ),
            call_artifact_worker,
        ],
    )
    return agent
