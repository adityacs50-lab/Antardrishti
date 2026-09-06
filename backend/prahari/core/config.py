"""Runtime configuration. Everything defaults to something that works offline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize_database_url(url: str) -> str:
    """Make a Postgres URL SQLAlchemy-ready.

    Hosted Postgres providers (Neon/Vercel, Railway, Render, ...) commonly
    hand out `postgres://` or bare `postgresql://` connection strings. Both
    work fine with psycopg2, but this project installs `psycopg` (v3) for its
    binary wheels, so the URL needs the `+psycopg` driver marker or SQLAlchemy
    will try to import psycopg2 and fail on a machine that doesn't have it.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    models_dir: Path
    data_dir: Path
    corpus_path: Path

    @property
    def database_url(self) -> str:
        # Offline by default: a local SQLite file, exactly as always. Set
        # DATABASE_URL (e.g. to a hosted Postgres instance) only for a
        # separate public/cloud demo deployment — never required to run the
        # app itself, which stays 100% local-first.
        override = os.environ.get("DATABASE_URL")
        if override:
            return _normalize_database_url(override)
        return f"sqlite:///{self.db_path}"


def get_settings() -> Settings:
    root = _repo_root()
    data_dir = Path(os.environ.get("PRAHARI_DATA_DIR", root / "data"))
    return Settings(
        db_path=Path(os.environ.get("PRAHARI_DB_PATH", data_dir / "prahari.db")),
        models_dir=Path(os.environ.get("PRAHARI_MODELS_DIR", root / "models")),
        data_dir=data_dir,
        corpus_path=Path(
            os.environ.get("PRAHARI_CORPUS_PATH", data_dir / "synthetic_reports.jsonl")
        ),
    )
