"""Runtime configuration. Everything defaults to something that works offline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    models_dir: Path
    data_dir: Path
    corpus_path: Path

    @property
    def database_url(self) -> str:
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
