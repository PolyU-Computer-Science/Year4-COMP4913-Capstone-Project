"""FastAPI application for the email assistant."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import cases, emails, settings, stats

load_dotenv(override=False)

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    """Build the FastAPI application with CORS and routers."""
    app = FastAPI(
        title="Email Assistant API",
        description="Backend API for the agentic AI email assistant.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(emails.router)
    app.include_router(cases.router)
    app.include_router(stats.router)
    app.include_router(settings.router)

    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    """Run the API server with uvicorn."""
    import uvicorn

    from email_assistant.core.settings_store import SettingsStore

    SettingsStore().ensure_default_ai_config()

    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=True)
