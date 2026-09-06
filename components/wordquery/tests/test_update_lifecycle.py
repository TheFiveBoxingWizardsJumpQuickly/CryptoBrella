import hashlib
import json
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from wordquery_jp import operations as ops
from wordquery_jp.lexicon.builder import BuildConfig, build_database


@pytest.fixture
def setup_update(tmp_path, monkeypatch):
    root = ops.component_root()
    baseline = tmp_path / "reviewed"
    baseline.mkdir()
    database = baseline / "lexicon.sqlite3"
    build_database(BuildConfig(
        output=database, additions=root / "tests/fixtures/manual_additions.tsv",
    ))
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT OR REPLACE INTO metadata VALUES ('source.jmdict.sha256', 'old')")
    for folder in ("manual", "gold"):
        shutil.copytree(root / "data" / folder, baseline / folder)
    shutil.copyfile(root / "data/sources.toml", baseline / "sources.toml")
    manifest = {
        "release_schema_version": 1, "formal_human_review": {"passed": True},
        "database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
        "database_input_hash": ops._database_input_hash(database),
        "metadata": {"source.jmdict.sha256": "old"},
    }
    (baseline / "manifest.json").write_text(json.dumps(manifest))
    state_dir = tmp_path / "state"
    ops.initialize_updates(state_dir, database)
    ops.build_search_index(database)
    monkeypatch.setattr(ops, "send_notification", lambda *a, **kw: False)
    monkeypatch.setattr(ops, "reload_pythonanywhere_webapp", lambda: None)
    return state_dir, database


def latest(monkeypatch, sha):
    monkeypatch.setattr(ops, "_download_latest_jmdict", lambda root, work: ops.SourceDownload(
        work / "latest.gz", sha, "2026-09-06",
    ))


def fake_build(monkeypatch, database, failures=()):
    def build(state_dir, root, work, source, **kwargs):
        target = work / "lexicon.sqlite3"
        shutil.copyfile(database, target)
        with sqlite3.connect(target) as connection:
            connection.execute("UPDATE metadata SET value='new-input' WHERE key='input_hash'")
            connection.execute("UPDATE metadata SET value=? WHERE key='source.jmdict.sha256'",
                               (source.sha256,))
        manifest = {"input_hash": "new-input", "failures": list(failures),
                    "sources": {"jmdict": {"sha256": source.sha256}}}
        (work / "manifest.json").write_text(json.dumps(manifest))
        return {"manifest": manifest, "failures": list(failures)}
    monkeypatch.setattr(ops, "_build_candidate", build)


def test_initialize_does_not_invent_freshness(setup_update):
    state_dir, database = setup_update
    assert not ops.public_data_is_fresh(ops.read_state(state_dir))
    assert (state_dir / "current").resolve() == database.parent
    with pytest.raises(ValueError, match="already initialized"):
        ops.initialize_updates(state_dir, database)


def test_update_smoke_uses_current_request_schema(setup_update):
    _, database = setup_update
    report = ops._run_smoke(database)
    assert report["failures"] == []
    assert len(report["durations_ms"]) == 8


def test_candidate_build_packages_index_and_survives_directory_move(setup_update, monkeypatch):
    from wordquery_jp.repository import load_snapshot
    from wordquery_jp.search_index import file_hash, index_path
    state_dir, _ = setup_update
    root = ops.component_root()
    fixtures = root / "tests/fixtures"
    work = state_dir / "work/fixture-build"
    work.mkdir()
    monkeypatch.setattr(ops, "_prepare_sudachi", lambda *a: fixtures / "sudachi_raw.csv")
    source = ops.SourceDownload(fixtures / "jmdict.xml", file_hash(fixtures / "jmdict.xml"),
                                "fixture")
    result = ops._build_candidate(state_dir, root, work, source, run_id="fixture-build",
                                  now=datetime.now(UTC))
    database = work / "lexicon.sqlite3"
    assert result["manifest"]["search_index"]["sha256"] == file_hash(index_path(database))
    assert result["manifest"]["smoke"]["failures"] == []
    destination = state_dir / "releases/fixture-build"
    work.rename(destination)
    snapshot = load_snapshot(destination / "lexicon.sqlite3")
    assert snapshot.auxiliary.search_index == index_path(destination / "lexicon.sqlite3")


def test_same_source_dry_run_does_not_extend_expiry(setup_update, monkeypatch):
    state_dir, _ = setup_update
    latest(monkeypatch, "old")
    before = (state_dir / "state.json").read_bytes()
    assert ops.update_lexicon(state_dir, dry_run=True).status == "validated"
    assert (state_dir / "state.json").read_bytes() == before
    assert ops.update_lexicon(state_dir).status == "already_current"
    state = ops.read_state(state_dir)
    assert ops.public_snapshot_is_fresh(state_dir, state["active_input_hash"])
    assert not ops.public_snapshot_is_fresh(state_dir, "another-worker-input")


def test_latest_identity_comes_from_database_not_manifest(setup_update, monkeypatch):
    state_dir, database = setup_update
    path = database.parent / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["metadata"]["source.jmdict.sha256"] = "new"
    path.write_text(json.dumps(manifest))
    latest(monkeypatch, "new")
    fake_build(monkeypatch, database, ["review-required"])
    assert ops.update_lexicon(state_dir).status == "quarantined"
    assert ops.read_state(state_dir)["last_success_at"] is None


@pytest.mark.parametrize("dry_run", [False, True])
def test_quarantine_never_refreshes_active_release(setup_update, monkeypatch, dry_run):
    state_dir, database = setup_update
    latest(monkeypatch, "new")
    fake_build(monkeypatch, database, ["excessive-diff"])
    before = ops.read_state(state_dir)
    assert ops.update_lexicon(state_dir, dry_run=dry_run).status == "quarantined"
    after = ops.read_state(state_dir)
    assert after["last_success_at"] == before["last_success_at"]
    assert (state_dir / "current").resolve() == database.parent
    if dry_run:
        assert after == before
    else:
        assert ops.update_due(after, now=datetime.now(UTC))


def test_activation_state_ready_before_reload_and_rollback_retains_date(setup_update, monkeypatch):
    state_dir, database = setup_update
    latest(monkeypatch, "old")
    ops.update_lexicon(state_dir)
    old_state = ops.read_state(state_dir)
    latest(monkeypatch, "new")
    fake_build(monkeypatch, database)
    def reload():
        assert ops.public_snapshot_is_fresh(state_dir, "new-input")
    monkeypatch.setattr(ops, "reload_pythonanywhere_webapp", reload)
    assert ops.update_lexicon(state_dir, force=True).status == "activated"
    ops.rollback_lexicon(state_dir, reload_webapp=False)
    assert ops.read_state(state_dir)["last_success_at"] == old_state["last_success_at"]
    assert (state_dir / "current").resolve() == database.parent


def test_reload_failure_restores_old_state(setup_update, monkeypatch):
    state_dir, database = setup_update
    latest(monkeypatch, "new")
    fake_build(monkeypatch, database)
    calls = []
    def reload():
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError("reload failed")
    monkeypatch.setattr(ops, "reload_pythonanywhere_webapp", reload)
    with pytest.raises(RuntimeError, match="reload failed"):
        ops.update_lexicon(state_dir)
    assert (state_dir / "current").resolve() == database.parent
    assert ops.read_state(state_dir)["last_success_at"] is None
    assert len(calls) == 2


def test_policy_change_fails_before_download(setup_update, monkeypatch):
    state_dir, _ = setup_update
    monkeypatch.setattr(ops, "update_policy_fingerprint", lambda root: "changed")
    monkeypatch.setattr(ops, "_download_latest_jmdict", lambda *a: pytest.fail("downloaded"))
    with pytest.raises(ValueError, match="policy"):
        ops.update_lexicon(state_dir)


def test_invalid_dates_do_not_authorize_publication():
    for raw in ["not-a-date", "2026-09-06", (datetime.now(UTC) + timedelta(days=1)).isoformat()]:
        assert not ops.public_data_is_fresh({"last_success_at": raw})


def test_notification_failure_does_not_undo_success(setup_update, monkeypatch):
    state_dir, database = setup_update
    latest(monkeypatch, "new")
    fake_build(monkeypatch, database)
    def fail(*a, **kw):
        raise OSError("smtp unavailable")
    monkeypatch.setattr(ops, "send_notification", fail)
    assert ops.update_lexicon(state_dir, reload_webapp=False).status == "activated"
    assert ops.public_snapshot_is_fresh(state_dir, "new-input")


def test_expired_rollback_is_refused(setup_update, monkeypatch):
    state_dir, database = setup_update
    latest(monkeypatch, "old")
    ops.update_lexicon(state_dir)
    state = ops.read_state(state_dir)
    state["last_success_at"] = (datetime.now(UTC) - timedelta(days=32)).isoformat()
    ops.write_state(state_dir, state)
    latest(monkeypatch, "new")
    fake_build(monkeypatch, database)
    ops.update_lexicon(state_dir, force=True, reload_webapp=False)
    current = (state_dir / "current").resolve()
    with pytest.raises(ValueError, match="expired"):
        ops.rollback_lexicon(state_dir, reload_webapp=False)
    assert (state_dir / "current").resolve() == current


def test_download_failure_retries_without_extending_deadline(setup_update, monkeypatch):
    state_dir, _ = setup_update
    def fail(*a):
        raise OSError("offline")
    monkeypatch.setattr(ops, "_download_latest_jmdict", fail)
    with pytest.raises(OSError, match="offline"):
        ops.update_lexicon(state_dir)
    state = ops.read_state(state_dir)
    assert state["last_success_at"] is None
    assert ops.update_due(state, now=datetime.now(UTC))


def test_failed_notification_retries_next_day(setup_update, monkeypatch):
    state_dir, _ = setup_update
    state = {"consecutive_failures": 1}
    calls = []
    monkeypatch.setattr(ops, "send_notification", lambda *a, **kw: calls.append(a) or False)
    ops._notify_failure_if_due(state_dir, state, datetime.now(UTC), "failure", "details")
    state["consecutive_failures"] = 2
    ops._notify_failure_if_due(state_dir, state, datetime.now(UTC), "failure", "details")
    assert len(calls) == 2


@pytest.mark.parametrize("partial", [False, True])
def test_repeated_failures_keep_only_one_quarantine(setup_update, monkeypatch, partial):
    state_dir, database = setup_update
    latest(monkeypatch, "new")
    fake_build(monkeypatch, database, ["smoke timeout"])
    if partial:
        def fail(*args):
            (args[1] / "partial.gz").write_bytes(b"partial")
            raise OSError("download interrupted")
        monkeypatch.setattr(ops, "_download_latest_jmdict", fail)
    before = ops.read_state(state_dir)
    for day in range(3):
        now = datetime(2026, 9, 6 + day, tzinfo=UTC)
        if partial:
            with pytest.raises(OSError, match="interrupted"):
                ops.update_lexicon(state_dir, now=now)
        else:
            assert ops.update_lexicon(state_dir, now=now).status == "quarantined"
        entries = list((state_dir / "quarantine").iterdir())
        assert len(entries) == 1
        assert entries[0].name.startswith(now.strftime("%Y%m%d"))
        assert not list((state_dir / "work").iterdir())
    assert ops.read_state(state_dir)["last_success_at"] == before["last_success_at"]
    assert (state_dir / "current").resolve() == database.parent


def test_prune_protects_links_baseline_and_unknown_directories(setup_update):
    state_dir, database = setup_update
    quarantine = state_dir / "quarantine"
    protected = quarantine / "20260901T000000Z-00000000"
    protected.mkdir()
    (state_dir / "previous").symlink_to(protected, target_is_directory=True)
    baseline = quarantine / "20260902T000000Z-00000000"
    baseline.mkdir()
    state = ops.read_state(state_dir)
    state["human_review_baseline"] = str(baseline)
    ops.write_state(state_dir, state)
    unknown = quarantine / "manual-backup"
    unknown.mkdir()
    symlink = quarantine / "20260903T000000Z-00000000"
    symlink.symlink_to(database.parent, target_is_directory=True)
    old = quarantine / "20260904T000000Z-00000000"
    old.mkdir()
    new = quarantine / "20260905T000000Z-00000000"
    new.mkdir()
    ops._prune_quarantine(state_dir)
    assert not old.exists()
    assert all(p.exists() for p in (new, protected, baseline, unknown, symlink, database))


def test_storage_shortage_stops_before_download_and_preserves_state(setup_update, monkeypatch):
    from types import SimpleNamespace
    state_dir, database = setup_update
    old = state_dir / "quarantine/20260901T000000Z-00000000"
    old.mkdir()
    monkeypatch.setattr(ops.shutil, "disk_usage", lambda p: SimpleNamespace(free=1))
    monkeypatch.setattr(ops, "_download_latest_jmdict", lambda *a: pytest.fail("downloaded"))
    with pytest.raises(ValueError, match="Insufficient update storage"):
        ops.update_lexicon(state_dir)
    state = ops.read_state(state_dir)
    assert state["last_success_at"] is None
    assert state["consecutive_failures"] == 1
    assert (state_dir / "current").resolve() == database.parent
    assert old.is_dir()  # Empty failed preflight must not evict useful evidence.
    assert not list((state_dir / "work").iterdir())


def test_account_quota_overrides_large_filesystem_free_space(setup_update, monkeypatch):
    from types import SimpleNamespace
    state_dir, _ = setup_update
    monkeypatch.setenv("WORDQUERY_STORAGE_QUOTA_BYTES", "12000000000")
    monkeypatch.setenv("WORDQUERY_STORAGE_USAGE_ROOT", str(state_dir.parent))
    monkeypatch.setattr(ops.shutil, "disk_usage", lambda p: SimpleNamespace(free=10 ** 12))
    monkeypatch.setattr(ops.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(stdout="11000000000\taccount\n"))
    with pytest.raises(ValueError, match="Insufficient update storage"):
        ops.check_update_storage(state_dir)
    monkeypatch.setattr(ops.subprocess, "run", lambda *a, **kw:
                        SimpleNamespace(stdout="6100000000\taccount\n"))
    assert ops.check_update_storage(state_dir)["available_bytes"] == 5900000000


def test_incomplete_quota_configuration_fails_closed(setup_update, monkeypatch):
    state_dir, _ = setup_update
    monkeypatch.setenv("WORDQUERY_STORAGE_QUOTA_BYTES", "12000000000")
    monkeypatch.delenv("WORDQUERY_STORAGE_USAGE_ROOT", raising=False)
    with pytest.raises(ValueError, match="Set both"):
        ops.check_update_storage(state_dir)


def test_dry_run_does_not_prune_existing_quarantines(setup_update, monkeypatch):
    state_dir, database = setup_update
    latest(monkeypatch, "new")
    fake_build(monkeypatch, database, ["smoke timeout"])
    for day in (1, 2):
        (state_dir / f"quarantine/2026090{day}T000000Z-00000000").mkdir()
    before = (state_dir / "state.json").read_bytes()
    ops.update_lexicon(state_dir, dry_run=True)
    assert len(list((state_dir / "quarantine").iterdir())) == 3
    assert (state_dir / "state.json").read_bytes() == before


def test_release_cleanup_preserves_review_baseline(setup_update):
    state_dir, _ = setup_update
    baseline = state_dir / "releases/baseline"
    baseline.mkdir()
    expired = state_dir / "releases/old"
    expired.mkdir()
    state = ops.read_state(state_dir)
    state["human_review_baseline"] = str(baseline)
    ops.write_state(state_dir, state)
    ops._prune_releases(state_dir)
    assert baseline.is_dir()
    assert not expired.exists()


def test_quota_measurement_failure_stops_update(setup_update, monkeypatch):
    state_dir, _ = setup_update
    monkeypatch.setenv("WORDQUERY_STORAGE_QUOTA_BYTES", "12000000000")
    monkeypatch.setenv("WORDQUERY_STORAGE_USAGE_ROOT", str(state_dir.parent))
    def fail(*a, **kw):
        raise ops.subprocess.TimeoutExpired("du", 60)
    monkeypatch.setattr(ops.subprocess, "run", fail)
    monkeypatch.setattr(ops, "_download_latest_jmdict", lambda *a: pytest.fail("downloaded"))
    with pytest.raises(ops.subprocess.TimeoutExpired):
        ops.update_lexicon(state_dir)
    assert ops.read_state(state_dir)["last_success_at"] is None
