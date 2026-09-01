"""The BIO dataset builder, exercised without downloading a checkpoint.

A whitespace tokenizer stands in for MuRIL. What is being tested is the
alignment between gold character spans and token labels — which is tokenizer
independent, and is the part that silently corrupts a training run when wrong.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from prahari.data.annotation import ID_TO_LABEL
from prahari.ml.training.prepare_data import build

CORPUS = Path(__file__).resolve().parents[3] / "data" / "synthetic_reports.jsonl"


class WhitespaceTokenizer:
    """Minimal stand-in exposing the two things `build` uses."""

    def __call__(self, text, return_offsets_mapping=False, truncation=False, max_length=None):  # noqa: ANN001, ARG002
        offsets = [(0, 0)]
        for match in re.finditer(r"\S+", text):
            offsets.append((match.start(), match.end()))
        offsets.append((0, 0))
        if max_length:
            offsets = offsets[:max_length]
        return {
            "input_ids": list(range(len(offsets))),
            "attention_mask": [1] * len(offsets),
            "offset_mapping": offsets,
        }


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    if not CORPUS.exists():
        pytest.skip("corpus not generated")
    out = tmp_path_factory.mktemp("dataset")
    stats = build(out, CORPUS, tokenizer=WhitespaceTokenizer())
    return out, stats


def test_splits_match_the_corpus_split(dataset) -> None:
    _, stats = dataset
    assert stats["train"] + stats["val"] + stats["test"] == 3000
    assert abs(stats["train"] / 3000 - 0.70) < 0.02
    assert abs(stats["val"] / 3000 - 0.15) < 0.02


def test_every_entity_type_appears_in_training(dataset) -> None:
    _, stats = dataset
    labels = {tag.split("-", 1)[1] for tag in stats["entity_tokens"] if "-" in tag}
    assert {
        "ENERGY_SOURCE", "MAGNITUDE_CUE", "CONTROL_MENTION",
        "CONTROL_NEGATION", "ACTIVITY", "LOCATION",
    } <= labels


def test_labels_line_up_with_tokens(dataset) -> None:
    out, _ = dataset
    rows = [json.loads(l) for l in (out / "train.jsonl").read_text(encoding="utf-8").splitlines()][:200]
    for row in rows:
        assert len(row["labels"]) == len(row["input_ids"]) == len(row["offsets"])


def test_special_tokens_are_ignored_by_the_loss(dataset) -> None:
    out, _ = dataset
    rows = [json.loads(l) for l in (out / "train.jsonl").read_text(encoding="utf-8").splitlines()][:200]
    for row in rows:
        for label, (start, end) in zip(row["labels"], row["offsets"]):
            if end <= start:
                assert label == -100


def test_labelled_tokens_actually_sit_inside_a_gold_span(dataset) -> None:
    """The check that catches an off-by-one before it wastes 2 GPU-hours."""
    out, _ = dataset
    rows = [json.loads(l) for l in (out / "train.jsonl").read_text(encoding="utf-8").splitlines()][:300]
    checked = 0
    for row in rows:
        gold = row["gold_spans"]
        for label_id, (start, end) in zip(row["labels"], row["offsets"]):
            if label_id is None or label_id <= 0:
                continue
            tag = ID_TO_LABEL[label_id]
            entity = tag.split("-", 1)[1]
            assert any(
                g["label"] == entity and start < g["end"] and g["start"] < end for g in gold
            ), f"{row['report_id']}: token [{start},{end}) tagged {tag} with no matching gold span"
            checked += 1
    assert checked > 500, "too few labelled tokens to be a meaningful check"


def test_b_tag_starts_a_span_and_i_tag_continues_it(dataset) -> None:
    out, _ = dataset
    rows = [json.loads(l) for l in (out / "train.jsonl").read_text(encoding="utf-8").splitlines()][:300]
    for row in rows:
        previous = "O"
        for label_id in row["labels"]:
            tag = "O" if label_id in (-100, 0) else ID_TO_LABEL[label_id]
            if tag.startswith("I-"):
                entity = tag.split("-", 1)[1]
                assert previous.endswith(entity), f"{row['report_id']}: I-{entity} after {previous}"
            if label_id != -100:
                previous = tag
