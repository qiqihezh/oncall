from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.services import semantic_search


ROOT_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=ROOT_DIR / "app" / "templates")
router = APIRouter(prefix="/v2", tags=["phase-2"])


@router.get("")
def page(request: Request):
    return templates.TemplateResponse(request, "v2.html")


@router.get("/search")
def search(q: str = "") -> dict:
    results = [item.to_dict() for item in semantic_search.search(q)]
    return {"query": q, "results": results}
