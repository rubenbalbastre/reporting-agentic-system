import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.reports import router as reports_router
from app.api.routes.skills import router as skills_router
from app.core.lifespan import lifespan

app = FastAPI(title="Chat Reports Backend", lifespan=lifespan)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3001")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router)
app.include_router(skills_router)
app.include_router(health_router)


if __name__ == "__main__":
    from dotenv import load_dotenv
    from fastapi.testclient import TestClient

    if os.getenv("APP_ENV") != "docker":
        load_dotenv(Path(__file__).resolve().parents[2] / ".env.local")

    with TestClient(app) as client:
        response = client.get("/health")
        print(response.status_code)
        print(response.json())
