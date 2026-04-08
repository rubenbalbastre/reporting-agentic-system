
import asyncio
import os

import requests
from dotenv import load_dotenv

from agents import Agent, Runner, function_tool

load_dotenv("../.env")


@function_tool
def call_artifact_worker(content: str) -> str:
    worker_url = os.getenv("ARTIFACT_WORKER_URL", "http://worker:5000")
    endpoint = f"{worker_url.rstrip('/')}/invoke/"
    try:
        response = requests.post(
            endpoint,
            json={"query": content},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("result", "")
    except requests.RequestException as exc:
        return f"Artifact worker request failed: {exc}"


report_assistant = Agent(
    name="Report assistant",
    instructions="You must generate a report to answer ther user's question. You should only respond with the report and nothing else.",
    model="gpt-5.4-nano"
)

def build_main_agent() -> Agent:
    agent = Agent(
        name="Main agent",
        instructions=(
            "You are a helpful assistant which helps users to generate reports based on their questions."
            "To do that, you can call the artifact worker tool, which can answer questions and execute code to generate reports."
            "You should only call the artifact worker tool and never generate a report by yourself."
        ),
        model="gpt-5.4-nano",
        tools=[
            # report_assistant.as_tool(
            #     tool_name="report_assistant",
            #     tool_description="Tool to generate reports based on the user's question."
            # ),
            call_artifact_worker
        ],
    )
    return agent


async def main() -> None:
    agent = build_main_agent()
    result = await Runner.run(agent, "Create a report with the total sales for each product category in the last month.")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
