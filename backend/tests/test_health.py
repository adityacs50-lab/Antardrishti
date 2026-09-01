"""Placeholder test - verifies the scaffold's health endpoint responds.

Skipped when FastAPI is not installed, so the domain and data test suites can
be run without pulling the whole backend dependency set.
"""

import pytest

fastapi_testclient = pytest.importorskip(
    "fastapi.testclient", reason="FastAPI not installed; run pip install -e '.[dev]'"
)

from prahari.main import app  # noqa: E402

client = fastapi_testclient.TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["offline"] == "true"
    assert body["engine_version"]
    assert body["extractor_version"]
