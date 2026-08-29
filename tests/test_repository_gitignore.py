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
