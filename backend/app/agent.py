
import asyncio
import os
import requests
from agents import Agent, Runner, function_tool
from app.report_agent import build_report_agent


def build_main_agent(report_id: int) -> Agent:
    @function_tool
    def call_artifact_worker(content: str) -> str:
        worker_url = os.getenv("ARTIFACT_WORKER_URL", "http://worker:5000")
        endpoint = f"{worker_url.rstrip('/')}/invoke/"
        try:
            response = requests.post(
                endpoint,
                json={"query": content, "report_id": report_id},
                timeout=300,
            )
            response.raise_for_status()
            return response.json().get("result", "")
        except requests.RequestException as exc:
            return f"Artifact worker request failed: {exc}"

    agent = Agent(
        name="Main agent",
        instructions=(
            "You are a helpful assistant which helps users to generate reports based on their questions."
            "To do that, you can call:"
            "* the artifact worker tool, which can answer questions and execute code to generate artifacts like images or tables."
            "* the report agent, which can create and update a markdown report based on the user's question and results from the artifact worker."
        ),
        model="gpt-5.4-nano",
        tools=[
            build_report_agent(report_id=report_id).as_tool(
                tool_name="Report Agent",
                tool_description="Tool to generate reports based on the user's question and results from the artifact worker."
            ),
            call_artifact_worker
        ],
    )
    return agent


async def main() -> None:
    agent = build_main_agent(report_id=1)
    result = await Runner.run(agent, "Create a report with the total sales for each product category in the last month.")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
