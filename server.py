"""Vercel entrypoint.

Vercel's Python runtime auto-detects a FastAPI `app` instance at this file
(one of its supported entrypoint names). It does nothing else: the real
application lives in backend/prahari/main.py exactly as it does for local
development (`make demo`, `make api`). This file only makes that package
importable from the repo root, which is where Vercel expects the entrypoint.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from prahari.main import app  # noqa: E402  (import after sys.path fix, by design)

__all__ = ["app"]
