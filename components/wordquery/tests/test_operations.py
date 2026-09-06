from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from wordquery_jp.operations import (
    evaluate_diff_policy,
    public_data_is_fresh,
    read_state,
    send_notification,
    status_report,
    update_due,
    write_state,
)

NOW = datetime(2026, 8, 23, 3, 0, tzinfo=UTC)


def test_update_is_due_after_21_days():
    state = {"last_success_at": (NOW - timedelta(days=20)).isoformat()}
    assert not update_due(state, now=NOW)

    state["last_success_at"] = (NOW - timedelta(days=21)).isoformat()
    assert update_due(state, now=NOW)


def test_public_freshness_expires_after_31_days():
    assert public_data_is_fresh(
        {"last_success_at": (NOW - timedelta(days=31)).isoformat()}, now=NOW
    )
    assert not public_data_is_fresh(
        {"last_success_at": (NOW - timedelta(days=31, seconds=1)).isoformat()},
        now=NOW,
    )


def test_state_is_written_atomically_and_reported(tmp_path, monkeypatch):
    monkeypatch.delenv("WORDQUERY_SMTP_HOST", raising=False)
    write_state(tmp_path, {"last_success_at": NOW.isoformat(), "last_status": "activated"})

    assert read_state(tmp_path)["last_status"] == "activated"
    report = status_report(tmp_path)
    assert report["freshness_timestamp_valid"]
    assert not report["fresh"]  # No active dictionary is attached to this state.
    assert not report["notification_configured"]
    assert json.loads((tmp_path / "state.json").read_text())["last_status"] == "activated"


def test_diff_policy_quarantines_large_accepted_change(tmp_path):
    before = tmp_path / "before.sqlite3"
    after = tmp_path / "after.sqlite3"
    _write_words(before, 1000)
    _write_words(after, 1021)
    diff = {
        "added": [{"status": "accepted"} for _ in range(21)],
        "removed": [],
        "changed": [],
    }

    assert evaluate_diff_policy(before, after, diff) == [
        "accepted_count_delta_exceeds_2_percent"
    ]


def test_notification_is_optional_until_smtp_is_configured(monkeypatch):
    for name in ("WORDQUERY_SMTP_HOST", "WORDQUERY_SMTP_FROM", "WORDQUERY_SMTP_TO"):
        monkeypatch.delenv(name, raising=False)

    assert not send_notification("subject", "body")


def _write_words(path: Path, count: int) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE words (status TEXT NOT NULL)")
        connection.executemany(
            "INSERT INTO words(status) VALUES ('accepted')",
            [() for _ in range(count)],
        )
