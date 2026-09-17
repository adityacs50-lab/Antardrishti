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


def test_future_dated_report_is_rejected(api):
    from datetime import date, timedelta

    r = api.post(
        "/api/reports",
        json={"text": "Guard missing on pump.", "site": "Moran",
              "date": (date.today() + timedelta(days=30)).isoformat()},
    )
    assert r.status_code == 422


def test_blank_site_is_rejected(api):
    from datetime import date

    r = api.post("/api/reports", json={"text": "x y z", "site": "   ", "date": date.today().isoformat()})
    assert r.status_code == 422


def test_unknown_api_path_is_json_404_not_the_spa(api):
    r = api.get("/api/definitely-not-a-route")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")


def test_triage_filters_by_primary_life_saving_rule(api):
    from datetime import date

    text = (
        "The machine guard was missing from the pumping unit drive and the unit was not "
        "isolated at the panel. The belt started on auto. No injury to any personnel."
    )
    r = api.post("/api/reports", json={"text": text, "site": "Moran", "date": date.today().isoformat()})
    assert r.status_code == 201
    lsr = r.json()["verdict"]["primary_lsr"]
    assert lsr
    hit = api.get("/api/triage", params={"lsr": lsr}).json()
    assert hit["total"] == 1
    other = "driving" if lsr != "driving" else "hot_work"
    assert api.get("/api/triage", params={"lsr": other}).json()["total"] == 0
