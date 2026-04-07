from fastapi import FastAPI

app = FastAPI(title="Artifact Worker")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "worker"}
