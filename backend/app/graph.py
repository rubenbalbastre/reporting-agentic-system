import os
from typing import Any, TypedDict
from xml.parsers.expat import model

from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from openai import OpenAI


class ReportingAgentGraphState(TypedDict, total=False):
    messages: list[dict[str, str]]
    output_text: str


class LLMCallNode:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = init_chat_model(client=self.client, model="gpt-3.5-turbo")

    async def __call__(self, state: ReportingAgentGraphState) -> ReportingAgentGraphState:
        messages = state.get("messages", [])
        response = await self.model.ainvoke(
            input=messages,
        )
        output_text = (response.output_text or "").strip()
        if not output_text:
            output_text = "I could not generate a response."
        return {"output_text": output_text}



class ReportingAgentGraph:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.graph = None
        self.compiled_graph = None
        self._build_graph()
        self._compile_graph()

    async def ainvoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return await self.compiled_graph.ainvoke(input_data)

    def _compile_graph(self) -> None:
        self.compiled_graph = self.graph.compile()

    def _build_graph(self) -> StateGraph:

        graph = StateGraph(ReportingAgentGraphState)
        graph.add_node("llm_call", LLMCallNode(api_key=self.api_key))
        graph.add_edge(START, "llm_call")
        graph.add_edge("llm_call", END)
        self.graph = graph
        return graph
