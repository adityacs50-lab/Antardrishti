"""Gold span annotation that survives the noise pipeline.

WHY THIS EXISTS
---------------
Training labels for the ML extractor must NOT be derived from the keyword
extractor's output. A model trained on `extractor.py`'s matches can only learn
to imitate `extractor.py`, inheriting exactly the blind spots that motivate
replacing it — it would never learn that "safety belt pindhi noasil" is a
control negation, because the phrase list is what taught it.

So the labels come from the generator, which KNOWS what it wrote. When it
renders a report it records, per character range, which clause role that range
plays. The lexicon is used only to locate the head phrase INSIDE a clause whose
role is already known — the role assignment itself is ground truth.

THE HONEST LIMITATION
---------------------
This is clause-scoped distant supervision, not human annotation. Where a head
phrase cannot be located inside its clause, the whole clause is labelled, which
is true but coarse. A model trained here learns real positional and
morphological structure it could not get from a phrase list, but its ceiling is
still the generator's own vocabulary. Real annotated OIL reports would beat it.

OFFSETS
-------
Style noise (typos, abbreviation substitution, article dropping) changes string
lengths, so every edit goes through `Annotated.splice`, which shifts recorded
spans. Spans an edit lands inside are clipped, and spans it destroys are
dropped rather than left pointing at the wrong characters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EntityLabel(str, Enum):
    """The six span types the token classifier learns."""

    ENERGY_SOURCE = "ENERGY_SOURCE"
    MAGNITUDE_CUE = "MAGNITUDE_CUE"
    CONTROL_MENTION = "CONTROL_MENTION"
    CONTROL_NEGATION = "CONTROL_NEGATION"
    ACTIVITY = "ACTIVITY"
    LOCATION = "LOCATION"


#: BIO tag vocabulary. Index 0 is O, then B-/I- per label, in a fixed order so
#: a saved model's label ids stay valid across runs.
BIO_LABELS: tuple[str, ...] = ("O",) + tuple(
    f"{prefix}-{label.value}" for label in EntityLabel for prefix in ("B", "I")
)
LABEL_TO_ID: dict[str, int] = {tag: i for i, tag in enumerate(BIO_LABELS)}
ID_TO_LABEL: dict[int, str] = {i: tag for tag, i in LABEL_TO_ID.items()}


@dataclass
class GoldSpan:
    label: EntityLabel
    start: int
    end: int
    #: How the span was located, so weak labels are auditable.
    provenance: str = "slot"

    @property
    def valid(self) -> bool:
        return self.end > self.start

    def as_dict(self, text: str) -> dict:
        return {
            "label": self.label.value,
            "start": self.start,
            "end": self.end,
            "text": text[self.start : self.end],
            "provenance": self.provenance,
        }


@dataclass
class Annotated:
    """Text plus spans, kept consistent through in-place edits."""

    text: str
    spans: list[GoldSpan] = field(default_factory=list)

    def add(self, label: EntityLabel, start: int, end: int, provenance: str = "slot") -> None:
        if end > start and 0 <= start < len(self.text):
            self.spans.append(GoldSpan(label, start, min(end, len(self.text)), provenance))

    def splice(self, start: int, end: int, replacement: str) -> None:
        """Replace text[start:end] and move every recorded span accordingly."""
        delta = len(replacement) - (end - start)
        self.text = self.text[:start] + replacement + self.text[end:]
        if delta == 0:
            return
        survivors: list[GoldSpan] = []
        for span in self.spans:
            if span.end <= start:
                survivors.append(span)
                continue
            if span.start >= end:
                span.start += delta
                span.end += delta
                survivors.append(span)
                continue
            # The edit lands inside the span: keep it, clipped, if anything is left.
            span.end = max(span.start, span.end + delta)
            if span.valid:
                survivors.append(span)
        self.spans = survivors

    def find(self, needle: str, within: tuple[int, int] | None = None) -> tuple[int, int] | None:
        """Case-insensitive search, optionally restricted to a clause."""
        lo, hi = within or (0, len(self.text))
        idx = self.text.lower().find(needle.lower(), lo, hi)
        return (idx, idx + len(needle)) if idx != -1 else None

    def normalise(self) -> None:
        """Drop empties and duplicates; sort by position then label."""
        seen: set[tuple[str, int, int]] = set()
        out: list[GoldSpan] = []
        for span in sorted(self.spans, key=lambda s: (s.start, s.end, s.label.value)):
            if not span.valid:
                continue
            key = (span.label.value, span.start, span.end)
            if key in seen:
                continue
            seen.add(key)
            out.append(span)
        self.spans = out

    def resolve_overlaps(self) -> None:
        """One label per character. Specific beats general on a clash.

        ACTIVITY is a clause-wide fallback, so anything more specific that lands
        inside it wins; MAGNITUDE_CUE and LOCATION are exact slot fills and win
        over everything.
        """
        priority = {
            EntityLabel.MAGNITUDE_CUE: 5,
            EntityLabel.LOCATION: 5,
            EntityLabel.CONTROL_NEGATION: 4,
            EntityLabel.CONTROL_MENTION: 4,
            EntityLabel.ENERGY_SOURCE: 3,
            EntityLabel.ACTIVITY: 1,
        }
        self.normalise()
        owner: list[GoldSpan | None] = [None] * len(self.text)
        for span in sorted(self.spans, key=lambda s: priority[s.label]):
            for i in range(span.start, min(span.end, len(self.text))):
                owner[i] = span

        merged: list[GoldSpan] = []
        i = 0
        while i < len(owner):
            current = owner[i]
            if current is None:
                i += 1
                continue
            j = i
            while j < len(owner) and owner[j] is current:
                j += 1
            merged.append(GoldSpan(current.label, i, j, current.provenance))
            i = j
        self.spans = merged
