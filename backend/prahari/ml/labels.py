"""Turn gold character spans into BIO token labels.

Pure data transformation: no model, no network, no verdicts. Kept out of the
training package so the inference path can decode BIO tags with the same code
that encoded them.
"""

from __future__ import annotations

from dataclasses import dataclass

from prahari.data.annotation import BIO_LABELS, ID_TO_LABEL, LABEL_TO_ID, EntityLabel

__all__ = [
    "BIO_LABELS", "LABEL_TO_ID", "ID_TO_LABEL", "EntityLabel",
    "CharSpan", "spans_to_bio", "bio_to_spans", "align_offsets",
]


@dataclass(frozen=True, slots=True)
class CharSpan:
    label: str
    start: int
    end: int
    score: float = 1.0


def spans_to_bio(spans: list[CharSpan], offsets: list[tuple[int, int]]) -> list[int]:
    """Label ids for each token, given its (start, end) character offsets.

    Special tokens must carry offset (0, 0); they get -100 so the loss ignores
    them, which is what HuggingFace's token-classification head expects.

    B- is assigned to the FIRST token that lands in each span instance, not to
    tokens whose offset happens to equal the span start. Those are different
    things: a wordpiece straddling the boundary between two adjacent spans
    would otherwise consume the B- of the second one and leave an orphan I-,
    producing a sequence no decoder can read back. That silently corrupts
    training, and it is invisible until you inspect the tensors.
    """
    labels: list[int] = []
    opened: set[int] = set()
    ordered = sorted(range(len(spans)), key=lambda i: (spans[i].start, spans[i].end))

    for start, end in offsets:
        if end <= start:
            labels.append(-100)
            continue
        chosen: int | None = None
        for index in ordered:
            span = spans[index]
            if start < span.end and span.start < end:
                chosen = index
                break
        if chosen is None:
            labels.append(0)
            continue
        prefix = "I" if chosen in opened else "B"
        opened.add(chosen)
        labels.append(LABEL_TO_ID.get(f"{prefix}-{spans[chosen].label}", 0))
    return labels


def bio_to_spans(
    tags: list[str], offsets: list[tuple[int, int]], scores: list[float] | None = None
) -> list[CharSpan]:
    """Decode BIO tags back to character spans.

    Tolerant of malformed sequences: an I- tag with no preceding B- opens a new
    span rather than being dropped. Under a recall-biased threshold that case is
    common, and discarding it would silently undo the threshold choice.
    """
    out: list[CharSpan] = []
    current: dict | None = None

    def close() -> None:
        nonlocal current
        if current is not None:
            out.append(
                CharSpan(
                    label=current["label"],
                    start=current["start"],
                    end=current["end"],
                    score=current["total"] / max(current["n"], 1),
                )
            )
            current = None

    for i, tag in enumerate(tags):
        start, end = offsets[i]
        if end <= start:
            continue
        score = scores[i] if scores else 1.0
        if tag == "O" or "-" not in tag:
            close()
            continue
        prefix, label = tag.split("-", 1)
        if current and current["label"] == label and prefix == "I":
            current["end"] = end
            current["total"] += score
            current["n"] += 1
        else:
            close()
            current = {"label": label, "start": start, "end": end, "total": score, "n": 1}
    close()
    return out


def align_offsets(text: str, offsets: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Clamp tokenizer offsets into the text, defending against off-by-ones."""
    n = len(text)
    return [(max(0, min(s, n)), max(0, min(e, n))) for s, e in offsets]
