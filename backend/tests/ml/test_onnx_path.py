"""The neural inference path, exercised against a stub ONNX graph."""

from __future__ import annotations

import time

import pytest

from prahari.domain.controls import ControlStatus
from prahari.ml.extractor import FactType
from prahari.ml.neural_extractor import extract as neural_extract
from prahari.ml.neural_extractor import model_status, predict_spans

TEXT = "worker was not wearing safety belt at Naoholia"
HAZARD = "worker at monkey board 8 mtr height . No injury occurred ."


def test_stub_model_loads(stub_model) -> None:
    status = model_status()
    assert status.loaded, status.reason


def test_predicted_spans_index_the_original_text(stub_model) -> None:
    spans = predict_spans(TEXT)
    assert spans, "the stub should fire on at least one token"
    for span in spans:
        assert 0 <= span.start < span.end <= len(TEXT)
        assert TEXT[span.start : span.end].strip()


def test_spans_become_typed_facts_through_the_resolver(stub_model) -> None:
    facts = neural_extract(TEXT, mode="replace")
    assert "muril-lora-onnx" in facts.extractor_version

    controls = [f for f in facts.of_type(FactType.CONTROL_MENTION) if "belt" in f.matched_text.lower()]
    assert controls, "a CONTROL_MENTION span should resolve to a named control"
    assert controls[0].value == "fall_arrest_system"

    statuses = facts.of_type(FactType.CONTROL_STATUS)
    assert any(f.value == ControlStatus.ABSENT.value for f in statuses)


def test_energy_span_resolves_to_the_right_wheel_category(stub_model) -> None:
    facts = neural_extract(HAZARD, mode="replace")
    energies = facts.of_type(FactType.ENERGY_PHRASE)
    assert any(f.value == "gravity" for f in energies), [f.value for f in energies]


def test_union_mode_never_loses_a_keyword_fact(stub_model) -> None:
    """Union is the default because recall is the objective."""
    from prahari.ml.extractor import extract as keyword_extract

    baseline = keyword_extract(TEXT)
    union = neural_extract(TEXT, mode="union")
    baseline_keys = {(f.fact_type, f.value, f.span.start, f.span.end) for f in baseline.facts}
    union_keys = {(f.fact_type, f.value, f.span.start, f.span.end) for f in union.facts}
    assert baseline_keys <= union_keys
    assert len(union.facts) >= len(baseline.facts)


def test_lower_threshold_never_reduces_recall(stub_model) -> None:
    """The threshold must actually control the precision/recall trade."""
    permissive = predict_spans(TEXT, threshold=0.05) or []
    strict = predict_spans(TEXT, threshold=0.99) or []
    assert len(permissive) >= len(strict)


def test_the_engine_accepts_neural_facts_unchanged(stub_model) -> None:
    """The whole point: swapping the extractor changes no rule."""
    from prahari.rules.engine import evaluate

    verdict = evaluate(neural_extract(HAZARD, mode="union"))
    assert verdict.fired_rules
    assert any(f.rule_id == "R-CLASS-01" for f in verdict.fired_rules)
    assert verdict.classification is not None


def test_cpu_inference_is_well_inside_the_budget(stub_model) -> None:
    for _ in range(3):
        predict_spans(TEXT)
    timings = []
    for _ in range(30):
        started = time.perf_counter()
        predict_spans(TEXT)
        timings.append((time.perf_counter() - started) * 1000)
    timings.sort()
    assert timings[len(timings) // 2] < 200.0


def test_inference_opens_no_socket(stub_model, monkeypatch) -> None:
    import socket

    def _blocked(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("the extractor attempted a network connection")

    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    assert predict_spans(TEXT) is not None


def test_a_too_tight_negation_span_still_resolves(stub_model) -> None:
    """A span the model got right must not be discarded for being terse.

    The resolver retries against the enclosing sentence, because dropping a
    correct detection is exactly the failure this system is tuned against.
    """
    from prahari.ml.resolver import resolve_control_status

    assert resolve_control_status("not") is None          # unnameable alone
    facts = neural_extract(TEXT, mode="replace")
    statuses = facts.of_type(FactType.CONTROL_STATUS)
    assert statuses, "the negation should survive via sentence context"
    assert any(f.value == ControlStatus.ABSENT.value for f in statuses)
