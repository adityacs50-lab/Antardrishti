"""Engine and session management. SQLite by default; Postgres when DATABASE_URL is set."""

from __future__ import annotations

import logging
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from prahari.core.config import get_settings
from prahari.db.models import Base

log = logging.getLogger("prahari.db")

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None
#: Where the database actually ended up, which may not be where it was asked
#: for. The banner reads this so the path on screen is the truth.
_resolved_db_path: str | None = None


def resolved_db_path() -> str | None:
    return _resolved_db_path


def _sqlite_can_write(path: Path) -> bool:
    """Can SQLite genuinely operate here, not just: can we create a file?

    Cloud-synced folders (OneDrive, Dropbox), SMB shares, some VM folder
    mounts and a few USB filesystems accept ordinary writes but cannot provide
    the byte-range locks SQLite needs. They answer with a bare "disk I/O
    error" that reads like corruption. Since the demo may run from a borrowed
    laptop or a copied folder, this is probed rather than assumed.
    """
    probe = path.parent / f".prahari-probe-{os.getpid()}.db"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(probe)
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        for suffix in ("", "-wal", "-shm", "-journal"):
            try:
                probe.with_name(probe.name + suffix).unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass


def _fallback_db_path(original: Path) -> Path:
    return Path(tempfile.gettempdir()) / "prahari" / original.name


def _configure(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        # Postgres (or anything else) needs none of the SQLite-specific
        # pragma dance below — it has real concurrent-write support already.
        return

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _record):  # noqa: ANN001
        """Set pragmas, tolerating filesystems that cannot do WAL.

        WAL needs shared-memory mapping and real byte-range locks. Network
        shares, some VM folder mounts and a few USB filesystems provide
        neither, and SQLite answers with a bare "disk I/O error" that looks
        like corruption rather than an unsupported mode.

        That matters here specifically because the demo may run from a
        borrowed laptop or a copied folder. So WAL is attempted, and its
        failure downgrades the journal mode instead of taking the app down.
        """
        cur = dbapi_conn.cursor()
        try:
            cur.execute("PRAGMA foreign_keys=ON")
        except Exception:  # noqa: BLE001
            pass
        for mode in ("WAL", "TRUNCATE", "DELETE"):
            try:
                cur.execute(f"PRAGMA journal_mode={mode}")
                break
            except Exception:  # noqa: BLE001
                continue
        cur.close()


def get_engine(url: str | None = None) -> Engine:
    global _engine, _SessionLocal, _resolved_db_path
    if _engine is None or url is not None:
        settings = get_settings()
        target = url or settings.database_url
        connect_args: dict[str, object] = {}
        if target.startswith("sqlite:///") and not target.endswith(":memory:"):
            db_path = Path(target[len("sqlite:///") :])
            db_path.parent.mkdir(parents=True, exist_ok=True)
            if not _sqlite_can_write(db_path):
                alternative = _fallback_db_path(db_path)
                alternative.parent.mkdir(parents=True, exist_ok=True)
                log.warning(
                    "prahari.db: %s cannot host a SQLite database (the filesystem "
                    "does not support the locking SQLite needs — common on synced "
                    "or network folders). Falling back to %s.",
                    db_path.parent,
                    alternative,
                )
                target = f"sqlite:///{alternative}"
                db_path = alternative
            if url is None:
                _resolved_db_path = str(db_path)
            connect_args = {"check_same_thread": False}
        engine = create_engine(target, future=True, connect_args=connect_args)
        _configure(engine)
        if url is not None:
            return engine
        _engine = engine
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def create_all(engine: Engine | None = None) -> None:
    Base.metadata.create_all(engine or get_engine())


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Test hook: drop the cached engine so a new DB URL takes effect."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
