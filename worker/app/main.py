import asyncio
from fastapi import FastAPI
from code_agent import build_code_executor_agent, build_code_planner_agent
from agents import Runner


app = FastAPI(title="Artifact Worker")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "worker"}


@app.post("invoke/")
async def invoke(request: dict) -> dict:
    planner_code_agent = build_code_planner_agent()
    code_executor_agent = build_code_executor_agent()

    # get plan
    plan_result = await Runner.run(planner_code_agent, request["query"])
    plan_result = plan_result.final_output

    #  ask more info
    if plan_result.status == "needs_more_info":
        out = plan_result.clarification_question + "\nMissing information: " + ", ".join(plan_result.missing_information)
    
    # execute plan
    elif plan_result.status == "ready_to_execute":
        steps_text = "\n".join(step.model_dump_json() for step in plan_result.steps)
        execution_result = await Runner.run(code_executor_agent, steps_text)
        out = execution_result.final_output
        
    return {"result": out}


if __name__ == "__main__":
    # make a test call to the worker
    test_request = {"query": "Write a Python script that prints the current date and time."}
    response = asyncio.run(invoke(test_request))
    print(response)