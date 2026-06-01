from __future__ import annotations

from pathlib import Path

from app.models import Document
from app.services.html_parser import parse_html


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
_MEMORY_DOCUMENTS: dict[str, Document] = {}


def list_documents() -> list[Document]:
    documents: list[Document] = []
    for path in sorted(data_dir().glob("*.html")):
        raw_html = path.read_text(encoding="utf-8")
        title, text = parse_html(raw_html)
        documents.append(Document(id=path.stem, title=title, text=text, filename=path.name))
    documents.extend(_MEMORY_DOCUMENTS.values())
    return documents


def upsert_document(doc_id: str, title: str, text: str) -> None:
    _MEMORY_DOCUMENTS[doc_id] = Document(
        id=doc_id,
        title=title or "Untitled SOP",
        text=text,
        filename=f"{doc_id}.html",
    )


def data_dir() -> Path:
    return DATA_DIR
