"""ONNX token-classification extractor.

WHAT THIS LAYER MAY AND MAY NOT DO — unchanged from extractor.py
----------------------------------------------------------------
It emits STRUCTURED FACTS with exact character offsets. It never emits a
classification, a severity or a score for the report. The rule engine is
untouched by this file existing: it consumes `ExtractedFacts` and cannot tell
whether a keyword matcher or a fine-tuned transformer produced them. That is
the entire point of the neuro-symbolic split, and it is why swapping in a model
cannot change how any verdict is justified.

FAILING CLOSED
--------------
If the ONNX file or the tokenizer is missing, unreadable, or throws at any
point, this module logs a warning once and returns the keyword extractor's
output instead. The demo degrades to the deterministic path rather than
crashing. That behaviour is tested.

NETWORK
-------
Nothing here touches the network. The tokenizer is loaded from a local
`tokenizer.json` via the `tokenizers` library, not from the HuggingFace hub,
and there is no `transformers` or `huggingface_hub` import in this file.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from prahari.ml import config
from prahari.ml.extractor import ExtractedFacts, Fact, FactType, Span, extract as keyword_extract
from prahari.ml.extractor import segment_sentences
from prahari.ml.labels import CharSpan, ID_TO_LABEL, align_offsets, bio_to_spans
from prahari.ml.resolver import resolve_control, resolve_control_status, resolve_energy

log = logging.getLogger("prahari.ml")

NEURAL_VERSION = "muril-lora-onnx-v1"


@dataclass(frozen=True, slots=True)
class ModelStatus:
    loaded: bool
    reason: str
    onnx_path: str
    tokenizer_path: str


class _Runtime:
    """Lazily loaded ONNX session + tokenizer. Thread-safe, loads once."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tried = False
        self._session = None
        self._tokenizer = None
        self._reason = "not loaded yet"

    @property
    def status(self) -> ModelStatus:
        return ModelStatus(
            loaded=self._session is not None,
            reason=self._reason,
            onnx_path=str(config.onnx_path()),
            tokenizer_path=str(config.tokenizer_path()),
        )

    def load(self):  # noqa: ANN201
        if self._tried:
            return self._session, self._tokenizer
        with self._lock:
            if self._tried:
                return self._session, self._tokenizer
            self._tried = True
            try:
                onnx_file = config.onnx_path()
                tok_file = config.tokenizer_path()
                if not onnx_file.exists():
                    self._reason = f"ONNX model not found at {onnx_file}"
                    log.warning("prahari.ml: %s — falling back to the keyword extractor", self._reason)
                    return None, None
                if not tok_file.exists():
                    self._reason = f"tokenizer not found at {tok_file}"
                    log.warning("prahari.ml: %s — falling back to the keyword extractor", self._reason)
                    return None, None

                import onnxruntime as ort  # local import: optional dependency
                from tokenizers import Tokenizer

                options = ort.SessionOptions()
                options.intra_op_num_threads = 1
                options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self._session = ort.InferenceSession(
                    str(onnx_file), sess_options=options, providers=["CPUExecutionProvider"]
                )
                self._tokenizer = Tokenizer.from_file(str(tok_file))
                self._tokenizer.enable_truncation(config.MAX_LENGTH)
                self._reason = "ok"
                log.info("prahari.ml: neural extractor loaded from %s", onnx_file)
            except Exception as exc:  # noqa: BLE001 — any failure must fall back
                self._session = None
                self._tokenizer = None
                self._reason = f"{type(exc).__name__}: {exc}"
                log.warning(
                    "prahari.ml: could not load the neural extractor (%s) — "
                    "falling back to the keyword extractor",
                    self._reason,
                )
            return self._session, self._tokenizer

    def reset(self) -> None:
        """Test hook: forget the load attempt so a new path takes effect."""
        with self._lock:
            self._tried = False
            self._session = None
            self._tokenizer = None
            self._reason = "not loaded yet"


_RUNTIME = _Runtime()


def model_status() -> ModelStatus:
    _RUNTIME.load()
    return _RUNTIME.status


def reset_runtime() -> None:
    _RUNTIME.reset()


def _softmax(rows):  # noqa: ANN001, ANN202
    import numpy as np

    shifted = rows - rows.max(axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=-1, keepdims=True)


def predict_spans(text: str, threshold: float | None = None) -> list[CharSpan] | None:
    """Character spans predicted by the model, or None if it is unavailable."""
    session, tokenizer = _RUNTIME.load()
    if session is None or tokenizer is None:
        return None
    threshold = config.DEFAULT_ENTITY_THRESHOLD if threshold is None else threshold

    try:
        import numpy as np

        encoding = tokenizer.encode(text)
        ids = np.array([encoding.ids], dtype=np.int64)
        mask = np.array([encoding.attention_mask], dtype=np.int64)
        feeds = {"input_ids": ids, "attention_mask": mask}
        names = {i.name for i in session.get_inputs()}
        if "token_type_ids" in names:
            feeds["token_type_ids"] = np.zeros_like(ids)
        feeds = {k: v for k, v in feeds.items() if k in names}

        logits = session.run(None, feeds)[0][0]
        probs = _softmax(logits)

        # Recall-biased decoding: a token is an entity when the best NON-O class
        # clears the threshold, even if "O" is the argmax. At threshold 0.35 a
        # token the model is only moderately sure about still surfaces. See
        # config.DEFAULT_ENTITY_THRESHOLD for why the asymmetry is deliberate.
        tags: list[str] = []
        scores: list[float] = []
        for row in probs:
            best_entity = int(row[1:].argmax()) + 1
            entity_p = float(row[best_entity])
            if entity_p >= threshold:
                tags.append(ID_TO_LABEL[best_entity])
                scores.append(entity_p)
            else:
                tags.append("O")
                scores.append(float(row[0]))

        offsets = align_offsets(text, list(encoding.offsets))
        return bio_to_spans(tags, offsets, scores)
    except Exception as exc:  # noqa: BLE001
        log.warning("prahari.ml: inference failed (%s) — falling back", exc)
        return None


def _facts_from_spans(text: str, spans: list[CharSpan]) -> list[Fact]:
    """Typed facts from predicted spans, via the closed-vocabulary resolver."""
    facts: list[Fact] = []
    sentences = segment_sentences(text)

    def enclosing(span: CharSpan) -> str:
        """The sentence a span sits in, for resolving a too-tight prediction."""
        for sentence in sentences:
            if sentence.span.start <= span.start < sentence.span.end:
                return text[sentence.span.start : sentence.span.end]
        return text

    def add(kind: FactType, value: str, span: CharSpan, detail: str | None) -> None:
        facts.append(
            Fact(
                fact_type=kind,
                value=value,
                span=Span(span.start, span.end),
                matched_text=text[span.start : span.end],
                detail=detail,
            )
        )

    for span in spans:
        body = text[span.start : span.end]
        if span.label == "ENERGY_SOURCE":
            source = resolve_energy(body) or resolve_energy(enclosing(span))
            if source:
                add(FactType.ENERGY_PHRASE, source.value, span, f"neural:{span.score:.2f}")
        elif span.label == "MAGNITUDE_CUE":
            add(FactType.MEASUREMENT, "neural_magnitude", span, body)
        elif span.label == "CONTROL_MENTION":
            key = resolve_control(body) or resolve_control(enclosing(span))
            if key:
                from prahari.domain.controls import CONTROLS_BY_KEY

                add(
                    FactType.CONTROL_MENTION,
                    key,
                    span,
                    "direct" if CONTROLS_BY_KEY[key].is_direct else "indirect",
                )
        elif span.label == "CONTROL_NEGATION":
            # A model trained to be tight can predict "not" where the state is
            # only nameable from "was not wearing". Refusing to type that span
            # would throw away a detection the model got right, which is the
            # opposite of the operating point this system is tuned for. So a
            # miss retries against the enclosing sentence before giving up.
            status = resolve_control_status(body) or resolve_control_status(enclosing(span))
            if status:
                add(FactType.CONTROL_STATUS, status.value, span, f"neural:{span.score:.2f}")
    return facts


def extract(
    text: str,
    threshold: float | None = None,
    mode: str | None = None,
) -> ExtractedFacts:
    """Extract facts using the model, falling back to keywords if unavailable.

    Modes
    -----
    union    (default) Facts from both extractors, deduplicated. The model adds
             spans the phrase lists never had; the phrase lists keep the
             precision they already have on the terms they do know. This is the
             recall-maximising option, which is the operating point the safety
             case calls for.
    replace  Model facts only, with the keyword extractor used solely for
             sentence segmentation and the fact types the model does not tag
             (injury, event markers, Life-Saving Rule cues). Closer to the
             letter of "replaces the keyword extractor"; measurably lower recall
             until the model is trained on real reports, so it is not default.
    """
    mode = mode or "union"
    baseline = keyword_extract(text)
    spans = predict_spans(text, threshold)
    if spans is None:
        return baseline

    neural = _facts_from_spans(text, spans)

    if mode == "replace":
        # The model tags six entity types; the engine also needs injury, event
        # and rule cues, which stay with the deterministic matcher.
        keep = {
            FactType.INJURY,
            FactType.INCIDENT_MARKER,
            FactType.CONDITION_MARKER,
            FactType.LSR_PHRASE,
            FactType.HIGH_ENERGY_CUE,
        }
        merged = [f for f in baseline.facts if f.fact_type in keep] + neural
    else:
        merged = list(baseline.facts) + neural

    seen: set[tuple] = set()
    deduped: list[Fact] = []
    for fact in merged:
        key = (fact.fact_type, fact.value, fact.span.start, fact.span.end)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fact)

    deduped.sort(key=lambda f: (f.span.start, f.span.end, f.fact_type.value, f.value))
    return ExtractedFacts(
        text=text,
        facts=tuple(deduped),
        sentences=segment_sentences(text),
        extractor_version=f"{NEURAL_VERSION}+{mode}",
    )
