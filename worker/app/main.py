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

from app.agents.code_agent import build_code_agent
from app.schemas import InvokeRequest


def _log_langfuse_readiness() -> None:
    """Log whether Langfuse is reachable without failing worker startup."""
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
    """Initialize environment and tracing for the worker application lifespan."""
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
    """Return a minimal worker health payload."""
    return {"status": "ok", "service": "worker"}


@app.post("/invoke")
async def invoke(request: InvokeRequest, http_request: Request) -> dict:
    """Run the worker code agent inside a validated report or skill workspace."""
    parent_context = extract(dict(http_request.headers))
    context_token = attach(parent_context)

    try:
        workspace_root = Path(os.getenv("WORKSPACE_ROOT", "/data/shared/jobs")).resolve()
        skills_root = Path(os.getenv("MAIN_AGENT_SKILLS_ROOT", "/data/shared/skills")).resolve()
        skills_drafts_root = Path(os.getenv("MAIN_AGENT_SKILLS_DRAFTS_ROOT", "/data/shared/skills_drafts")).resolve()

        # Skill tasks must always run in an explicit drafts workspace.
        if request.task_type == "skill":
            if not request.workspace_path:
                return {
                    "result": "Invalid skill request: workspace_path is required",
                    "session_id": "invalid",
                }
            skill_path = Path(request.workspace_path).resolve()
            if not (skill_path == skills_drafts_root or skills_drafts_root in skill_path.parents):
                return {
                    "result": "Invalid skill request: workspace_path must be under skills_drafts root",
                    "session_id": "invalid",
                }
            workspace_dir = str(skill_path)
            session_id = skill_path.name
        elif request.workspace_path:
            workspace_path = Path(request.workspace_path).resolve()
            is_under_workspace = workspace_path == workspace_root or workspace_root in workspace_path.parents
            is_under_skills = workspace_path == skills_root or skills_root in workspace_path.parents
            is_under_skill_drafts = workspace_path == skills_drafts_root or skills_drafts_root in workspace_path.parents
            if not (is_under_workspace or is_under_skills or is_under_skill_drafts):
                return {
                    "result": "Invalid workspace_path: must be under workspace, skills, or skills_drafts root",
                    "session_id": "invalid",
                }
            workspace_dir = str(workspace_path)
            session_id = workspace_path.name
        else:
            session_id = request.session_id or f"report_{request.report_id}"
            workspace_dir = str(workspace_root / session_id)

        code_agent = build_code_agent(workspace_dir=workspace_dir, task_type=request.task_type)

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
