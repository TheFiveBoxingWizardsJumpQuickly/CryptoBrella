import importlib
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_secret_stubs():
    if "app.secret" not in sys.modules:
        sys.modules["app.secret"] = types.ModuleType("app.secret")

    cryptobrella = types.ModuleType("app.secret.cryptobrella")
    cryptobrella.cb_challenge_contents = lambda mode="keys", pageid=None: [] if mode == "keys" else {}
    cryptobrella.cb_contents = lambda mode="keys", pageid=None: [] if mode == "keys" else {}
    sys.modules["app.secret.cryptobrella"] = cryptobrella


@pytest.fixture()
def client():
    _install_secret_stubs()
    sys.modules.pop("app.app", None)

    app_module = importlib.import_module("app.app")
    app = app_module.app
    app.config["TESTING"] = False

    with app.test_client() as c:
        yield c
