"""The Ontology Explorer and Engine Performance card read only real data."""

from __future__ import annotations

import re
from pathlib import Path

from prahari.api.ontology import RULE_CATALOGUE, build_ontology
from prahari.domain.controls import ControlStatus
from prahari.domain.energy import EnergySource
from prahari.domain.lsr import LifeSavingRule

ENGINE_SRC = Path(__file__).resolve().parents[2] / "prahari" / "rules" / "engine.py"


def test_rule_catalogue_matches_the_engine_exactly():
    emitted = set(re.findall(r'rule_id="(R-[A-Z]+-\d+)"', ENGINE_SRC.read_text(encoding="utf-8")))
    assert emitted == {r["id"] for r in RULE_CATALOGUE}


def test_ontology_covers_every_domain_value():
    o = build_ontology()
    assert {e["value"] for e in o["energy_sources"]} == {e.value for e in EnergySource}
    assert {s["value"] for s in o["barrier_states"]} == {s.value for s in ControlStatus}
    assert {r["value"] for r in o["life_saving_rules"]} == {r.value for r in LifeSavingRule}
    protective = [s["value"] for s in o["barrier_states"] if s["protective"]]
    assert protective == ["present_verified"]


def test_ontology_endpoint(api):
    r = api.get("/api/ontology")
    assert r.status_code == 200
    assert r.json()["version"].startswith("engine-")


def test_engine_metrics_endpoint_reports_agreement_from_reviews(api):
    r = api.get("/api/engine-metrics")
    assert r.status_code == 200
    body = r.json()
    bench = body["benchmark"]
    assert bench is not None, "run: python -m prahari.evaluation.metrics"
    pd = bench["splits"]["test"]["precursor_detection"]
    assert 0 <= pd["precision"] <= 1 and 0 <= pd["recall"] <= 1
    agreement = body["reviewer_agreement"]
    assert agreement["confirmed"] + agreement["overridden"] == agreement["reviewed_reports"]
