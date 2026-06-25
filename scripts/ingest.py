"""Index (or re-index) the runbook knowledge base into the vector store.

Usage:
    python -m scripts.ingest [path/to/runbooks]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import Services  # noqa: E402


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else None
    services = Services()
    documents, chunks = services.ingest(path)
    print(
        f"Indexed {documents} runbooks into {chunks} chunks "
        f"using the '{services.embedder.backend}' embedding backend."
    )


if __name__ == "__main__":
    main()
