"""prahari backend entrypoint.

100% offline. Nothing in this application or anything it imports makes a
network call. See CLAUDE.md.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prahari.api.routes import router
from prahari.db.session import create_all
from prahari.ml.extractor import EXTRACTOR_VERSION
from prahari.rules.engine import ENGINE_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    create_all()
    # Judges should be able to see which extraction path is live without
    # opening a terminal tab or trusting a claim on a slide.
    from prahari.core.banner import print_banner

    print_banner()
    yield


app = FastAPI(
    title="prahari",
    description=(
        "Offline SIF precursor detection for oil & gas safety reports. "
        "Neuro-symbolic: the model extracts facts, a deterministic rule engine "
        "decides, and every verdict cites a named rule and exact character spans."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Local dev only. No auth by design - this is a demo prototype.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, object]:
    """Liveness plus provenance: which path is running, and on how much data."""
    from prahari.core.banner import collect, count_reports

    facts = collect(count_reports())
    return {
        "status": "ok",
        "engine_version": ENGINE_VERSION,
        "extractor_version": EXTRACTOR_VERSION,
        "offline": "true",
        "extractor": facts.extractor,
        "extractor_detail": facts.extractor_detail,
        "model_present": facts.model_present,
        "report_count": facts.report_count,
    }
