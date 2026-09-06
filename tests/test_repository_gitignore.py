from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def test_private_local_files_are_ignored():
    private_paths = (
        ".env",
        ".env.production",
        ".agents/session.json",
        "docs/local/wordquery/status.md",
        "components/wordquery/AGENTS.md",
        "notes.private.md",
        "release-handoff.md",
        "credentials.json",
        "secrets.json",
        "service-account-production.json",
        "server.pem",
        "server.key",
        "identity.p12",
        "identity.pfx",
        "id_ed25519",
        "debug.log",
        "lexicon.sqlite3",
        "lexicon.sqlite3-wal",
        "local.db",
        "var/wordquery/current/lexicon.sqlite3",
        "var/wordquery/releases/20260830/manifest.json",
        "var/wordquery/sources/JMdict_e.gz",
        "components/wordquery/var/lexicon.sqlite3",
        "components/wordquery/data/raw/JMdict_e.gz",
        "components/wordquery/reports/quality.json",
        "reports/formal-human-gate.json",
        "tools/wordquery_formal_review_core.js",
        "tools/wordquery_formal_review_workbench.html",
        "tools/wordquery_formal_review_workbench.js",
        "tests/wordquery/test_formal_review_workbench.py",
    )

    assert all(is_ignored(path) for path in private_paths)


def test_reviewed_public_and_example_files_remain_trackable():
    public_paths = (
        ".env.example",
        "credentials.example.json",
        "docs/public/wordquery/README.md",
        "components/wordquery/data/manual/additions.tsv",
    )

    assert all(not is_ignored(path) for path in public_paths)
