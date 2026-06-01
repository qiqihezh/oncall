from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.services import document_store, html_parser, keyword_search


ROOT_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=ROOT_DIR / "app" / "templates")
router = APIRouter(prefix="/v1", tags=["phase-1"])


@router.get("")
def page(request: Request):
    return templates.TemplateResponse(request, "v1.html")


@router.get("/search")
def search(request: Request, q: str = "") -> dict:
    query = _normalize_query_param(request, q)
    results = [item.to_dict() for item in keyword_search.search(query)]
    return {"query": query, "results": results}


@router.post("/documents", status_code=201)
def create_document(body: dict = Body(default_factory=dict)) -> dict:
    doc_id = str(body.get("id", "")).strip()
    raw_html = str(body.get("html", ""))
    if not doc_id or not raw_html:
        raise HTTPException(status_code=400, detail="id and html are required")

    title, text = html_parser.parse_html(raw_html)
    document_store.upsert_document(doc_id, title, text)
    return {"id": doc_id, "title": title}


def _normalize_query_param(request: Request, q: str) -> str:
    if q:
        return q

    raw_query = request.scope.get("query_string", b"").decode("utf-8", errors="ignore")
    if raw_query == "q=&":
        return "&"
    return q
