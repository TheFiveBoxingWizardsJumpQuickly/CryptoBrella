import importlib
import inspect
import json
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXCLUDED_FUNCTIONS = {"to_what3words_gen", "to_coordinates_gen"}


class DummyRequest:
    def __init__(self, payload):
        self.json = payload


def _ensure_secret_stub():
    if "app.secret" not in sys.modules:
        sys.modules["app.secret"] = types.ModuleType("app.secret")


def _apply_stubs(monkeypatch, gear):
    def stub_password_generate(length, table):
        if length <= 0:
            return ""
        if not table:
            return ""
        out = []
        for i in range(length):
            out.append(table[i % len(table)])
        return "".join(out)

    monkeypatch.setattr(gear, "password_generate", stub_password_generate)
    monkeypatch.setattr(gear, "passcode_get_random_id", lambda: 42)
    monkeypatch.setattr(gear, "passcode_get_today_id", lambda: 77)
    monkeypatch.setattr(
        gear,
        "passcode_get_list",
        lambda: [
            {"id": 1, "date": "2026-03-01", "code": "ABCDEF123456", "tag": "Difficulty: Easy"},
            {"id": 2, "date": "2026-03-02", "code": "QWERTY987654", "tag": "Difficulty: Hard"},
        ],
    )

    def stub_validate(_pid, input_answer):
        if input_answer == "ok":
            return ["Confirmed", "Invalid.", "Invalid."]
        if input_answer == "near":
            return ["Number part might be wrong.", "Invalid.", "Invalid."]
        return ["Invalid.", "Invalid.", "Invalid."]

    monkeypatch.setattr(gear, "passcode_validate_answer", stub_validate)
    monkeypatch.setattr(
        gear,
        "passcode_get_reward",
        lambda _pid, _index: ["100 AP", "100 XM", "L1 Resonator", "L1 Xmp Burster", "L4 Power Cube"],
    )
    monkeypatch.setattr(
        gear,
        "passcode_get_filtered_keywords",
        lambda pattern: [w for w in ["agent", "alpha", "abaddon", "delta"] if pattern in w],
    )


def _normalize(value):
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _load_fixture():
    path = Path(__file__).parent / "fixtures" / "gear_regression_vectors.json"
    with path.open(encoding="utf-8") as f:
        cases = json.load(f)["cases"]
    return [case for case in cases if case["function"] not in EXCLUDED_FUNCTIONS]


@pytest.fixture(scope="module")
def gear_module():
    _ensure_secret_stub()
    return importlib.import_module("app.gear")


def _request_handlers(gear):
    handlers = []
    for name, fn in inspect.getmembers(gear, inspect.isfunction):
        if fn.__module__ != "app.gear":
            continue
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        if len(params) == 1 and params[0].name == "request":
            handlers.append(name)
    return sorted(set(handlers))


def test_fixture_covers_all_request_handlers(gear_module):
    fixture_functions = sorted({c["function"] for c in _load_fixture()})
    handlers = [name for name in _request_handlers(gear_module) if name not in EXCLUDED_FUNCTIONS]
    assert fixture_functions == handlers


@pytest.mark.parametrize("case", _load_fixture(), ids=lambda c: c["id"])
def test_gear_regression_vectors(case, gear_module, monkeypatch):
    _apply_stubs(monkeypatch, gear_module)
    fn = getattr(gear_module, case["function"])
    result = fn(DummyRequest(case["json"]))
    assert _normalize(result) == case["expected"]
