"""A stub ONNX model, so the neural inference path is exercised in CI.

The real MuRIL adapters need a GPU to train and ~110MB to ship. Without a stand-in,
the only thing the test suite would ever prove is that the FALLBACK works — the
ONNX session, the tokenizer wiring, the recall-biased decoding and the span
resolver would all be untested until someone ran a Colab notebook.

So this builds a tiny graph with the real interface: same input names, same
`[batch, sequence, num_labels]` output. Its weights are not trained; it exists
to prove the plumbing carries a prediction from tokenizer to typed fact.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prahari.data.annotation import BIO_LABELS


def _build_tokenizer(path: Path, vocab_words: list[str]) -> None:
    from tokenizers import Tokenizer, models, pre_tokenizers

    vocab = {"[UNK]": 0, "[CLS]": 1, "[SEP]": 2}
    for word in vocab_words:
        vocab.setdefault(word, len(vocab))
    tok = Tokenizer(models.WordLevel(vocab=vocab, unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.save(str(path))


def _build_onnx(path: Path, vocab_size: int, num_labels: int, hot: dict[int, int]) -> None:
    """A lookup graph: token id -> logits. Deterministic and tiny.

    `hot` maps a token id to the label id that token should fire, which lets a
    test assert that a specific word produces a specific typed fact.
    """
    import numpy as np
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    table = np.full((vocab_size, num_labels), -6.0, dtype=np.float32)
    table[:, 0] = 4.0  # default: "O"
    for token_id, label_id in hot.items():
        table[token_id, 0] = -4.0
        table[token_id, label_id] = 8.0

    graph = helper.make_graph(
        nodes=[helper.make_node("Gather", ["table", "input_ids"], ["logits"], axis=0)],
        name="prahari_stub",
        inputs=[
            helper.make_tensor_value_info("input_ids", TensorProto.INT64, ["batch", "sequence"]),
            helper.make_tensor_value_info("attention_mask", TensorProto.INT64, ["batch", "sequence"]),
        ],
        outputs=[
            helper.make_tensor_value_info(
                "logits", TensorProto.FLOAT, ["batch", "sequence", num_labels]
            )
        ],
        initializer=[numpy_helper.from_array(table, name="table")],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 14)])
    model.ir_version = 9
    onnx.checker.check_model(model)
    onnx.save(model, str(path))


@pytest.fixture()
def stub_model(tmp_path, monkeypatch):
    """Install a working stub extractor and return its details."""
    pytest.importorskip("onnx")
    pytest.importorskip("tokenizers")
    from prahari.ml.neural_extractor import reset_runtime

    words = [
        "worker", "was", "not", "wearing", "safety", "belt", "at", "Naoholia",
        "monkey", "board", "8", "mtr", "height", "No", "injury", "occurred", ".",
    ]
    tok_path = tmp_path / "tokenizer.json"
    _build_tokenizer(tok_path, words)

    tokenizer_vocab = json.loads(tok_path.read_text(encoding="utf-8"))["model"]["vocab"]
    label_index = {tag: i for i, tag in enumerate(BIO_LABELS)}

    # "safety"/"belt" -> a control mention; "not" -> a control negation;
    # "Naoholia" -> a location. Enough to prove spans become typed facts.
    hot = {
        tokenizer_vocab["safety"]: label_index["B-CONTROL_MENTION"],
        tokenizer_vocab["belt"]: label_index["I-CONTROL_MENTION"],
        # A multi-token negation, as a trained model would produce it.
        tokenizer_vocab["was"]: label_index["B-CONTROL_NEGATION"],
        tokenizer_vocab["not"]: label_index["I-CONTROL_NEGATION"],
        tokenizer_vocab["wearing"]: label_index["I-CONTROL_NEGATION"],
        tokenizer_vocab["Naoholia"]: label_index["B-LOCATION"],
        tokenizer_vocab["monkey"]: label_index["B-ENERGY_SOURCE"],
        tokenizer_vocab["board"]: label_index["I-ENERGY_SOURCE"],
    }
    _build_onnx(tmp_path / "prahari.onnx", len(tokenizer_vocab), len(BIO_LABELS), hot)

    monkeypatch.setenv("PRAHARI_MODELS_DIR", str(tmp_path))
    reset_runtime()
    yield {"dir": tmp_path, "words": words}
    reset_runtime()
