"""Shared fixtures. Every test runs against a throwaway SQLite file."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date, timedelta

import pytest

pytest.importorskip("fastapi")


@pytest.fixture()
def api(tmp_path, monkeypatch) -> Iterator:
    """A TestClient bound to a fresh database."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("PRAHARI_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("PRAHARI_DATA_DIR", str(tmp_path))

    from prahari.db import session as session_module

    session_module.reset_engine()
    from prahari.main import app

    with TestClient(app) as client:
        yield client
    session_module.reset_engine()


HIGH_ENERGY_UNCONTROLLED = (
    "On 12.08.2026, Sri B. Gogoi (roustabout) was working at monkey board at approx "
    "8 mtr height at Rig No. 12. He was not wearing safety belt. He lost balance and "
    "slipped. No injury occurred."
)
# Note the stated height. The engine establishes high energy from a published
# cue or a measured magnitude; a report that never says how high the work was
# cannot be recognised as high-energy, which is a real limitation of the v0
# extractor and is documented in docs/DOMAIN.md.
HIGH_ENERGY_CONTROLLED = (
    "During work at height at 6 mtr at Rig No. 9, full body harness was worn and "
    "double lanyard was anchored to the certified anchor point, checked by TP before "
    "start. The arrangement was observed during the site round. There was no injury "
    "to any personnel."
)
LOW_ENERGY_INJURY = (
    "Sri R. Das (fitter) was cutting GI sheet at the workshop. Hand gloves were not "
    "worn while doing the job. The blade slipped and he sustained a cut on the left "
    "index finger. First aid was given at the installation."
)
VAGUE = "Unsafe act observed at Duliajan. Workman was careless during the job. Advised."


def post_report(client, text: str, *, site="Naoholia", day: date | None = None, **kw):
    payload = {
        "text": text,
        "site": site,
        "date": (day or date.today()).isoformat(),
        "reporter_role": "Safety Officer",
    }
    payload.update(kw)
    return client.post("/api/reports", json=payload)


def seed_repeats(client, *, site="Baghjan", n=5, days_apart=10):
    """Ingest the same uncontrolled high-energy scenario repeatedly at one site."""
    today = date.today()
    ids = []
    for i in range(n):
        r = post_report(
            client,
            HIGH_ENERGY_UNCONTROLLED,
            site=site,
            day=today - timedelta(days=i * days_apart),
            activity="working at height",
        )
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    return ids
