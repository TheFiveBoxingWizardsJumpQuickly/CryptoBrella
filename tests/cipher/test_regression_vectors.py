import json
from pathlib import Path

import pytest

from app.cipher.fn import (
    affine_d,
    affine_e,
    atbash,
    beaufort,
    hexbash,
    rot,
    table_subtitution,
    uu_decode,
    uu_encode,
    vig_d,
    vig_d_auto,
    vig_e,
    vig_e_auto,
)


FUNCTIONS = {
    "rot": rot,
    "vig_e": vig_e,
    "vig_d": vig_d,
    "beaufort": beaufort,
    "vig_e_auto": vig_e_auto,
    "vig_d_auto": vig_d_auto,
    "atbash": atbash,
    "hexbash": hexbash,
    "affine_e": affine_e,
    "affine_d": affine_d,
    "table_subtitution": table_subtitution,
    "uu_encode": uu_encode,
    "uu_decode": uu_decode,
}


def _load_cases():
    fixture_path = Path(__file__).parent / "fixtures" / "regression_vectors.json"
    with fixture_path.open(encoding="utf-8") as f:
        payload = json.load(f)
    return payload["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_regression_vectors(case):
    fn = FUNCTIONS[case["function"]]
    args = dict(case["args"])

    if case["function"] == "uu_encode":
        args["byte"] = bytes.fromhex(args.pop("byte_hex"))

    try:
        result = fn(**args)
    except Exception as exc:
        assert case.get("expected_exception") == exc.__class__.__name__
        return

    assert "expected_exception" not in case
    if "expected_hex" in case:
        assert isinstance(result, (bytes, bytearray))
        assert bytes(result).hex() == case["expected_hex"]
    else:
        assert result == case["expected"]
