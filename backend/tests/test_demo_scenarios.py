"""The four Live Sandbox quick-select scenarios, as a contract.

The scenario texts live in ONE file, `web/src/data/demo-scenarios.json`, which
the browser imports directly. This test reads the same file, so the text a
presenter clicks on stage is byte-for-byte the text verified here. Each
scenario declares the verdict it exists to demonstrate; a lexicon change that
moves one fails the build instead of surprising someone in front of judges.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prahari.rules.engine import analyse

SCENARIOS = json.loads(
    (Path(__file__).resolve().parents[2] / "web" / "src" / "data" / "demo-scenarios.json").read_text(
        encoding="utf-8"
    )
)


def _val(x):
    return None if x is None else x.value


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_scenario_produces_its_declared_verdict(scenario: dict) -> None:
    _, v = analyse(scenario["text"])
    got = {
        "classification": _val(v.classification),
        "energy_source": _val(v.energy_source),
        "control_status": _val(v.control_status),
        "primary_lsr": _val(v.primary_lsr),
    }
    assert got == scenario["expect"]


def test_multi_rule_scenario_engages_several_life_saving_rules() -> None:
    s = next(s for s in SCENARIOS if s["id"] == "scn-multirule")
    _, v = analyse(s["text"])
    assert len(v.secondary_lsr) >= 2
