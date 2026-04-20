from contextlib import asynccontextmanager

from fastapi import FastAPI
from langfuse import get_client
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor


def _log_langfuse_readiness() -> None:
    """Log whether Langfuse is reachable without blocking app startup."""
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
    """Initialize tracing/instrumentation for the backend application lifespan."""
    OpenAIAgentsInstrumentor().instrument()
    _log_langfuse_readiness()

    yield

    print("Shutting down worker...")
