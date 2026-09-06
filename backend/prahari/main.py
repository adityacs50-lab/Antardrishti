"""prahari backend entrypoint.

100% offline by default. Nothing in this application or anything it imports
makes a network call unless DATABASE_URL points it at a hosted database for a
separate public/cloud demo deployment (see db/session.py and core/config.py).
See CLAUDE.md.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from prahari.api.routes import router
from prahari.db.session import create_all
from prahari.ml.extractor import EXTRACTOR_VERSION
from prahari.rules.engine import ENGINE_VERSION

#: Built frontend, if present. Only exists after `npm run build` in web/ (or
#: a platform build step, e.g. Vercel). Never required for the API itself.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


def _maybe_seed_cloud_db() -> None:
    """First-request bootstrap for a hosted (DATABASE_URL) deployment only.

    Local/offline SQLite runs are seeded explicitly (`make demo`, `cli seed`)
    and this never touches that path. A hosted deployment has no shell to run
    that command from, so if DATABASE_URL is set and the table is empty, seed
    it once here. `seed()` already no-ops safely if reports already exist,
    so a rare double cold-start race is harmless.
    """
    if not os.environ.get("DATABASE_URL"):
        return
    from sqlalchemy import func, select

    from prahari.cli import seed
    from prahari.db.models import Report
    from prahari.db.session import session_scope

    with session_scope() as db:
        existing = db.scalar(select(func.count()).select_from(Report)) or 0
    if existing == 0:
        # Same parameters `make demo` uses (SEED_LIMIT=700), so the
        # accumulation index tells the same story as the local demo.
        seed(700, None, 42, 240, True)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    create_all()
    _maybe_seed_cloud_db()
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


# Serve the built React app (web/dist) directly from this same FastAPI app
# when it has been built — e.g. by a platform build step (Vercel) or a local
# `make build`/`make demo`. API routes above always take priority, so this is
# purely additive: if web/dist doesn't exist (a bare `make api` for backend
# dev), nothing changes.
if _FRONTEND_DIST.is_dir():
    app.frontend("/", directory=str(_FRONTEND_DIST))
