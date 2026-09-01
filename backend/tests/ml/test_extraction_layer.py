"""The ML layer's contract, its fallback, and the offline guarantee.

These run with or without a trained model present. The recall floor lives in
test_recall_floor.py and skips (loudly) when there is no model to score.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

import pytest

from prahari.data.annotation import BIO_LABELS, Annotated, EntityLabel, GoldSpan
from prahari.ml import active_extractor, extract_facts, keyword_extract
from prahari.ml.extractor import ExtractedFacts, FactType
from prahari.ml.labels import CharSpan, bio_to_spans, spans_to_bio
from prahari.ml.neural_extractor import extract as neural_extract
from prahari.ml.neural_extractor import model_status, predict_spans, reset_runtime
from prahari.ml.resolver import resolve_control, resolve_control_status, resolve_energy

SAMPLE = (
    "On 12.08.2026, Sri B. Gogoi was working at monkey board at 8 mtr height at "
    "Rig No. 12, Naoholia. He was not wearing safety belt. No injury occurred."
)


# -- fallback: the demo must never hard-fail --------------------------------


def test_missing_model_falls_back_to_keyword_extractor(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PRAHARI_MODELS_DIR", str(tmp_path))
    reset_runtime()
    facts = neural_extract(SAMPLE)
    assert isinstance(facts, ExtractedFacts)
    assert facts.facts, "fallback must still produce facts"
    assert facts.extractor_version == keyword_extract(SAMPLE).extractor_version
    reset_runtime()


def test_missing_model_logs_a_warning(monkeypatch, tmp_path, caplog) -> None:
    monkeypatch.setenv("PRAHARI_MODELS_DIR", str(tmp_path))
    reset_runtime()
    with caplog.at_level(logging.WARNING, logger="prahari.ml"):
        neural_extract(SAMPLE)
    assert any("falling back" in r.getMessage().lower() for r in caplog.records), caplog.text
    reset_runtime()


def test_corrupt_model_file_falls_back_rather_than_raising(monkeypatch, tmp_path) -> None:
    """A truncated or garbage ONNX file must degrade, not crash the demo."""
    (tmp_path / "prahari.onnx").write_bytes(b"this is not a valid onnx graph")
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("PRAHARI_MODELS_DIR", str(tmp_path))
    reset_runtime()
    facts = neural_extract(SAMPLE)
    assert facts.facts
    assert model_status().loaded is False
    reset_runtime()


def test_predict_spans_returns_none_without_a_model(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PRAHARI_MODELS_DIR", str(tmp_path))
    reset_runtime()
    assert predict_spans(SAMPLE) is None
    reset_runtime()


def test_registry_can_be_pinned_to_the_keyword_path(monkeypatch) -> None:
    monkeypatch.setenv("PRAHARI_EXTRACTOR", "keyword")
    assert active_extractor() == "keyword"
    assert extract_facts(SAMPLE).extractor_version == keyword_extract(SAMPLE).extractor_version


def test_engine_is_unchanged_by_which_extractor_ran() -> None:
    """The engine consumes facts; it cannot tell where they came from."""
    from prahari.rules.engine import evaluate

    verdict = evaluate(keyword_extract(SAMPLE))
    assert verdict.classification.value in {c for c in ("psif", "exposure", "hsif")}
    assert verdict.fired_rules


# -- the model must never emit a verdict ------------------------------------


def test_ml_layer_exposes_no_verdict_or_severity_concept() -> None:
    """CLAUDE.md: the model extracts facts. It never decides."""
    import prahari.ml as ml
    import prahari.ml.neural_extractor as ne

    banned = ("severity", "score", "classify", "verdict", "risk", "sif_class")
    for module in (ml, ne):
        exported = [n for n in dir(module) if not n.startswith("_")]
        offenders = [n for n in exported if any(b in n.lower() for b in banned)]
        assert not offenders, f"{module.__name__} must not expose {offenders}"


def test_fact_types_produced_are_only_those_the_engine_knows() -> None:
    facts = extract_facts(SAMPLE)
    assert all(isinstance(f.fact_type, FactType) for f in facts.facts)


# -- BIO round trip ---------------------------------------------------------


def test_bio_labels_are_stable_and_complete() -> None:
    assert BIO_LABELS[0] == "O"
    assert len(BIO_LABELS) == 1 + 2 * len(EntityLabel)
    assert len(set(BIO_LABELS)) == len(BIO_LABELS)


def test_spans_survive_a_bio_round_trip() -> None:
    from prahari.data.annotation import ID_TO_LABEL

    text = "worker was not wearing safety belt at Naoholia"
    offsets = [(0, 0), (0, 6), (7, 10), (11, 14), (15, 22), (23, 29), (30, 34), (35, 37), (38, 46), (0, 0)]
    spans = [
        CharSpan("CONTROL_NEGATION", 7, 22),
        CharSpan("CONTROL_MENTION", 23, 34),
        CharSpan("LOCATION", 38, 46),
    ]
    ids = spans_to_bio(spans, offsets)
    tags = [ID_TO_LABEL.get(i, "O") if i >= 0 else "O" for i in ids]
    decoded = {(s.label, text[s.start : s.end]) for s in bio_to_spans(tags, offsets)}
    assert ("CONTROL_MENTION", "safety belt") in decoded
    assert ("LOCATION", "Naoholia") in decoded


def test_special_tokens_are_masked_out_of_the_loss() -> None:
    assert spans_to_bio([], [(0, 0), (0, 4), (0, 0)]) == [-100, 0, -100]


# -- gold-span annotation ---------------------------------------------------


def test_splice_keeps_spans_pointing_at_the_same_text() -> None:
    ann = Annotated("worker was not wearing safety belt")
    ann.spans = [GoldSpan(EntityLabel.CONTROL_MENTION, 23, 34)]
    before = ann.text[23:34]
    ann.splice(0, 6, "workman")
    assert ann.text[ann.spans[0].start : ann.spans[0].end] == before


def test_resolve_overlaps_gives_each_character_one_label() -> None:
    ann = Annotated("working at monkey board at 8 mtr height")
    ann.add(EntityLabel.ACTIVITY, 0, 38)
    ann.add(EntityLabel.ENERGY_SOURCE, 11, 23)
    ann.resolve_overlaps()
    covered: list[int] = []
    for span in ann.spans:
        covered.extend(range(span.start, span.end))
    assert len(covered) == len(set(covered)), "a character may carry only one label"
    assert any(s.label is EntityLabel.ENERGY_SOURCE for s in ann.spans)


def test_generator_emits_aligned_gold_spans() -> None:
    from prahari.data.generator import build_spec, render_annotated
    from prahari.domain.classification import SifClassification

    rng = random.Random(7)
    for target in (SifClassification.PSIF, SifClassification.EXPOSURE, SifClassification.HSIF):
        for _ in range(15):
            ann = render_annotated(build_spec(target, rng), rng)
            for span in ann.spans:
                assert 0 <= span.start < span.end <= len(ann.text)


def test_corpus_gold_spans_are_aligned_and_present() -> None:
    corpus = Path(__file__).resolve().parents[3] / "data" / "synthetic_reports.jsonl"
    if not corpus.exists():
        pytest.skip("corpus not generated")
    rows = [json.loads(l) for l in corpus.read_text(encoding="utf-8").splitlines() if l.strip()][:400]
    assert all("gold_spans" in r for r in rows)
    for row in rows:
        for span in row["gold_spans"]:
            assert row["text"][span["start"] : span["end"]] == span["text"], row["report_id"]
    labels = {s["label"] for r in rows for s in r["gold_spans"]}
    assert {"ENERGY_SOURCE", "CONTROL_MENTION", "CONTROL_NEGATION", "LOCATION"} <= labels


# -- resolver ---------------------------------------------------------------


def test_resolver_types_spans_via_the_closed_vocabularies() -> None:
    assert resolve_energy("monkey board") is not None
    assert resolve_control("safety belt") is not None
    assert resolve_control_status("was not wearing") is not None


def test_resolver_returns_none_rather_than_guessing() -> None:
    assert resolve_energy("the quick brown fox") is None
    assert resolve_control("the quick brown fox") is None
    assert resolve_control_status("the quick brown fox") is None


def test_bypass_wording_resolves_to_bypassed_not_absent() -> None:
    from prahari.domain.controls import ControlStatus

    assert resolve_control_status("the guard had been removed") is ControlStatus.BYPASSED
