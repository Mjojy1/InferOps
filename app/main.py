"""InferOps FastAPI application entrypoint.

Run locally:
    uvicorn app.main:app --reload --port 8000

The app indexes the runbook knowledge base on startup and serves a small web UI
at ``/`` plus a JSON API under ``/api/v1``.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api import routes_chat, routes_health, routes_ingest
from app.config import settings
from app.services import Services
from app.telemetry.observability import setup_logging

logger = logging.getLogger("inferops")

BASE_DIR = Path(__file__).resolve().parent.parent
UI_DIR = BASE_DIR / "ui"


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    services = Services()
    documents, chunks = services.ingest()
    logger.info(
        "InferOps ready | backend=%s | indexed %d runbooks into %d chunks",
        services.router.active_backend,
        documents,
        chunks,
    )
    app.state.services = services
    yield


app = FastAPI(
    title="InferOps",
    description=(
        "A local-inference DevOps/Observability copilot. RAG over SRE runbooks + an "
        "autonomous tool-calling agent for incident triage."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(routes_health.router)
app.include_router(routes_ingest.router)
app.include_router(routes_chat.router)

if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/ui/")
