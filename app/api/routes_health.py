"""Health and inference-metrics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request

from app.inference.metrics import metrics
from app.models.schemas import HealthResponse

router = APIRouter(tags=["observability"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return request.app.state.services.health()


@router.get("/api/v1/inference/metrics")
def inference_metrics() -> dict:
    """Aggregate inference telemetry: tokens, latency, and backend mix."""
    return metrics.snapshot()
