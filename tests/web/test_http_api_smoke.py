import importlib
import sys
import types

import pytest


def _install_secret_stubs():
    if "app.secret" not in sys.modules:
        sys.modules["app.secret"] = types.ModuleType("app.secret")

    apikey = types.ModuleType("app.secret.apikey")
    apikey.get_w3w_apikey = lambda: "DUMMY_W3W_API_KEY"
    apikey.get_line_channel_access_token = lambda: "DUMMY_LINE_TOKEN"
    apikey.get_line_channel_secret = lambda: "DUMMY_LINE_SECRET"
    sys.modules["app.secret.apikey"] = apikey

    cryptobrella = types.ModuleType("app.secret.cryptobrella")
    cryptobrella.cb_challenge_contents = lambda mode="keys", pageid=None: [] if mode == "keys" else {}
    cryptobrella.cb_contents = lambda mode="keys", pageid=None: [] if mode == "keys" else {}
    sys.modules["app.secret.cryptobrella"] = cryptobrella


@pytest.fixture()
def client(monkeypatch):
    _install_secret_stubs()
    sys.modules.pop("app.line_bot_blueprint", None)
    sys.modules.pop("app.app", None)

    app_module = importlib.import_module("app.app")
    app = app_module.app
    app.config["TESTING"] = False

    gear = importlib.import_module("app.gear")
    monkeypatch.setattr(gear, "get_w3w_apikey", lambda: "DUMMY_W3W_API_KEY")
    monkeypatch.setattr(
        gear,
        "convert_to_3wa",
        lambda apikey, latitude, longitude, language: {
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
        },
    )

    with app.test_client() as c:
        yield c


def test_get_basic_pages(client):
    assert client.get("/").status_code == 200
    assert client.get("/about").status_code == 200


def test_post_gear_rot_success(client):
    resp = client.post("/gear/rot_gen", json={"input_text": "Abc-123"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert "0" in body
    assert "00: Abc-123" in body["0"]


def test_post_gear_railfence_empty_offset_branch(client):
    resp = client.post(
        "/gear/railfence_gen",
        json={"input_text": "WEAREDISCOVEREDFLEEATONCE", "mode": "Encode", "offset": ""},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert "0" in body
    assert body["0"].startswith("Offset = 0")


def test_post_gear_number_conv_empty_base_branch(client):
    resp = client.post(
        "/gear/number_conv_gen",
        json={"input_text": "10,255", "base": ""},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["1"] == "from base: 10"


def test_post_gear_unknown_handler_returns_500(client):
    resp = client.post("/gear/not_existing_handler", json={"input_text": "abc"})
    assert resp.status_code == 500


def test_post_gear_missing_key_returns_500(client):
    resp = client.post("/gear/vigenere_gen", json={"input_text": "AttackAtDawn"})
    assert resp.status_code == 500
