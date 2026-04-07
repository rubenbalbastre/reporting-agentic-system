import os
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI


class ReportingAgentGraphState(TypedDict, total=False):
    messages: list[dict[str, str]]
    output_text: str


class ReportingAgentGraph:
    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        self.model_name = model_name or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.graph = None
        self.compiled_graph = None
        self._build_graph()
        self._compile_graph()

    async def ainvoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return await self.compiled_graph.ainvoke(input_data)

    def _compile_graph(self) -> None:
        self.compiled_graph = self.graph.compile()

    def _build_graph(self) -> StateGraph:
        async def llm_call(state: ReportingAgentGraphState) -> ReportingAgentGraphState:
            messages = state.get("messages", [])
            if not self.openai_client:
                return {"output_text": "I stored your message. Add OPENAI_API_KEY to enable AI responses."}

            response = self.openai_client.responses.create(
                model=self.model_name,
                input=messages,
            )
            output_text = (response.output_text or "").strip()
            if not output_text:
                output_text = "I could not generate a response."
            return {"output_text": output_text}

        graph = StateGraph(ReportingAgentGraphState)
        graph.add_node("llm_call", llm_call)
        graph.add_edge(START, "llm_call")
        graph.add_edge("llm_call", END)
        self.graph = graph
        return graph
