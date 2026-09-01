"""Fact extraction. Two implementations, one contract.

`extract_facts` is the single entry point the rule engine uses. It routes to the
ONNX token classifier when a trained model is present, and to the deterministic
keyword extractor when it is not. Both return `ExtractedFacts`, so the engine
cannot tell them apart and no rule changes when the model is swapped in.

Set PRAHARI_EXTRACTOR=keyword to pin the deterministic path (useful when
measuring what the model actually adds).
"""

from __future__ import annotations

import os

from prahari.ml.extractor import EXTRACTOR_VERSION, ExtractedFacts, Fact, FactType, Span
from prahari.ml.extractor import extract as keyword_extract

__all__ = [
    "extract_facts", "keyword_extract", "ExtractedFacts", "Fact", "FactType",
    "Span", "EXTRACTOR_VERSION", "active_extractor",
]


def active_extractor() -> str:
    """Which path is live: 'keyword', or 'neural:<mode>'."""
    if os.environ.get("PRAHARI_EXTRACTOR", "auto").lower() == "keyword":
        return "keyword"
    from prahari.ml.neural_extractor import model_status

    status = model_status()
    if not status.loaded:
        return "keyword"
    return f"neural:{os.environ.get('PRAHARI_EXTRACTOR_MODE', 'union')}"


def extract_facts(text: str) -> ExtractedFacts:
    """Extract structured facts. Never raises because of a missing model."""
    if os.environ.get("PRAHARI_EXTRACTOR", "auto").lower() == "keyword":
        return keyword_extract(text)
    from prahari.ml.neural_extractor import extract as neural_extract

    return neural_extract(text, mode=os.environ.get("PRAHARI_EXTRACTOR_MODE", "union"))
