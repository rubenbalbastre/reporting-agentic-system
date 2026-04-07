from fastapi import FastAPI

app = FastAPI(title="Agentic Analytics Backend")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "backend"}
