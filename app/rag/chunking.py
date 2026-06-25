"""Text chunking for the RAG indexer.

Splits documents on paragraph boundaries, packs paragraphs up to ``chunk_size``
characters, and prepends a short overlap from the previous chunk so context is
preserved across boundaries.
"""
from __future__ import annotations

import re

_PARA_RE = re.compile(r"\n\s*\n")


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    paragraphs = [p.strip() for p in _PARA_RE.split(text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if current and len(current) + len(para) + 1 > chunk_size:
            chunks.append(current)
            current = ""
        if len(para) > chunk_size:
            # Hard-split an oversized paragraph.
            if current:
                chunks.append(current)
                current = ""
            step = max(1, chunk_size - overlap)
            for i in range(0, len(para), step):
                chunks.append(para[i : i + chunk_size])
        else:
            current = f"{current}\n{para}".strip() if current else para

    if current:
        chunks.append(current)

    if overlap > 0 and len(chunks) > 1:
        overlapped: list[str] = []
        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped.append(chunk)
            else:
                tail = chunks[i - 1][-overlap:]
                overlapped.append(f"{tail}\n{chunk}")
        chunks = overlapped

    return chunks
