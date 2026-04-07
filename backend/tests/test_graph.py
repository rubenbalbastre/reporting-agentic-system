import asyncio

from app.graph import ReportingAgentGraph


def test_graph_fallback_without_api_key():
    graph = ReportingAgentGraph(api_key="")
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello"},
                ]
            }
        )
    )

    assert "output_text" in result
    assert "Add OPENAI_API_KEY" in result["output_text"]


def test_graph_returns_mocked_openai_output():
    class MockResponse:
        output_text = "Mocked response from graph"

    class MockResponsesClient:
        @staticmethod
        def create(*args, **kwargs):
            return MockResponse()

    class MockOpenAIClient:
        responses = MockResponsesClient()

    graph = ReportingAgentGraph(api_key="")
    graph.openai_client = MockOpenAIClient()

    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Give me a summary"},
                ]
            }
        )
    )

    assert result["output_text"] == "Mocked response from graph"
