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

from app.code_planner_agent import build_code_planner_agent
from app.code_executor_agent import build_code_executor_agent
from app.schemas import InvokeRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup logic ---
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    OpenAIAgentsInstrumentor().instrument()

    langfuse = get_client()
    if langfuse.auth_check():
        print("Langfuse client is authenticated and ready!")
    else:
        print("Authentication failed. Please check your credentials and host.")

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

        planner_code_agent = build_code_planner_agent()
        code_executor_agent = build_code_executor_agent(workspace_dir=workspace_dir)

        # get plan
        plan_result = await Runner.run(planner_code_agent, request.query)
        plan_result = plan_result.final_output

        #  ask more info
        if plan_result.status == "needs_more_info":
            out = plan_result.clarification_question + "\nMissing information: " + ", ".join(plan_result.missing_information)
        
        # execute plan
        elif plan_result.status == "ready_to_execute":
            steps_text = "\n".join(step.model_dump_json() for step in plan_result.steps)
            skills_text = ", ".join(plan_result.skills_to_apply) if plan_result.skills_to_apply else "(none)"
            notes_text = plan_result.skill_notes or "No specific skill notes."
            executor_input = (
                f"User request:\n{request.query}\n\n"
                f"Skills to apply:\n{skills_text}\n\n"
                f"Skill notes:\n{notes_text}\n\n"
                f"Plan steps:\n{steps_text}"
            )
            execution_result = await Runner.run(code_executor_agent, executor_input, max_turns=30)
            out = execution_result.final_output
            
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
