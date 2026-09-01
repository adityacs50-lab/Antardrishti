"""Evidence-span colours must not sit inside a Tailwind @layer.

`HighlightedReport.tsx` builds its class names dynamically:

    className={cn("cue", `cue-${seg.kind}`, ...)}

Tailwind's content scanner only sees literal strings, so it never sees
"cue-energy", "cue-control" or "cue-context" and purges those rules out of
`@layer components` at build time. The spans still render, with the right
classes and the right text — and no colour at all.

That silently breaks the single screen the whole product is pitched on:
DEMO.md Step 2 says "point at the colour-coded highlights", and there are none.
It cannot be caught by looking at the source, only by looking at the built CSS
or the running page, which is exactly why it survived until someone ran the app.

Plain top-level CSS is emitted verbatim and cannot be purged. This test pins
that arrangement.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parents[2] / "web" / "src" / "index.css"
CUE_CLASSES = [".cue-energy", ".cue-control", ".cue-context"]


def _layer_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges covered by any top-level @layer block."""
    spans: list[tuple[int, int]] = []
    for match in re.finditer(r"@layer\s+[\w\s,]+\{", text):
        depth, i = 0, match.end() - 1
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((match.start(), i))
                    break
            i += 1
    return spans


@pytest.mark.parametrize("cls", CUE_CLASSES)
def test_cue_colour_rule_is_outside_any_layer(cls: str) -> None:
    if not CSS.exists():  # pragma: no cover
        pytest.skip("web/src/index.css not present")
    text = CSS.read_text(encoding="utf-8")

    positions = [m.start() for m in re.finditer(re.escape(cls) + r"\s*\{", text)]
    assert positions, f"{cls} is not defined in index.css at all"

    layers = _layer_spans(text)
    for pos in positions:
        inside = next((s for s in layers if s[0] < pos < s[1]), None)
        assert inside is None, (
            f"{cls} is defined inside an @layer block. Tailwind will purge it, "
            f"because HighlightedReport builds the class name dynamically and the "
            f"literal string never appears in any scanned file. The evidence "
            f"highlighting will render invisible. Move it to top-level CSS."
        )
