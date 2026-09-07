"""Coverage on every endpoint, plus the invariants that matter."""

from __future__ import annotations

import io
import json
from datetime import date, timedelta

import pytest

from tests.conftest import (
    HIGH_ENERGY_CONTROLLED,
    HIGH_ENERGY_UNCONTROLLED,
    LOW_ENERGY_INJURY,
    VAGUE,
    post_report,
    seed_repeats,
)

# -- health & ingest --------------------------------------------------------


def test_health_reports_offline_and_versions(api) -> None:
    body = api.get("/health").json()
    assert body["status"] == "ok"
    assert body["offline"] == "true"
    assert body["engine_version"] and body["extractor_version"]


def test_post_report_returns_a_traceable_verdict(api) -> None:
    r = post_report(api, HIGH_ENERGY_UNCONTROLLED)
    assert r.status_code == 201
    v = r.json()["verdict"]
    assert v["classification"] == "psif"
    assert v["high_energy"] is True
    assert v["direct_control_effective"] is False
    assert v["fired_rules"], "a verdict with no rule firings is not defensible"
    assert all(f["rule_id"] and f["description"] and f["citation_key"] for f in v["fired_rules"])


def test_every_verdict_cites_a_named_rule_and_spans(api) -> None:
    """The core architectural promise, checked end to end."""
    rid = post_report(api, HIGH_ENERGY_UNCONTROLLED).json()["id"]
    detail = api.get(f"/api/reports/{rid}").json()
    assert detail["verdict"]["fired_rules"]
    spans = detail["evidence_spans"]
    assert spans, "no evidence spans to highlight"
    text = detail["text"]
    for span in spans:
        assert 0 <= span["start"] < span["end"] <= len(text)
        assert text[span["start"] : span["end"]] == span["quoted_text"]


def test_controlled_high_energy_is_not_a_precursor(api) -> None:
    v = post_report(api, HIGH_ENERGY_CONTROLLED).json()["verdict"]
    assert v["classification"] in ("success", "capacity")
    assert v["direct_control_effective"] is True


def test_visible_injury_low_energy_is_not_a_sif(api) -> None:
    """The trap a severity model gets wrong."""
    v = post_report(api, LOW_ENERGY_INJURY).json()["verdict"]
    assert v["classification"] == "low_severity"
    assert v["high_energy"] is False
    assert v["injury_outcome"] in ("first_aid", "minor_injury")


def test_vague_report_returns_insufficient_information(api) -> None:
    v = post_report(api, VAGUE).json()["verdict"]
    assert v["classification"] == "insufficient_information"
    assert v["primary_lsr"] is None


def test_blank_text_is_rejected(api) -> None:
    assert post_report(api, "   ").status_code == 422


def test_duplicate_report_uid_conflicts(api) -> None:
    assert post_report(api, HIGH_ENERGY_UNCONTROLLED, report_uid="X-1").status_code == 201
    assert post_report(api, HIGH_ENERGY_UNCONTROLLED, report_uid="X-1").status_code == 409


# -- bulk -------------------------------------------------------------------


def test_bulk_jsonl_upload(api) -> None:
    lines = [
        json.dumps({"text": HIGH_ENERGY_UNCONTROLLED, "site": "Moran", "date": "2026-05-01"}),
        json.dumps({"text": LOW_ENERGY_INJURY, "site": "Moran", "date": "2026-05-02"}),
        json.dumps({"text": "", "site": "Moran", "date": "2026-05-03"}),
    ]
    payload = "\n".join(lines).encode()
    r = api.post(
        "/api/reports/bulk",
        files={"file": ("corpus.jsonl", io.BytesIO(payload), "application/x-ndjson")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["received"] == 3
    assert body["ingested"] == 2
    assert body["skipped"] == 1
    assert sum(body["classification_counts"].values()) == 2


def test_bulk_csv_upload(api) -> None:
    csv_text = (
        "text,site,date,reporter_role\n"
        f'"{HIGH_ENERGY_UNCONTROLLED}",Dikom,2026-06-01,Safety Officer\n'
        f'"{LOW_ENERGY_INJURY}",Dikom,2026-06-02,Tool Pusher\n'
    )
    r = api.post(
        "/api/reports/bulk",
        files={"file": ("corpus.csv", io.BytesIO(csv_text.encode()), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["ingested"] == 2


def test_bulk_maps_real_world_column_names_and_dates(api) -> None:
    """A real export never names its narrative column `text`.

    This is the OSHA severe-injury file's own header shape (Final Narrative /
    City / EventDate / ID, US-style m/d/Y dates). Before column aliasing every
    row of a 90,000-row public corpus was skipped as "missing text" and the
    import reported nothing ingested for a perfectly good file.
    """
    csv_text = (
        '"ID","EventDate","City","Final Narrative"\n'
        f'"2015010015",3/14/2015,"SANDUSKY","{HIGH_ENERGY_UNCONTROLLED}"\n'
        f'"2015010016",1/1/2015,"OTISVILLE","{LOW_ENERGY_INJURY}"\n'
    )
    r = api.post(
        "/api/reports/bulk",
        files={"file": ("osha.csv", io.BytesIO(csv_text.encode()), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["ingested"] == 2

    listed = api.get("/api/reports?limit=10").json()["items"]
    assert {row["site"] for row in listed} == {"SANDUSKY", "OTISVILLE"}
    # m/d/Y read as month-first, not silently dropped or defaulted to today.
    assert "2015-03-14" in {row["date"] for row in listed}


def test_bulk_keeps_good_rows_when_a_later_row_fails(api) -> None:
    """One bad row must not discard the rows already ingested before it.

    The failure path used to call `db.rollback()`, which throws away the whole
    uncommitted transaction — every earlier row went with it while still being
    counted as ingested. The import then claimed success over an empty queue.
    """
    over_limit = "x " * 20_000  # past ReportIn/column bounds — fails on flush
    lines = [
        json.dumps({"text": HIGH_ENERGY_UNCONTROLLED, "site": "Moran", "date": "2026-05-01"}),
        json.dumps({"text": over_limit, "site": "Moran", "date": "2026-05-02"}),
        json.dumps({"text": LOW_ENERGY_INJURY, "site": "Moran", "date": "2026-05-03"}),
    ]
    r = api.post(
        "/api/reports/bulk",
        files={"file": ("corpus.jsonl", io.BytesIO("\n".join(lines).encode()), "application/x-ndjson")},
    )
    assert r.status_code == 200
    body = r.json()
    # Whatever the middle row does, the count reported must match what is
    # actually stored — that equality is the property the savepoint restores.
    assert api.get("/api/reports?limit=100").json()["total"] == body["ingested"]
    assert body["ingested"] >= 2


def test_bulk_says_which_columns_it_found_when_nothing_matched(api) -> None:
    csv_text = 'alpha,beta\n"some value","another"\n'
    r = api.post(
        "/api/reports/bulk",
        files={"file": ("mystery.csv", io.BytesIO(csv_text.encode()), "text/csv")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ingested"] == 0
    assert "alpha" in body["errors"][0] and "beta" in body["errors"][0]


def test_bulk_rejects_unparseable_upload(api) -> None:
    r = api.post(
        "/api/reports/bulk",
        files={"file": ("bad.jsonl", io.BytesIO(b"{not json at all"), "application/x-ndjson")},
    )
    assert r.status_code == 400


# -- list / filter / paginate ----------------------------------------------


def test_list_is_paginated(api) -> None:
    seed_repeats(api, n=6)
    page = api.get("/api/reports?limit=2&offset=0").json()
    assert page["total"] == 6
    assert len(page["items"]) == 2
    page2 = api.get("/api/reports?limit=2&offset=2").json()
    assert {i["id"] for i in page["items"]}.isdisjoint({i["id"] for i in page2["items"]})


@pytest.mark.parametrize(
    "query,expected",
    [
        ("classification=psif", "psif"),
        ("classification=low_severity", "low_severity"),
        ("classification=insufficient_information", "insufficient_information"),
    ],
)
def test_filter_by_classification(api, query, expected) -> None:
    post_report(api, HIGH_ENERGY_UNCONTROLLED)
    post_report(api, LOW_ENERGY_INJURY)
    post_report(api, VAGUE)
    items = api.get(f"/api/reports?{query}").json()["items"]
    assert items
    assert all(i["classification"] == expected for i in items)


def test_filter_by_site_lsr_energy_and_dates(api) -> None:
    post_report(api, HIGH_ENERGY_UNCONTROLLED, site="Naoholia", day=date(2026, 3, 1))
    post_report(api, HIGH_ENERGY_UNCONTROLLED, site="Moran", day=date(2026, 8, 1))

    assert api.get("/api/reports?site=Moran").json()["total"] == 1
    assert api.get("/api/reports?energy_source=gravity").json()["total"] == 2
    assert api.get("/api/reports?lsr=working_at_height").json()["total"] == 2
    assert api.get("/api/reports?date_from=2026-07-01").json()["total"] == 1
    assert api.get("/api/reports?date_to=2026-04-01").json()["total"] == 1


def test_filter_by_min_confidence(api) -> None:
    """min_confidence filters evidence_completeness, not a model probability."""
    post_report(api, HIGH_ENERGY_UNCONTROLLED)
    post_report(api, VAGUE)
    strict = api.get("/api/reports?min_confidence=1.0").json()
    assert strict["total"] >= 1
    assert all(i["evidence_completeness"] >= 1.0 for i in strict["items"])
    assert api.get("/api/reports?min_confidence=0.0").json()["total"] == 2


def test_filter_by_reviewed_flag(api) -> None:
    rid = post_report(api, HIGH_ENERGY_UNCONTROLLED).json()["id"]
    post_report(api, LOW_ENERGY_INJURY)
    assert api.get("/api/reports?reviewed=true").json()["total"] == 0
    api.patch(
        f"/api/reports/{rid}/review",
        json={"reviewer_role": "HSE Officer", "decision": "confirm", "reason": "Agreed."},
    )
    assert api.get("/api/reports?reviewed=true").json()["total"] == 1
    assert api.get("/api/reports?reviewed=false").json()["total"] == 1


# -- detail -----------------------------------------------------------------


def test_detail_404_for_missing_report(api) -> None:
    assert api.get("/api/reports/9999").status_code == 404


def test_detail_includes_rule_firings_with_spans(api) -> None:
    rid = post_report(api, HIGH_ENERGY_UNCONTROLLED).json()["id"]
    detail = api.get(f"/api/reports/{rid}").json()
    by_id = {f["rule_id"]: f for f in detail["verdict"]["fired_rules"]}
    assert "R-CLASS-01" in by_id, "the classification rule must always be recorded"
    assert any(f["spans"] for f in detail["verdict"]["fired_rules"])


# -- triage -----------------------------------------------------------------


def test_triage_returns_only_sif_potential_ranked(api) -> None:
    post_report(api, HIGH_ENERGY_UNCONTROLLED)
    post_report(api, LOW_ENERGY_INJURY)
    post_report(api, HIGH_ENERGY_CONTROLLED)
    post_report(api, VAGUE)

    items = api.get("/api/triage").json()["items"]
    assert items
    assert all(i["classification"] in ("psif", "exposure") for i in items)
    ranks = [i["triage_rank"] for i in items]
    assert ranks == sorted(ranks, reverse=True), "triage must be ranked, highest first"


def test_triage_can_include_actual_events(api) -> None:
    post_report(api, HIGH_ENERGY_UNCONTROLLED)
    base = api.get("/api/triage").json()["total"]
    withev = api.get("/api/triage?include_actual_events=true").json()["total"]
    assert withev >= base


def test_triage_ties_break_by_recency(api) -> None:
    old = post_report(api, HIGH_ENERGY_UNCONTROLLED, day=date.today() - timedelta(days=90))
    new = post_report(api, HIGH_ENERGY_UNCONTROLLED, day=date.today())
    items = api.get("/api/triage").json()["items"]
    order = [i["id"] for i in items]
    assert order.index(new.json()["id"]) < order.index(old.json()["id"])


# -- review: the human-in-the-loop invariant -------------------------------


def test_override_stores_a_correction_without_touching_the_verdict(api) -> None:
    """The audit promise: the engine's output is never overwritten."""
    rid = post_report(api, HIGH_ENERGY_UNCONTROLLED).json()["id"]
    original = api.get(f"/api/reports/{rid}").json()["verdict"]["classification"]

    r = api.patch(
        f"/api/reports/{rid}/review",
        json={
            "reviewer_role": "HSE Officer",
            "decision": "override",
            "reason": "Harness was in fact worn; the reporter omitted it.",
            "corrected_classification": "capacity",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["classification"] == original, "verdict must be immutable"
    assert body["effective_classification"] == "capacity"
    assert body["reviews"][-1]["decision"] == "override"
    assert body["reviews"][-1]["corrected_classification"] == "capacity"


def test_confirm_keeps_the_engine_classification(api) -> None:
    rid = post_report(api, HIGH_ENERGY_UNCONTROLLED).json()["id"]
    body = api.patch(
        f"/api/reports/{rid}/review",
        json={"reviewer_role": "HSE Officer", "decision": "confirm", "reason": "Correct."},
    ).json()
    assert body["effective_classification"] == body["verdict"]["classification"]


def test_override_without_a_correction_is_rejected(api) -> None:
    rid = post_report(api, HIGH_ENERGY_UNCONTROLLED).json()["id"]
    r = api.patch(
        f"/api/reports/{rid}/review",
        json={"reviewer_role": "HSE", "decision": "override", "reason": "Wrong."},
    )
    assert r.status_code == 422


def test_reviews_accumulate_and_latest_wins(api) -> None:
    rid = post_report(api, HIGH_ENERGY_UNCONTROLLED).json()["id"]
    for cls in ("capacity", "exposure"):
        api.patch(
            f"/api/reports/{rid}/review",
            json={
                "reviewer_role": "HSE Officer",
                "decision": "override",
                "reason": f"Reclassified to {cls}.",
                "corrected_classification": cls,
            },
        )
    body = api.get(f"/api/reports/{rid}").json()
    assert len(body["reviews"]) == 2
    assert body["effective_classification"] == "exposure"


def test_review_404_for_missing_report(api) -> None:
    r = api.patch(
        "/api/reports/4242/review",
        json={"reviewer_role": "HSE", "decision": "confirm", "reason": "n/a"},
    )
    assert r.status_code == 404


# -- analytics --------------------------------------------------------------


def test_density_returns_counts_and_rates(api) -> None:
    post_report(api, HIGH_ENERGY_UNCONTROLLED, site="Moran", activity="working at height")
    post_report(api, LOW_ENERGY_INJURY, site="Moran", activity="workshop")
    body = api.get("/api/analytics/density").json()
    cells = {(c["site"], c["activity"]): c for c in body["cells"]}
    wah = cells[("Moran", "working at height")]
    assert wah["total_reports"] == 1
    assert wah["precursor_count"] == 1
    assert wah["precursor_rate"] == 1.0
    assert cells[("Moran", "workshop")]["precursor_rate"] == 0.0


def test_lsr_returns_all_nine_rules(api) -> None:
    post_report(api, HIGH_ENERGY_UNCONTROLLED)
    body = api.get("/api/analytics/lsr").json()
    assert len(body["buckets"]) == 9, "all nine rules must be returned, including zeros"
    assert sum(b["count"] for b in body["buckets"]) + body["unassigned"] == body["total"]


def test_lsr_counts_unassigned_separately(api) -> None:
    post_report(api, VAGUE)
    body = api.get("/api/analytics/lsr").json()
    assert body["unassigned"] == 1
    assert sum(b["count"] for b in body["buckets"]) == 0


def test_barriers_identifies_the_repeating_control(api) -> None:
    seed_repeats(api, site="Jorajan", n=4)
    body = api.get("/api/analytics/barriers?window_days=365").json()
    assert body["patterns"]
    top = body["patterns"][0]
    assert top["site"] == "Jorajan"
    assert top["failure_count"] == 4
    assert top["trend"] in ("rising", "falling", "flat", "insufficient_history")
    assert sum(top["statuses"].values()) == 4


def test_barriers_excludes_verified_controls(api) -> None:
    post_report(api, HIGH_ENERGY_CONTROLLED, site="Dikom")
    body = api.get("/api/analytics/barriers?window_days=365").json()
    assert all(p["site"] != "Dikom" for p in body["patterns"])


# -- the accumulation index ------------------------------------------------


def test_accumulation_rises_with_repeats_of_the_same_barrier(api) -> None:
    seed_repeats(api, site="Baghjan", n=2, days_apart=5)
    low = api.get("/api/analytics/accumulation?window_days=365").json()["cells"][0]["index"]
    seed_repeats(api, site="Baghjan", n=4, days_apart=3)
    high = api.get("/api/analytics/accumulation?window_days=365").json()["cells"][0]["index"]
    assert high > low, "repetition of the same barrier failure must escalate the index"


def test_repetition_outscores_variety(api) -> None:
    """The distinctive claim, stated as a test.

    Four failures of ONE barrier at one place must score higher than four
    failures of DIFFERENT barriers at another. Linear counting would tie them.
    """
    seed_repeats(api, site="Baghjan", n=4, days_apart=3)
    varied = [
        HIGH_ENERGY_UNCONTROLLED,
        "Hot work was taken up on the flowline at GGS. Gas test was not done and no fire "
        "watch was provided. There was a flash fire when sparks reached the vapour. No injury occurred.",
        "MCC panel was opened for attending the starter at 415 volt. No electrical isolation "
        "was carried out before opening the panel. An arc occurred when the spanner bridged "
        "the busbar. No injury occurred.",
        "Bell hole of 3 mtr depth was excavated at ROW. The trench was vertical without any "
        "shoring, benching or sloping. One side of the trench collapsed. No injury occurred.",
    ]
    for i, text in enumerate(varied):
        post_report(api, text, site="Moran", day=date.today() - timedelta(days=i * 3))

    cells = {(c["site"], c["energy_source"]): c for c in api.get(
        "/api/analytics/accumulation?window_days=365"
    ).json()["cells"]}
    repeated = cells[("Baghjan", "gravity")]
    assert repeated["max_repeat"] >= 4
    others = [c for k, c in cells.items() if k[0] == "Moran"]
    assert repeated["index"] > max(c["index"] for c in others)


def test_accumulation_is_reproducible_by_hand(api) -> None:
    """Every score must return the report ids and weights that produced it."""
    seed_repeats(api, site="Baghjan", n=3, days_apart=7)
    cell = api.get("/api/analytics/accumulation?window_days=365").json()["cells"][0]
    sig = cell["signatures"][0]
    assert sig["occurrences"] == len(sig["contributors"])
    for c in sig["contributors"]:
        assert c["report_uid"] and c["decayed_weight"] > 0
        assert api.get(f"/api/reports/{c['report_id']}").status_code == 200


def test_accumulation_decays_with_age(api) -> None:
    today = date.today()
    for i in range(4):
        post_report(api, HIGH_ENERGY_UNCONTROLLED, site="Old", day=today - timedelta(days=300 + i))
        post_report(api, HIGH_ENERGY_UNCONTROLLED, site="New", day=today - timedelta(days=i))
    cells = {c["site"]: c for c in api.get(
        "/api/analytics/accumulation?window_days=730"
    ).json()["cells"]}
    assert cells["New"]["index"] > cells["Old"]["index"]


def test_accumulation_ignores_controlled_and_low_energy_work(api) -> None:
    for i in range(4):
        post_report(api, HIGH_ENERGY_CONTROLLED, site="Kusijan", day=date.today() - timedelta(days=i))
        post_report(api, LOW_ENERGY_INJURY, site="Kusijan", day=date.today() - timedelta(days=i))
    cells = api.get("/api/analytics/accumulation?window_days=365").json()["cells"]
    assert all(c["site"] != "Kusijan" for c in cells)


def test_accumulation_bands_and_explanation(api) -> None:
    seed_repeats(api, site="Baghjan", n=6, days_apart=4)
    body = api.get("/api/analytics/accumulation?window_days=365").json()
    cell = body["cells"][0]
    assert cell["band"] in ("watch", "elevated", "high", "critical")
    assert body["repeat_exponent"] > 1.0
    assert 0 < body["diversity_discount"] < 1.0
    assert "Repetition" in cell["explanation"]


def test_accumulation_min_index_filter(api) -> None:
    seed_repeats(api, site="Baghjan", n=3)
    assert api.get("/api/analytics/accumulation?min_index=99999").json()["cells"] == []


def test_empty_database_returns_empty_analytics(api) -> None:
    for path in (
        "/api/analytics/density",
        "/api/analytics/barriers",
        "/api/analytics/accumulation",
    ):
        assert api.get(path).status_code == 200
    assert api.get("/api/analytics/lsr").json()["total"] == 0
    assert api.get("/api/reports").json()["total"] == 0
    assert api.get("/api/triage").json()["total"] == 0


# -- analyze (Live Analysis panel) & meta ----------------------------------


def test_analyze_returns_a_verdict_without_persisting(api) -> None:
    """The UI must never need its own copy of the rule engine."""
    before = api.get("/api/reports").json()["total"]
    r = api.post("/api/analyze", json={"text": HIGH_ENERGY_UNCONTROLLED})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"]["classification"] == "psif"
    assert body["verdict"]["fired_rules"]
    assert body["evidence_spans"]
    assert body["reason"]
    assert api.get("/api/reports").json()["total"] == before, "analyze must not persist"


def test_analyze_spans_index_the_submitted_text(api) -> None:
    body = api.post("/api/analyze", json={"text": HIGH_ENERGY_UNCONTROLLED}).json()
    text = body["text"]
    assert text == HIGH_ENERGY_UNCONTROLLED
    for span in body["evidence_spans"]:
        assert text[span["start"] : span["end"]] == span["quoted_text"]
        assert span["rule_id"]


def test_analyze_agrees_with_ingest(api) -> None:
    """One engine. The preview and the stored verdict must never disagree."""
    preview = api.post("/api/analyze", json={"text": HIGH_ENERGY_UNCONTROLLED}).json()
    stored = post_report(api, HIGH_ENERGY_UNCONTROLLED).json()["verdict"]
    for field in (
        "classification",
        "energy_source",
        "high_energy",
        "control_status",
        "direct_control_effective",
        "injury_outcome",
        "primary_lsr",
        "triage_rank",
    ):
        assert preview["verdict"][field] == stored[field], field


def test_analyze_rejects_blank_text(api) -> None:
    assert api.post("/api/analyze", json={"text": "   "}).status_code == 422


def test_analyze_handles_code_mixed_text(api) -> None:
    text = (
        "Rig no 33 Duliajan me casing lowering chal raha tha, load abt 2500 kg. "
        "Sling ka condition kharab tha aur koi secondary retention nahi tha. "
        "Sling parted and load dropped from 4 mtr. Koi chot nahi lagi."
    )
    body = api.post("/api/analyze", json={"text": text}).json()
    assert body["verdict"]["classification"] in ("psif", "exposure", "hsif")
    assert body["evidence_spans"]


def test_summary_rows_carry_a_reason(api) -> None:
    post_report(api, HIGH_ENERGY_UNCONTROLLED)
    item = api.get("/api/reports").json()["items"][0]
    assert item["reason"]
    assert len(item["reason"]) > 20


def test_meta_lists_vocabulary_and_present_sites(api) -> None:
    post_report(api, HIGH_ENERGY_UNCONTROLLED, site="Moran", activity="working at height")
    body = api.get("/api/meta").json()
    assert body["sites"] == ["Moran"]
    assert body["activities"] == ["working at height"]
    assert len(body["life_saving_rules"]) == 9
    assert len(body["classifications"]) == 8
    assert len(body["energy_sources"]) == 10
    assert body["report_count"] == 1
    assert body["engine_version"] and body["extractor_version"]
