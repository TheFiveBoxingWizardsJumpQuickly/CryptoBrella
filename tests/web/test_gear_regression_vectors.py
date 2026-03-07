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


class DummyRequest:
    def __init__(self, payload):
        self.json = payload


def _ensure_secret_stub():
    if "app.secret" not in sys.modules:
        sys.modules["app.secret"] = types.ModuleType("app.secret")
    if "app.secret.apikey" not in sys.modules:
        mod = types.ModuleType("app.secret.apikey")
        mod.get_w3w_apikey = lambda: "DUMMY_W3W_API_KEY"
        sys.modules["app.secret.apikey"] = mod


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

    def stub_convert_to_3wa(apikey, latitude, longitude, language):
        return {
            "language": language,
            "words": "filled.count.soap",
            "coordinates": {"lat": float(latitude), "lng": float(longitude)},
            "square": {
                "southwest": {"lat": float(latitude) - 0.001, "lng": float(longitude) - 0.001},
                "northeast": {"lat": float(latitude) + 0.001, "lng": float(longitude) + 0.001},
            },
            "country": "JP",
            "nearestPlace": "Tokyo",
            "map": "https://example.invalid/map",
        }

    def stub_convert_to_coordinates(apikey, words):
        if words == "badformat":
            return {"format error": "badformat is not W3W format."}
        if words == "apifail":
            return {"error": "simulated API error"}
        return {
            "language": "en",
            "words": words,
            "coordinates": {"lat": 35.0, "lng": 139.0},
            "square": {
                "southwest": {"lat": 34.999, "lng": 138.999},
                "northeast": {"lat": 35.001, "lng": 139.001},
            },
            "country": "JP",
            "nearestPlace": "Tokyo",
            "map": "https://example.invalid/map2",
        }

    monkeypatch.setattr(gear, "password_generate", stub_password_generate)
    monkeypatch.setattr(gear, "get_w3w_apikey", lambda: "DUMMY_W3W_API_KEY")
    monkeypatch.setattr(gear, "convert_to_3wa", stub_convert_to_3wa)
    monkeypatch.setattr(gear, "convert_to_coordinates", stub_convert_to_coordinates)
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
        return json.load(f)["cases"]


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
    handlers = _request_handlers(gear_module)
    assert fixture_functions == handlers


@pytest.mark.parametrize("case", _load_fixture(), ids=lambda c: c["id"])
def test_gear_regression_vectors(case, gear_module, monkeypatch):
    _apply_stubs(monkeypatch, gear_module)
    fn = getattr(gear_module, case["function"])
    result = fn(DummyRequest(case["json"]))
    assert _normalize(result) == case["expected"]
