"""Mock observability backend.

In a real deployment these methods would query Prometheus, Loki, Datadog, etc.
Here they read a static snapshot so the demo is fully self-contained while
exposing the same shape an agent tool would consume in production.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import settings


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    )


class TelemetryStore:
    def __init__(self, data: dict) -> None:
        self._services: dict[str, dict] = data.get("services", {})
        self.cluster: str = data.get("cluster", "unknown")
        self.generated_at: str = data.get("generated_at", "")

    @classmethod
    def load(cls, path: str | Path | None = None) -> "TelemetryStore":
        path = Path(path) if path else Path(settings.data_dir) / "sample_telemetry" / "metrics.json"
        if not path.exists():
            return cls({"services": {}})
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def list_services(self) -> list[str]:
        return list(self._services.keys())

    def resolve_service(self, text: str) -> str | None:
        """Best-effort: find a known service name mentioned in free text."""
        text_l = (text or "").lower()
        for name in self._services:
            if name.lower() in text_l:
                return name
        if len(self._services) == 1:
            return next(iter(self._services))
        return None

    def metrics_for(self, service: str) -> dict | None:
        svc = self._services.get(service)
        return svc.get("metrics") if svc else None

    def logs_for(self, service: str) -> list[str]:
        svc = self._services.get(service)
        return svc.get("recent_logs", []) if svc else []
