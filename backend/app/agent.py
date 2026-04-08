
import asyncio

import requests
from dotenv import load_dotenv

from agents import Agent, Runner, function_tool

load_dotenv("../.env")


@function_tool
def call_artifact_worker(content: str) -> str:
    response = requests.post(
        "http://localhost:5000/invoke/",
        json={
            "query": content
        }
    )
    return response.json().get("result", "")


report_assistant = Agent(
    name="Report assistant",
    instructions="You must generate a report to answer ther user's question. You should only respond with the report and nothing else.",
    model="gpt-5.4-nano"
)

def build_main_agent() -> Agent:
    agent = Agent(
        name="Reporting agent",
        instructions="You are a reporting agent that generates reports based on user questions. You should use the tools provided to you to generate the report. Always use the tools and never try to answer the question without using the tools.",
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
