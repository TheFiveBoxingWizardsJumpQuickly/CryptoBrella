import importlib
import sys
import types

import pytest


def _install_secret_stubs():
    if "app.secret" not in sys.modules:
        sys.modules["app.secret"] = types.ModuleType("app.secret")

    cryptobrella = types.ModuleType("app.secret.cryptobrella")
    cryptobrella.cb_challenge_contents = lambda mode="keys", pageid=None: [] if mode == "keys" else {}
    cryptobrella.cb_contents = lambda mode="keys", pageid=None: [] if mode == "keys" else {}
    sys.modules["app.secret.cryptobrella"] = cryptobrella


@pytest.fixture()
def client(monkeypatch):
    _install_secret_stubs()
    sys.modules.pop("app.app", None)

    app_module = importlib.import_module("app.app")
    app = app_module.app
    app.config["TESTING"] = False

    gear = importlib.import_module("app.gear")

    with app.test_client() as c:
        yield c


def test_get_basic_pages(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Crypto Brella" in body
    assert 'type="search"' in body
    assert "Cryptography" in body
    assert "Remember Ingress" in body
    assert client.get("/about").status_code == 200
    link_resp = client.get("/link")
    assert link_resp.status_code == 200
    link_body = link_resp.get_data(as_text=True)
    assert "Built with" in link_body
    assert "Useful external sites related to ciphers" in link_body


def test_missing_page_uses_custom_404(client):
    resp = client.get("/not-found")
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    assert "404 Not Found" in body
    assert "The page you are looking for could not be found." in body
    assert "Back to Top" in body


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
