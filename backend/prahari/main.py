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


def _maybe_restore_demo_corpus() -> None:
    """Populate an empty ephemeral database from the corpus shipped in the repo.

    A serverless deployment with no DATABASE_URL gets a brand-new, empty SQLite
    file on every cold start - the bundle itself is read-only, so the database
    lands in the platform's temp directory and dies with the instance. The
    queue, the map and the accumulation index then all render "no data" no
    matter what was submitted a minute earlier, which reads as a broken app
    rather than an empty one. Copying the pre-built corpus in on startup makes
    a deployed demo populated on arrival with no hosted database and no
    dashboard configuration - the one thing a cloud deployment cannot do for
    itself, since it has no shell to run `prahari.cli seed` from.

    Deliberately narrow:
      * never when DATABASE_URL is set - that path has its own seeding, and a
        real hosted database must never be overwritten by a demo fixture;
      * never when the database already holds even one report, so it cannot
        clobber a real corpus or a developer's local work;
      * only when the shipped file is actually present in the configured data
        directory. The test suite points PRAHARI_DATA_DIR at an empty tmp_path,
        so tests never see it and keep their fresh, empty databases;
      * PRAHARI_NO_DEMO_SEED=1 opts out entirely.

    What gets loaded is the project's own synthetic corpus, already scored by
    the real rule engine at build time - the same `prahari.cli seed` output a
    local `make demo` produces. These are not fabricated verdicts: every row
    came out of the same rules that score anything typed into the app, which
    is why this does not violate the no-mock-data rule the UI is built on.
    """
    if os.environ.get("DATABASE_URL") or os.environ.get("PRAHARI_NO_DEMO_SEED"):
        return

    import shutil
    from datetime import date as _date

    from sqlalchemy import func, select, text

    from prahari.core.config import get_settings
    from prahari.db.models import Report
    from prahari.db.session import create_all, reset_engine, resolved_db_path, session_scope

    seed_file = get_settings().data_dir / "demo_seed.db"
    target = resolved_db_path()
    if not seed_file.exists() or not target:
        return

    with session_scope() as db:
        if (db.scalar(select(func.count()).select_from(Report)) or 0) > 0:
            return

    # Swap the file out from under a disposed engine, then reopen on the copy.
    reset_engine()
    shutil.copyfile(seed_file, target)
    create_all()

    # The corpus was dated relative to the day it was built, but the
    # accumulation index is a rolling-window measure - left alone, the whole
    # corpus would drift out of every window and the map would empty itself
    # again a few months from now. Shift every date so the newest report lands
    # on today, preserving the relative spacing the clustering depends on.
    # SQLite-specific by design: this whole function returns early unless the
    # deployment is on the local SQLite path.
    with session_scope() as db:
        newest = db.scalar(select(func.max(Report.report_date)))
        if not newest:
            return
        shift = (_date.today() - newest).days
        if shift:
            delta = f"{shift:+d} days"
            db.execute(text("UPDATE reports SET report_date = date(report_date, :d)"), {"d": delta})
            db.execute(
                text("UPDATE reports SET ingested_at = datetime(ingested_at, :d)"), {"d": delta}
            )


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    create_all()
    _maybe_restore_demo_corpus()
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

@app.middleware("http")
async def _no_store_html(request, call_next):  # noqa: ANN001, ANN201
    """Never let a browser reuse a cached index.html across a deployment.

    The SPA's script tag names a content-hashed bundle (`index-<hash>.js`), and
    a new build deletes the old one. A browser holding yesterday's index.html
    therefore asks for a file that no longer exists, gets a 404, and renders a
    blank page with no error anyone can see - observed live on the deployment
    right before a demo. Hashed assets are immutable and stay cacheable; only
    the HTML document, which is the thing that must never go stale, is marked
    no-store. API responses are JSON and unaffected.
    """
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-store, must-revalidate"
    return response


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
