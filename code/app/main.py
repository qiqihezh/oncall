from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from app.routes import v1, v2, v3


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def create_app() -> FastAPI:
    app = FastAPI(title="On-Call Assistant", version="0.1.0")
    app.mount("/static", StaticFiles(directory=ROOT_DIR / "app" / "static"), name="static")

    app.include_router(v1.router)
    app.include_router(v2.router)
    app.include_router(v3.router)

    @app.get("/")
    def index() -> dict[str, str]:
        return {"message": "On-Call Assistant", "start": "/v1"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
