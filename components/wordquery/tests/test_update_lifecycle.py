import hashlib
import json
import shutil
import sqlite3
import subprocess
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
        for folder in ("manual", "gold"):
            shutil.copytree(root / "data" / folder, work / folder)
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


@pytest.fixture
def manual_update(setup_update, tmp_path, monkeypatch):
    state_dir, database = setup_update
    root = tmp_path / "component"
    for folder in ("data", "src"):
        shutil.copytree(ops.component_root() / folder, root / folder)
    additions = root / "data/manual/additions.tsv"
    with additions.open("a") as handle:
        handle.write("試験語\tしけんご\tgeneral\t名詞\t20\t確認\ttest\n")
    monkeypatch.setattr(ops, "_committed_revision", lambda root: "committed-revision")
    latest(monkeypatch, "old")
    fake_build(monkeypatch, database)
    return state_dir, database, root


def test_manual_update_bypasses_due_and_same_source_and_supports_schedule(manual_update):
    state_dir, _, root = manual_update
    state = ops.read_state(state_dir)
    state["last_success_at"] = datetime.now(UTC).isoformat()
    ops.write_state(state_dir, state)
    assert ops.update_lexicon(state_dir, root=root).status == "not_due"
    result = ops.update_lexicon(state_dir, root=root, apply_manual=True)
    assert result.status == "activated"
    after = ops.read_state(state_dir)
    assert after["approved_policy_sha256"] == ops.update_policy_fingerprint(root)
    assert after["previous_state"]["approved_policy_sha256"] == state["approved_policy_sha256"]
    assert after["human_review_baseline"] == state["human_review_baseline"]
    manifest = ops.read_active_manifest(state_dir)
    assert manifest["manual_update"]["git_revision"] == "committed-revision"
    manual_diff = json.loads((state_dir / "current/manual-diff.json").read_text())
    assert "manual/additions.tsv" in manual_diff
    # The next ordinary update accepts the new policy without a human gate.
    assert ops.update_lexicon(state_dir, root=root, force=True).status == "activated"
    # A subsequent manual update uses the latest data snapshot, not the initial review.
    assert ops.update_lexicon(state_dir, root=root, apply_manual=True).status == "activated"


def test_manual_rollback_restores_policy_and_revision(manual_update, monkeypatch):
    state_dir, database, root = manual_update
    before = ops.read_state(state_dir)
    before["last_success_at"] = datetime.now(UTC).isoformat()
    ops.write_state(state_dir, before)
    ops.update_lexicon(state_dir, root=root, apply_manual=True)
    ops.rollback_lexicon(state_dir, reload_webapp=False)
    restored = ops.read_state(state_dir)
    assert restored["approved_policy_sha256"] == before["approved_policy_sha256"]
    assert restored["last_success_at"] == before["last_success_at"]
    assert restored.get("manual_git_revision") == before.get("manual_git_revision")
    assert (state_dir / "current").resolve() == database.parent


def test_input_change_during_build_rejects_activation(manual_update, monkeypatch):
    state_dir, database, root = manual_update
    original_build = ops._build_candidate
    def build(*args, **kwargs):
        result = original_build(*args, **kwargs)
        with (root / "data/manual/additions.tsv").open("a") as handle:
            handle.write("変更\tへんこう\tgeneral\t名詞\t20\ttest\ttest\n")
        return result
    monkeypatch.setattr(ops, "_build_candidate", build)
    before = ops.read_state(state_dir)
    with pytest.raises(ValueError, match="inputs changed"):
        ops.update_lexicon(state_dir, root=root, apply_manual=True)
    assert ops.read_state(state_dir)["approved_policy_sha256"] == before["approved_policy_sha256"]
    assert (state_dir / "current").resolve() == database.parent


def test_manual_dry_run_retains_state_and_approval(manual_update):
    state_dir, database, root = manual_update
    before = (state_dir / "state.json").read_bytes()
    result = ops.update_lexicon(state_dir, root=root, apply_manual=True, dry_run=True)
    assert result.status == "validated"
    assert (state_dir / "state.json").read_bytes() == before
    assert (state_dir / "current").resolve() == database.parent
    manifest = json.loads((state_dir / "work" / result.release_id / "manifest.json").read_text())
    assert manifest["manual_update"]["data_sha256"] == ops.manual_data_fingerprint(root / "data")


def test_manual_mode_does_not_approve_build_rule_changes(manual_update):
    state_dir, _, root = manual_update
    with (root / "src/wordquery_jp/lexicon/builder.py").open("a") as handle:
        handle.write("\n# changed build policy\n")
    with pytest.raises(ValueError, match="Build policy changed"):
        ops.update_lexicon(state_dir, root=root, apply_manual=True, dry_run=True)


def test_manual_quarantine_does_not_approve_data(manual_update, monkeypatch):
    state_dir, database, root = manual_update
    before = ops.read_state(state_dir)
    fake_build(monkeypatch, database, ["excessive-diff"])
    assert ops.update_lexicon(state_dir, root=root, apply_manual=True).status == "quarantined"
    after = ops.read_state(state_dir)
    assert after["approved_policy_sha256"] == before["approved_policy_sha256"]
    assert after["last_success_at"] == before["last_success_at"]


def test_manual_reload_failure_restores_approval(manual_update, monkeypatch):
    state_dir, database, root = manual_update
    before = ops.read_state(state_dir)
    calls = []
    def reload():
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError("reload failed")
    monkeypatch.setattr(ops, "reload_pythonanywhere_webapp", reload)
    with pytest.raises(RuntimeError, match="reload failed"):
        ops.update_lexicon(state_dir, root=root, apply_manual=True)
    assert ops.read_state(state_dir)["approved_policy_sha256"] == before["approved_policy_sha256"]
    assert (state_dir / "current").resolve() == database.parent


def test_git_manual_update_rejects_dirty_and_untracked_inputs(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()
    git("init", "-q")
    for folder in ("manual", "gold"):
        (root / "data" / folder).mkdir(parents=True)
        (root / "data" / folder / "test.tsv").write_text("fixture\n")
    git("add", "data")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-qm", "fixture")
    assert ops._committed_revision(root) == git("rev-parse", "HEAD")
    extra = root / "data/manual/extra.tsv"
    extra.write_text("uncommitted\n")
    with pytest.raises(ValueError, match="Commit WordQuery"):
        ops._committed_revision(root)
    extra.unlink()
    (root / "data/manual/test.tsv").write_text("changed\n")
    git("add", "data")
    with pytest.raises(ValueError, match="Commit WordQuery"):
        ops._committed_revision(root)


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
    assert ops._database_metadata(database)["source.jmdict.sha256"] == source.sha256
    assert (work / "manual/additions.tsv").read_bytes() == (
        root / "data/manual/additions.tsv"
    ).read_bytes()
    assert (work / "diff.json").is_file()
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
