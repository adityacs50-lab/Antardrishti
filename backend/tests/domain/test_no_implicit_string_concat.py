"""No accidentally-merged trigger phrases in the domain vocabularies.

Python silently concatenates adjacent string literals, so a single missing
comma inside a phrase tuple turns two lookup phrases into one that can never
match:

    phrases=("chain brake" "load limiter",)   ->  ("chain brakeload limiter",)

That is a silent recall hole: the extractor stops recognising BOTH phrases and
nothing fails. Twenty-nine of these were found at once in `controls.py` and
`high_energy.py`, costing 58 trigger phrases.

The vocabularies are long, hand-maintained, comma-separated lists — exactly the
shape that breeds this bug — so the invariant is asserted at source level,
where it is unambiguous, rather than guessed at from phrase content.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

DOMAIN = Path(__file__).resolve().parents[2] / "prahari" / "domain"
VOCAB_MODULES = ["controls.py", "high_energy.py", "energy.py", "lsr.py"]


def _implicitly_concatenated(source: str) -> list[tuple[int, str]]:
    """Constant strings the parser built from more than one literal.

    A JoinedStr (f-string) is excluded; deliberate multi-line prose is excluded
    by only inspecting literals that live inside a tuple or list, which is where
    the vocabularies are and where prose never is.
    """
    tree = ast.parse(source)
    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Tuple, ast.List)):
            continue
        for element in node.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                continue
            # Re-parse the exact source segment: if it holds two adjacent
            # string literals, the parser merged them.
            segment = ast.get_source_segment(source, element)
            if segment is None:
                continue
            try:
                inner = ast.parse(segment, mode="eval").body
            except SyntaxError:  # pragma: no cover - segment is always valid
                continue
            if isinstance(inner, ast.Constant) and segment.count('"') + segment.count("'") > 2:
                offenders.append((element.lineno, element.value))
    return offenders


@pytest.mark.parametrize("module", VOCAB_MODULES)
def test_vocabulary_has_no_merged_phrases(module: str) -> None:
    path = DOMAIN / module
    if not path.exists():  # pragma: no cover
        pytest.skip(f"{module} not present")
    offenders = _implicitly_concatenated(path.read_text(encoding="utf-8"))
    assert not offenders, (
        f"{len(offenders)} phrase(s) in {module} were built from adjacent string "
        f"literals — almost certainly a missing comma, which silently deletes two "
        f"trigger phrases. Offenders: {offenders[:5]}"
    )
