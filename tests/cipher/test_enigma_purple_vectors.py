import json
from pathlib import Path

import pytest

from app.cipher.enigma import enigma
from app.cipher.purple import purple_decode, purple_encode


FUNCTIONS = {
    "enigma": enigma,
    "purple_encode": purple_encode,
    "purple_decode": purple_decode,
}


def _load_cases():
    path = Path(__file__).parent / "fixtures" / "enigma_purple_vectors.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_enigma_purple_vectors(case):
    fn = FUNCTIONS[case["function"]]
    args = dict(case["args"])
    try:
        actual = fn(**args)
    except Exception as exc:
        assert case.get("expected_exception") == exc.__class__.__name__
        return

    assert "expected_exception" not in case
    assert actual == case["expected"]
