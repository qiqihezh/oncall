from __future__ import annotations

import re

from app.models import SearchResult
from app.services import document_store


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]|[^\s]")


def search(query: str) -> list[SearchResult]:
    normalized = query.strip().lower()
    if not normalized:
        return []

    results: list[SearchResult] = []
    for doc in document_store.list_documents():
        haystack = f"{doc.title} {doc.text}"
        lowered = haystack.lower()
        index = lowered.find(normalized)
        if index == -1:
            continue

        title_hits = doc.title.lower().count(normalized)
        body_hits = doc.text.lower().count(normalized)
        score = 1.0 + title_hits * 2.0 + body_hits * 0.2
        results.append(
            SearchResult(
                id=doc.id,
                title=doc.title,
                snippet=_snippet(haystack, index, len(query.strip())),
                score=round(score, 3),
            )
        )

    return sorted(results, key=lambda item: (-item.score, item.id))


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


def _snippet(text: str, index: int, query_length: int, radius: int = 60) -> str:
    start = max(index - radius, 0)
    end = min(index + max(query_length, 1) + radius, len(text))
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"
