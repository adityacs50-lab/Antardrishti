"""Turn a predicted SPAN into a typed fact the rule engine can consume.

The token classifier answers "is there an entity here, and of what kind" — it
does not answer "which of the ten Energy Wheel categories" or "which of the
seven control states". Those are closed vocabularies with published
definitions, so resolving them is a lookup, not a prediction.

That division is deliberate. The model does the part it is good at and the
lexicon cannot do — finding the span at all, in transliterated code-mixed text
the phrase lists have never seen. The lexicon does the part it is good at and
the model would only make less reliable — naming which category a known phrase
belongs to. A span the resolver cannot type is still reported, as an untyped
fact, so it shows up in the UI and in evaluation rather than vanishing.
"""

from __future__ import annotations

import re

from prahari.domain.controls import ALL_CONTROLS, ControlStatus
from prahari.domain.energy import ENERGY_SOURCES, EnergySource
from prahari.ml.extractor import _STATUS_PATTERNS

#: phrase -> energy source, longest phrase first so "monkey board" beats "board"
_ENERGY_INDEX: list[tuple[str, EnergySource]] = sorted(
    ((phrase, source) for source, d in ENERGY_SOURCES.items() for phrase in d.trigger_phrases),
    key=lambda kv: -len(kv[0]),
)

_CONTROL_INDEX: list[tuple[str, str]] = sorted(
    ((phrase, c.key) for c in ALL_CONTROLS for phrase in c.phrases),
    key=lambda kv: -len(kv[0]),
)


def resolve_energy(span_text: str) -> EnergySource | None:
    """Which Energy Wheel category a predicted span names, if any."""
    lowered = span_text.lower()
    for phrase, source in _ENERGY_INDEX:
        if phrase in lowered:
            return source
    return None


def resolve_control(span_text: str) -> str | None:
    """Which named control a predicted span refers to, if any."""
    lowered = span_text.lower()
    for phrase, key in _CONTROL_INDEX:
        if phrase in lowered:
            return key
    return None


def resolve_control_status(span_text: str) -> ControlStatus | None:
    """Which control state a predicted negation span asserts.

    Ordered most-specific-first by `_STATUS_PATTERNS`, so a deliberate defeat
    ("had been removed") resolves to BYPASSED rather than plain ABSENT.
    """
    for status, patterns in _STATUS_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, span_text, flags=re.IGNORECASE):
                return status
    return None
