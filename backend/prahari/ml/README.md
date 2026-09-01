# prahari · ml

Fact extraction. **Never decides a verdict.**

Two implementations behind one contract:

| file | what it is |
|---|---|
| `extractor.py` | Deterministic keyword/pattern matcher. Always available, no dependencies. |
| `neural_extractor.py` | MuRIL token classifier via ONNX. Used when `models/prahari.onnx` exists. |
| `__init__.py` | `extract_facts()` — the single entry point; routes and falls back. |
| `resolver.py` | Predicted span → typed value, via the closed vocabularies. |
| `labels.py` | BIO encode/decode. |
| `config.py` | Paths, and the recall-biased threshold with its rationale. |
| `training/` | Build-time only. Never imported by the app. |

Both return `ExtractedFacts`, so `rules/engine.py` cannot tell which one ran and
**no rule changes when the model is swapped in**. That is the whole benefit of
the neuro-symbolic split, and it is enforced by a test.

## Fallback

Missing model, missing tokenizer, corrupt ONNX file, or any exception during
inference → one warning is logged and the keyword extractor's output is
returned. The demo degrades; it never hard-fails. Tested three ways.

## Pinning

```bash
PRAHARI_EXTRACTOR=keyword        # force the deterministic path
PRAHARI_EXTRACTOR_MODE=replace   # neural facts only (default: union)
PRAHARI_ENTITY_THRESHOLD=0.25    # lower = more recall
```

`union` is the default rather than `replace`: it keeps every keyword fact and
adds the model's, which maximises recall. That is the operating point the
safety case calls for. `replace` exists and is one env var away.

See `training/README.md` for the pipeline and the reasoning behind the label
source, the model choice and the threshold.
