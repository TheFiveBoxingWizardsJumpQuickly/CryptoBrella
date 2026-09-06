from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from component_paths import REPOSITORY_ROOT, WORDQUERY_SOURCE, activate_wordquery
from wordquery_cli import main as wordquery_main


def test_activate_wordquery_prioritizes_checked_out_source(monkeypatch):
    source = str(WORDQUERY_SOURCE)
    monkeypatch.setattr(sys, "path", [entry for entry in sys.path if entry != source])

    activated = activate_wordquery()

    assert activated == WORDQUERY_SOURCE
    assert sys.path[0] == source
    spec = importlib.util.find_spec("wordquery_jp")
    assert spec is not None
    assert spec.origin is not None
    assert WORDQUERY_SOURCE in Path(spec.origin).parents


def test_wordquery_imports_without_site_packages_or_editable_install(tmp_path):
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(REPOSITORY_ROOT)!r}); "
        "from component_paths import activate_wordquery; "
        "activate_wordquery(); "
        "import wordquery_jp; "
        "print(wordquery_jp.__file__)"
    )

    result = subprocess.run(
        [sys.executable, "-S", "-c", code],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert WORDQUERY_SOURCE in Path(result.stdout.strip()).parents


def test_flask_layer_loads_component_after_editable_path_is_removed(tmp_path):
    source = str(WORDQUERY_SOURCE)
    code = (
        "import sys; "
        f"sys.path = [p for p in sys.path if p != {source!r}]; "
        f"sys.path.insert(0, {str(REPOSITORY_ROOT)!r}); "
        "from app.wordquery import blueprint; "
        "import wordquery_jp; "
        "print(wordquery_jp.__file__)"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert WORDQUERY_SOURCE in Path(result.stdout.strip()).parents


def test_production_requirements_do_not_install_component_editable():
    requirements = (REPOSITORY_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "-e " not in requirements
    assert "regex>=" in requirements
    assert "lxml>=" in requirements


def test_web_startup_without_fcntl_and_updater_fails_before_writing(tmp_path):
    code = f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(REPOSITORY_ROOT)!r})
sys.modules['fcntl'] = None
from flask import Flask
from app.wordquery.blueprint import register_wordquery
from wordquery_jp.operations import update_lexicon
app = Flask('app', root_path={str(REPOSITORY_ROOT / 'app')!r})
register_wordquery(app, {{
    'WORDQUERY_DB': {str(tmp_path / 'missing.sqlite3')!r},
    'WORDQUERY_RELEASE_MODE': 'updated',
    'WORDQUERY_ENFORCE_FRESHNESS': False,
}})
assert app.test_client().get('/wordquery/').status_code == 503
state = Path({str(tmp_path / 'update-state')!r})
try:
    update_lexicon(state)
except RuntimeError as exc:
    assert 'WSL/Linux' in str(exc)
else:
    raise AssertionError('Updater must require Unix locking')
assert not state.exists()
"""
    subprocess.run([sys.executable, "-c", code], cwd=tmp_path, check=True, capture_output=True)


def test_repository_cli_runs_without_console_script(tmp_path, capsys):
    result = wordquery_main(["status", "--state-dir", str(tmp_path)])

    assert result == 1
    assert '"fresh": false' in capsys.readouterr().out


def test_repository_cli_help(capsys):
    with pytest.raises(SystemExit) as exited:
        wordquery_main(["--help"])

    assert exited.value.code == 0
    assert "formal-review-gate" in capsys.readouterr().out
