import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

import pytest

from app.cipher.fn import braille_ja_d
from app.cipher.kakushi import kakushi_decode, kakushi_encode
from app.cipher.transposition import (
    columnar_d,
    columnar_e,
    railfence_d,
    railfence_e,
    skip_d,
    skip_e,
    swap_xy_axes,
)


def _norm(v):
    if is_dataclass(v):
        return _norm(asdict(v))
    if isinstance(v, dict):
        return {str(k): _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, tuple):
        return [_norm(x) for x in v]
    if isinstance(v, bytes):
        return {"__bytes_hex__": v.hex()}
    return v


FUNCTIONS = {
    "columnar_e": lambda c, col: "".join(columnar_e(c, col)),
    "columnar_d": lambda c, col: "".join(columnar_d(c, col)),
    "columnar_roundtrip": lambda c, col: "".join(columnar_d("".join(columnar_e(c, col)), col)),
    "railfence_e": railfence_e,
    "railfence_d": railfence_d,
    "railfence_roundtrip": lambda text, rails, offset=0: railfence_d(
        railfence_e(text, rails, offset), rails, offset
    ),
    "skip_e": skip_e,
    "skip_d": skip_d,
    "skip_roundtrip": lambda text, step: skip_d(skip_e(text, step), step),
    "swap_xy_axes": swap_xy_axes,
    "braille_ja_d": braille_ja_d,
    "kakushi_encode": kakushi_encode,
    "kakushi_decode": kakushi_decode,
}


def _load_cases():
    path = Path(__file__).parent / "fixtures" / "transposition_kakushi_vectors.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_transposition_kakushi_vectors(case):
    fn = FUNCTIONS[case["function"]]
    args = dict(case["args"])

    try:
        actual = _norm(fn(**args))
    except Exception as exc:
        assert case.get("expected_exception") == exc.__class__.__name__
        return

    assert "expected_exception" not in case
    assert actual == case["expected"]
