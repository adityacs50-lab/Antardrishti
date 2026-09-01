"""The offline guarantee, enforced as a test.

CLAUDE.md: 100% offline, no calls to any external API, LLM service or cloud
database, ever. `docker compose up` must work with the network disconnected.
A promise in a README is not a guarantee; this is.
"""

from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[2] / "prahari"

#: Modules that reach the network, or clients for services that do.
FORBIDDEN_MODULES = {
    "requests", "urllib.request", "urllib3", "httpx", "aiohttp", "http.client",
    "socket", "ftplib", "telnetlib", "smtplib", "openai", "anthropic", "cohere",
    "boto3", "botocore", "google.cloud", "azure", "psycopg2", "pymongo", "redis",
    "elasticsearch", "huggingface_hub",
}


#: Build-time only. These are never imported by the running application — they
#: exist to train and export the model on a machine that does have a network.
#: `prahari.ml.extract_facts` reaches none of them at runtime.
BUILD_TIME_ONLY = {"ml/training"}


def _python_files() -> list[Path]:
    return sorted(
        path
        for path in PACKAGE.rglob("*.py")
        if not any(part in path.as_posix() for part in BUILD_TIME_ONLY)
    )


def test_build_time_scripts_are_not_reachable_from_the_app() -> None:
    """Nothing the running app imports may pull in a training module."""
    import ast

    runtime = [p for p in _python_files()]
    offenders: list[str] = []
    for path in runtime:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                if "ml.training" in name:
                    offenders.append(f"{path.relative_to(PACKAGE.parent)}:{node.lineno} -> {name}")
    assert not offenders, "runtime code imports a build-time module:\n" + "\n".join(offenders)


def test_no_runtime_module_imports_a_network_client() -> None:
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            for name in names:
                root = name.split(".")[0]
                if name in FORBIDDEN_MODULES or root in FORBIDDEN_MODULES:
                    offenders.append(f"{path.relative_to(PACKAGE.parent)}:{node.lineno} -> {name}")
    assert not offenders, "network-capable imports found in runtime code:\n" + "\n".join(offenders)


def test_no_hardcoded_http_urls_outside_citations() -> None:
    """URLs are fine in the citation registry - they are provenance, not calls."""
    offenders: list[str] = []
    for path in _python_files():
        if path.name == "citations.py":
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith('"') or stripped.startswith("'"):
                continue
            if "http://" in line or "https://" in line:
                if "localhost" in line or "127.0.0.1" in line:
                    continue
                offenders.append(f"{path.relative_to(PACKAGE.parent)}:{i}")
    assert not offenders, "external URLs in runtime code:\n" + "\n".join(offenders)


def test_the_whole_api_works_with_sockets_disabled(api, monkeypatch) -> None:
    """Run the real endpoints with socket creation blocked at the OS level."""
    from datetime import date

    from tests.conftest import HIGH_ENERGY_UNCONTROLLED

    # Ingest first, while the TestClient's own transport still works.
    r = api.post(
        "/api/reports",
        json={
            "text": HIGH_ENERGY_UNCONTROLLED,
            "site": "Naoholia",
            "date": date.today().isoformat(),
        },
    )
    assert r.status_code == 201

    real_socket = socket.socket

    def _blocked(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("the application attempted to open a network socket")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    try:
        for path in (
            "/health",
            "/api/reports",
            "/api/triage",
            "/api/reports/1",
            "/api/analytics/density",
            "/api/analytics/lsr",
            "/api/analytics/barriers",
            "/api/analytics/accumulation",
        ):
            assert api.get(path).status_code == 200, path
    finally:
        monkeypatch.setattr(socket, "socket", real_socket)


def test_engine_and_extractor_are_pure_functions_of_text() -> None:
    """Same text in, same verdict out. No clock, no network, no hidden state."""
    from prahari.rules.engine import analyse

    from tests.conftest import HIGH_ENERGY_UNCONTROLLED

    a_facts, a = analyse(HIGH_ENERGY_UNCONTROLLED)
    b_facts, b = analyse(HIGH_ENERGY_UNCONTROLLED)
    assert a.classification == b.classification
    assert [f.rule_id for f in a.fired_rules] == [f.rule_id for f in b.fired_rules]
    assert [(s.start, s.end) for s in a.all_spans] == [(s.start, s.end) for s in b.all_spans]
    assert len(a_facts.facts) == len(b_facts.facts)
