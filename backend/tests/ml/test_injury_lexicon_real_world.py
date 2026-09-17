"""Real-world injury wording (OSHA Severe Injury Reports benchmark).

The benchmark in claude/prahari-osha-accuracy-benchmark.md found the serious-
injury lexicon missed plain-English outcomes: "was hospitalized",
"fracturing", "broken leg", "second-degree burns", "surgery", "laceration",
"crushed his hand". These sentences are written for this test in that style;
they are not OSHA records. The negative cases pin the guards that stop the
wider vocabulary from over-reading OIL field reports.
"""

from __future__ import annotations

import pytest

from prahari.rules.engine import analyse

SERIOUS = [
    "An employee was hospitalized after falling from a ladder.",
    "The worker fell 12 feet, fracturing his left wrist.",
    "Employee suffered a broken left leg when the pipe rolled onto him.",
    "He sustained second-degree burns to his arms from the steam release.",
    "The press crushed his hand and he required surgery.",
    "Worker suffered a laceration to the head and was taken to hospital.",
]

NOT_SERIOUS = [
    ("The worker was not hospitalized and returned to duty.", "minor_injury"),
    ("No fracture was found. First aid was given.", "first_aid"),
    # OIL corpus convention: an unqualified burn from a steam leak is minor.
    ("He received burn on the forearm from the steam leak. First aid given.", "first_aid"),
    ("The load could have crushed him. No injury to any personnel.", "none"),
    ("He did not require surgery; dressing done at the dispensary.", "minor_injury"),
]


@pytest.mark.parametrize("text", SERIOUS)
def test_plain_english_serious_outcomes_are_read(text: str) -> None:
    _, verdict = analyse(text)
    assert verdict.injury_outcome.value == "serious_injury"


@pytest.mark.parametrize(("text", "expected"), NOT_SERIOUS)
def test_negated_or_unqualified_cues_are_not_serious(text: str, expected: str) -> None:
    _, verdict = analyse(text)
    assert verdict.injury_outcome.value == expected
