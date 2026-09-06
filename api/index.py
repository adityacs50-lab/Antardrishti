"""Vercel entrypoint.

Vercel's Python runtime detects Serverless Functions under api/. It expects
a FastAPI instance named `app` here. The real application still lives in
backend/prahari/main.py exactly as it does for local development (`make
demo`, `make api`) — this file only makes that package importable from
Vercel's function root.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from prahari.main import app  # noqa: E402  (import after sys.path fix, by design)

__all__ = ["app"]
