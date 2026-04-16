import os
from pathlib import Path
from fastapi import FastAPI, Request
from agents import Runner
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from langfuse import get_client
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from opentelemetry.propagate import extract
from opentelemetry.context import attach, detach

from app.agents.code_executor_agent import build_code_executor_agent
from app.schemas import InvokeRequest


def _log_langfuse_readiness() -> None:
    langfuse = get_client()
    try:
        if langfuse.auth_check():
            print("Langfuse client is authenticated and ready!")
        else:
            print("Langfuse authentication failed. Continuing without blocking startup.")
    except Exception as exc:
        print(f"Langfuse check failed ({exc}). Continuing startup without Langfuse readiness check.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup logic ---
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    OpenAIAgentsInstrumentor().instrument()
    _log_langfuse_readiness()

    yield  # <-- app is running here

    # --- shutdown logic (optional) ---
    print("Shutting down worker...")


app = FastAPI(title="Artifact Worker", lifespan=lifespan)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "worker"}


@app.post("/invoke")
async def invoke(request: InvokeRequest, http_request: Request) -> dict:
    parent_context = extract(dict(http_request.headers))
    context_token = attach(parent_context)

    try:
        session_id = f"report_{request.report_id}"
        workspace_root = Path(os.getenv("WORKSPACE_ROOT", "/data/shared/jobs"))
        workspace_dir = str(workspace_root / session_id)

        code_agent = build_code_executor_agent(workspace_dir=workspace_dir)

        # run code agent
        result = await Runner.run(code_agent, request.query)
        result = result.final_output

        if result.status == "needs_more_info":
            out = result.clarification_question + "\nMissing information: " + ", ".join(result.missing_information)
        elif result.status == "ready_to_execute":
            out = result.summary
            
        return {"result": out, "session_id": session_id}
    finally:
        detach(context_token)


if __name__ == "__main__":
    if os.getenv("APP_ENV") != "docker":
        load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")
        
    from fastapi.testclient import TestClient

    with TestClient(app) as client:

        response = client.post("/invoke", json={
            "query": "Can you answer questions about total sales by product category for january 2017? Provide me a first result. If you need more information to answer, ask me for it later.",
            "report_id": 501,
        })
        print(response.status_code)
        print(response.json())
