from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    text: str
    filename: str


@dataclass(frozen=True)
class SearchResult:
    id: str
    title: str
    snippet: str
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: dict

    def to_dict(self) -> dict:
        return asdict(self)
