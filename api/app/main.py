"""FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .config import get_settings
from .db import sessionmaker
from .llm.providers import get_provider
from .packs.loader import sync_builtin_packs
from .routers import auth, packs, people, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with sessionmaker()() as db:
        await sync_builtin_packs(db)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="PrepRoom API",
        version=__version__,
        lifespan=lifespan,
        description="AI mock-interview platform running on free, open-source models.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.middleware("http")
    async def body_limit(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > s.max_audio_bytes + 1_000_000:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        return await call_next(request)

    for r in (auth.router, packs.router, sessions.router, people.router):
        app.include_router(r)

    @app.get("/api/health", tags=["meta"])
    async def health():
        return {"status": "ok", "version": __version__, "llm": get_provider().name, "stt": s.stt_provider}

    return app


app = create_app()
