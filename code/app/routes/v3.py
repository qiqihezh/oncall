from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, Request
from fastapi.templating import Jinja2Templates

from app.services import agent


ROOT_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=ROOT_DIR / "app" / "templates")
router = APIRouter(prefix="/v3", tags=["phase-3"])


@router.get("")
def page(request: Request):
    return templates.TemplateResponse(request, "v3.html")


@router.post("/chat")
def chat(body: dict = Body(default_factory=dict)) -> dict:
    message = str(body.get("message", "")).strip()
    return agent.reply(message)
