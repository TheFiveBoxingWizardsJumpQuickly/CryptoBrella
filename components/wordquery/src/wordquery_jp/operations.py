"""PythonAnywhere-oriented, versioned lexicon release operations."""

from __future__ import annotations

import difflib
import email.message
import hashlib
import json
import logging
import os
import re
import shutil
import smtplib
import sqlite3
import subprocess
import tempfile
import time
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .lexicon.builder import BuildConfig, build_database
from .lexicon.candidate_audit import audit_auxiliary_candidates
from .lexicon.fetch import fetch_source
from .lexicon.quality import compare_databases, evaluate_database
from .query import SEARCH_REQUEST_VERSION, parse_search_request
from .repository import load_snapshot
from .search import SearchService
from .search_index import build_search_index, file_hash, index_path, validate_search_index
from .sqlite_paths import absolute_read_only_uri

CHECK_INTERVAL = timedelta(days=21)
PUBLIC_FRESHNESS_LIMIT = timedelta(days=31)
MAX_ACCEPTED_COUNT_DELTA = 0.02
MAX_ACCEPTED_REMOVED = 0.005
MAX_ACCEPTED_TOUCHED = 0.05
_RUN_ID = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}")


@dataclass(frozen=True, slots=True)
class UpdateResult:
    status: str
    release_id: str | None = None
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SourceDownload:
    path: Path
    sha256: str
    version: str


def component_root() -> Path:
    return Path(__file__).resolve().parents[2]


def update_lexicon(
    state_dir: Path,
    *,
    root: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
    reload_webapp: bool = True,
    now: datetime | None = None,
    apply_manual: bool = False,
) -> UpdateResult:
    """Check, build, validate, and atomically activate the latest JMdict."""

    # The web app also imports read-only release/status helpers from this module.
    # Only the Unix deployment updater needs flock; importing the app on Windows
    # must not require it. Fail before creating state or downloading anything.
    try:
        import fcntl
    except ImportError as exc:
        raise RuntimeError(
            "Automatic lexicon updates require Unix file locking. "
            "Run this command in WSL/Linux or on PythonAnywhere. "
            "The web app can run on Windows."
        ) from exc

    root = (root or component_root()).resolve()
    state_dir = state_dir.resolve()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    _prepare_state_directories(state_dir)
    lock_path = state_dir / "update.lock"
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read_state(state_dir)
        if not force and not apply_manual and not update_due(state, now=now):
            return UpdateResult("not_due", detail="latest check is less than 21 days old")

        run_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
        work = state_dir / "work" / run_id
        work.mkdir(parents=True, exist_ok=False)
        try:
            policy_hash = update_policy_fingerprint(root)
            revision = _manual_update_revision(root, state) if apply_manual else None
            if not apply_manual and state.get("approved_policy_sha256") != policy_hash:
                raise ValueError(
                    "Update policy is not approved; initialize from a reviewed release"
                )
            if not dry_run:
                _prune_quarantine(state_dir)
            storage = check_update_storage(state_dir)
            logging.getLogger(__name__).info(
                "Update storage: available=%s required=%s bytes",
                storage["available_bytes"], storage["required_bytes"],
            )
            logging.getLogger(__name__).info("Downloading latest JMdict: %s", run_id)
            candidate = _download_latest_jmdict(root, work)
            active_metadata = _database_metadata(state_dir / "current" / "lexicon.sqlite3")
            active_jmdict_sha = active_metadata.get("source.jmdict.sha256")
            if (not apply_manual and active_jmdict_sha == candidate.sha256
                    and validate_search_index(
                        state_dir / "current" / "lexicon.sqlite3") is not None):
                if dry_run:
                    return UpdateResult(
                        "validated", run_id, "Current source matches latest; state unchanged"
                    )
                active_input = _database_input_hash(state_dir / "current" / "lexicon.sqlite3")
                recovered = int(state.get("consecutive_failures", 0)) > 0
                state.update(
                    {
                        "last_checked_at": now.isoformat(),
                        "last_success_at": now.isoformat(),
                        "last_status": "already_current",
                        "consecutive_failures": 0,
                        "active_input_hash": active_input,
                        "last_failure_notification": None,
                        "last_failures": [],
                    }
                )
                write_state(state_dir, state)
                shutil.rmtree(work)
                if reload_webapp:
                    reload_pythonanywhere_webapp()
                if recovered:
                    _safe_notification(
                        "WordQuery JMdict update recovered",
                        "The active release is already the latest JMdict.",
                    )
                return UpdateResult("already_current", detail=candidate.sha256)

            logging.getLogger(__name__).info("Building and validating candidate: %s", run_id)
            result = _build_candidate(
                state_dir,
                root,
                work,
                candidate,
                run_id=run_id,
                now=now,
            )
            if update_policy_fingerprint(root) != policy_hash:
                raise ValueError("Update inputs changed during build; retry from a stable checkout")
            if apply_manual:
                if _manual_update_revision(root, state) != revision:
                    raise ValueError("Git revision changed during build")
                result["manifest"]["manual_git_revision"] = revision
                result["manifest"]["manual_update"] = {
                    "git_revision": revision,
                    "data_sha256": manual_data_fingerprint(root / "data"),
                    "previous_policy_sha256": state.get("approved_policy_sha256"),
                    "review_method": "operator-reviewed Git change and automated validation",
                }
                baseline = Path(state.get("manual_data_release") or state["human_review_baseline"])
                _write_json(work / "manual-diff.json", _manual_data_diff(baseline, root / "data"))
                _write_json(work / "manifest.json", result["manifest"])
            if result["failures"]:
                quarantine = state_dir / "quarantine" / run_id
                os.replace(work, quarantine)
                if not dry_run:
                    _prune_quarantine(state_dir)
                if dry_run:
                    return UpdateResult("quarantined", run_id, "; ".join(result["failures"]))
                _record_failure(state_dir, state, now, result["failures"])
                _notify_failure_if_due(
                    state_dir,
                    state,
                    now,
                    "WordQuery JMdict update quarantined",
                    "\n".join(result["failures"]),
                )
                return UpdateResult("quarantined", run_id, "; ".join(result["failures"]))

            if dry_run:
                result["manifest"]["dry_run"] = True
                _write_json(work / "manifest.json", result["manifest"])
                return UpdateResult("validated", run_id, str(work))

            release_dir = state_dir / "releases" / run_id
            os.replace(work, release_dir)
            old_target = _read_link_target(state_dir / "current")
            old_previous = _read_link_target(state_dir / "previous")
            old_state = dict(state)
            try:
                _set_link(state_dir / "current", release_dir)
                if old_target is not None:
                    _set_link(state_dir / "previous", old_target)
                state.update({
                    "last_checked_at": now.isoformat(), "last_success_at": now.isoformat(),
                    "last_status": "activated", "active_release": run_id,
                    "active_input_hash": result["manifest"]["input_hash"],
                    "consecutive_failures": 0, "last_failure_notification": None,
                    "last_failures": [],
                    "approved_policy_sha256": policy_hash,
                    "manual_data_release": str(release_dir),
                    "manual_git_revision": revision or state.get("manual_git_revision"),
                    "manual_data_sha256": manual_data_fingerprint(root / "data"),
                    "previous_state": {k: v for k, v in old_state.items() if k != "previous_state"},
                })
                write_state(state_dir, state)
                if reload_webapp:
                    reload_pythonanywhere_webapp()
            except Exception:
                state.clear()
                state.update(old_state)
                if old_target is not None:
                    _set_link(state_dir / "current", old_target)
                    if old_previous is not None:
                        _set_link(state_dir / "previous", old_previous)
                    else:
                        (state_dir / "previous").unlink(missing_ok=True)
                write_state(state_dir, state)
                if old_target is not None and reload_webapp:
                    reload_pythonanywhere_webapp()
                raise
            recovered = int(old_state.get("consecutive_failures", 0)) > 0
            _prune_releases(state_dir)
            _prune_quarantine(state_dir)
            _safe_notification(
                (
                    "WordQuery JMdict update recovered"
                    if recovered
                    else "WordQuery JMdict update succeeded"
                ),
                f"release={run_id}\nversion={candidate.version}\nsha256={candidate.sha256}",
                success=not recovered,
            )
            return UpdateResult("activated", run_id)
        except Exception as exc:
            # Preserve the newest failed build for diagnosis, including partial
            # downloads/builds. Never touch an already activated release here.
            if not dry_run and work.is_dir():
                try:
                    if any(work.iterdir()):
                        os.replace(work, state_dir / "quarantine" / run_id)
                        _prune_quarantine(state_dir)
                    else:
                        work.rmdir()
                except OSError:
                    logging.getLogger(__name__).exception("Could not retain failed update")
            if dry_run:
                raise
            _record_failure(state_dir, state, now, [f"{type(exc).__name__}: {exc}"])
            _notify_failure_if_due(
                state_dir,
                state,
                now,
                "WordQuery JMdict update failed",
                str(exc),
            )
            raise


def update_due(state: dict[str, Any], *, now: datetime) -> bool:
    if int(state.get("consecutive_failures", 0)) > 0:
        return True
    raw = state.get("last_success_at") or state.get("last_checked_at")
    if not isinstance(raw, str):
        return True
    try:
        last = datetime.fromisoformat(raw)
        if last.tzinfo is None:
            return True
        last = last.astimezone(UTC)
    except ValueError:
        return True
    return now < last or now - last >= CHECK_INTERVAL


def public_data_is_fresh(state: dict[str, Any], *, now: datetime | None = None) -> bool:
    raw = state.get("last_success_at")
    if not isinstance(raw, str):
        return False
    try:
        last = datetime.fromisoformat(raw)
        if last.tzinfo is None:
            return False
        last = last.astimezone(UTC)
    except ValueError:
        return False
    age = (now or datetime.now(UTC)).astimezone(UTC) - last
    return last.tzinfo is not None and timedelta(0) <= age <= PUBLIC_FRESHNESS_LIMIT


def read_state(state_dir: Path) -> dict[str, Any]:
    path = state_dir / "state.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def public_snapshot_is_fresh(state_dir: Path, input_hash: str | None) -> bool:
    state = read_state(state_dir)
    return bool(input_hash and state.get("active_input_hash") == input_hash
                and public_data_is_fresh(state))


def _database_metadata(database: Path) -> dict[str, str]:
    with sqlite3.connect(absolute_read_only_uri(database), uri=True) as connection:
        return dict(connection.execute("SELECT key, value FROM metadata"))


def _database_input_hash(database: Path) -> str:
    return _database_metadata(database)["input_hash"]


def update_policy_fingerprint(root: Path, *, data_root: Path | None = None) -> str:
    """Changes to sources other than JMdict, build policy or manual data require approval."""
    digest = hashlib.sha256()
    data_root = data_root or root / "data"
    paths = sorted([
        *(root / "src/wordquery_jp/lexicon").glob("*.py"),
        *(root / "data" / p.relative_to(data_root)
          for folder in ("manual", "gold") for p in (data_root / folder).glob("*.tsv")),
        root / "src/wordquery_jp/normalization.py", root / "src/wordquery_jp/units.py",
    ])
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        source = (data_root / path.relative_to(root / "data")
                  if path.is_relative_to(root / "data") else path)
        digest.update(source.read_bytes())
    with (root / "data/sources.toml").open("rb") as handle:
        sources = tomllib.load(handle)
    for key in ("sha256", "version"):
        sources.get("jmdict", {}).pop(key, None)
    digest.update(json.dumps(sources, sort_keys=True).encode())
    return digest.hexdigest()


def manual_data_fingerprint(data_root: Path) -> str:
    digest = hashlib.sha256()
    for folder in ("manual", "gold"):
        for path in sorted((data_root / folder).glob("*.tsv")):
            digest.update(path.relative_to(data_root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _manual_data_diff(before: Path, after: Path) -> dict[str, list[str]]:
    changes = {}
    for folder in ("manual", "gold"):
        names = {p.name for base in (before, after) for p in (base / folder).glob("*.tsv")}
        for name in sorted(names):
            old, new = before / folder / name, after / folder / name
            old_lines = old.read_text().splitlines() if old.is_file() else []
            new_lines = new.read_text().splitlines() if new.is_file() else []
            if old_lines != new_lines:
                changes[f"{folder}/{name}"] = list(difflib.unified_diff(
                    old_lines, new_lines, fromfile="approved", tofile="candidate", lineterm="",
                ))
    return changes


def _manual_update_revision(root: Path, state: dict[str, Any]) -> str:
    """Allow only committed data changes against the previously approved policy."""
    baseline = state.get("manual_data_release") or state.get("human_review_baseline")
    if not baseline:
        raise ValueError("No approved manual data baseline")
    baseline = Path(baseline)
    if any(not list((baseline / folder).glob("*.tsv")) for folder in ("manual", "gold")):
        raise ValueError("Approved manual data snapshot is missing")
    if update_policy_fingerprint(root, data_root=baseline) != state.get("approved_policy_sha256"):
        raise ValueError("Build policy changed; --apply-manual only approves manual/gold data")
    return _committed_revision(root)


def _committed_revision(root: Path) -> str:
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, stderr=subprocess.PIPE,
        ).strip()

    if git("status", "--porcelain", "--untracked-files=all", "--", "data", "src"):
        raise ValueError("Commit WordQuery data and source changes before --apply-manual")
    for folder in ("manual", "gold"):
        for path in (root / "data" / folder).glob("*.tsv"):
            git("ls-files", "--error-unmatch", "--", str(path.relative_to(root)))
    return git("rev-parse", "HEAD")


def initialize_updates(state_dir: Path, database: Path, *, root: Path | None = None) -> None:
    """Attach the reviewed baseline without claiming it is a current upstream version."""
    import fcntl
    root = (root or component_root()).resolve()
    state_dir, database = state_dir.resolve(), database.resolve()
    manifest = verify_reviewed_release(database)
    for folder in ("manual", "gold"):
        approved = {p.name: p.read_bytes() for p in (database.parent / folder).glob("*.tsv")}
        current = {p.name: p.read_bytes() for p in (root / "data" / folder).glob("*.tsv")}
        if not approved or approved != current:
            raise ValueError(f"Reviewed {folder} data do not match the update inputs")
    with (database.parent / "sources.toml").open("rb") as handle:
        approved_sources = tomllib.load(handle)
    with (root / "data/sources.toml").open("rb") as handle:
        current_sources = tomllib.load(handle)
    for sources in (approved_sources, current_sources):
        for key in ("sha256", "version"):
            sources.get("jmdict", {}).pop(key, None)
    if approved_sources != current_sources:
        raise ValueError("Reviewed source configuration does not match update inputs")
    policy_hash = update_policy_fingerprint(root)
    _prepare_state_directories(state_dir)
    with (state_dir / "update.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if ((state_dir / "current").exists() or (state_dir / "current").is_symlink()
                or (state_dir / "state.json").exists()):
            raise ValueError("Update state already initialized; existing state was not changed")
        _set_link(state_dir / "current", database.parent)
        write_state(state_dir, {
            "last_status": "initialized_unverified", "last_success_at": None,
            "active_input_hash": manifest["database_input_hash"],
            "approved_policy_sha256": policy_hash,
            "human_review_baseline": str(database.parent),
        })


def rollback_lexicon(state_dir: Path, *, reload_webapp: bool = True) -> None:
    """Restore the previous verified state, never extending its freshness deadline."""
    import fcntl
    state_dir = state_dir.resolve()
    with (state_dir / "update.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read_state(state_dir)
        previous_state = state.get("previous_state")
        previous = _read_link_target(state_dir / "previous")
        current = _read_link_target(state_dir / "current")
        if not isinstance(previous_state, dict) or previous is None or current is None:
            raise ValueError("No previous release and verification state available")
        if (not public_data_is_fresh(previous_state)
                or previous_state.get("active_input_hash")
                != _database_input_hash(previous / "lexicon.sqlite3")):
            raise ValueError("Previous release is expired or unverified; rollback refused")
        restored = {**previous_state, "last_status": "rolled_back",
                    "previous_state": {k: v for k, v in state.items() if k != "previous_state"}}
        try:
            _set_link(state_dir / "current", previous)
            write_state(state_dir, restored)
            if reload_webapp:
                reload_pythonanywhere_webapp()
        except Exception:
            _set_link(state_dir / "current", current)
            write_state(state_dir, state)
            if reload_webapp:
                reload_pythonanywhere_webapp()
            raise
        _set_link(state_dir / "previous", current)


def verify_reviewed_release(database: Path) -> dict[str, Any]:
    """Verify an operator-prepared reviewed release before serving its pinned DB."""
    manifest_path = database.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("release_schema_version") != 1:
        raise ValueError("Unsupported reviewed release manifest")
    gate = manifest.get("formal_human_review", {})
    if not isinstance(gate, dict) or gate.get("passed") is not True:
        raise ValueError("Reviewed release has no passing human gate")
    digest = manifest.get("database_sha256")
    with database.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != actual:
        raise ValueError("Reviewed database SHA-256 does not match the release manifest")
    with sqlite3.connect(absolute_read_only_uri(database), uri=True) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    if metadata.get("input_hash") != manifest.get("database_input_hash"):
        raise ValueError("Reviewed database input hash does not match the release manifest")
    return manifest


def write_state(state_dir: Path, state: dict[str, Any]) -> None:
    _write_json_atomic(state_dir / "state.json", state)


def read_active_manifest(state_dir: Path) -> dict[str, Any]:
    path = state_dir / "current" / "manifest.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_diff_policy(
    before: Path | None,
    after: Path,
    diff: dict[str, object],
) -> list[str]:
    if before is None or not before.is_file():
        return []
    old_count = _count_status(before, "accepted")
    new_count = _count_status(after, "accepted")
    if old_count == 0:
        return []
    added = sum(item["status"] == "accepted" for item in diff["added"])
    removed = sum(item["status"] == "accepted" for item in diff["removed"])
    changed = sum(
        item["before"]["status"] == "accepted" or item["after"]["status"] == "accepted"
        for item in diff["changed"]
    )
    failures = []
    if abs(new_count - old_count) / old_count > MAX_ACCEPTED_COUNT_DELTA:
        failures.append("accepted_count_delta_exceeds_2_percent")
    if removed / old_count > MAX_ACCEPTED_REMOVED:
        failures.append("accepted_removals_exceed_0.5_percent")
    if (added + removed + changed) / old_count > MAX_ACCEPTED_TOUCHED:
        failures.append("accepted_changes_exceed_5_percent")
    return failures


def reload_pythonanywhere_webapp() -> None:
    username = os.environ["PA_USERNAME"]
    domain = os.environ["PA_DOMAIN"]
    token = os.environ["API_TOKEN"]
    base = os.environ.get("PA_API_BASE", "https://www.pythonanywhere.com")
    url = f"{base.rstrip('/')}/api/v0/user/{username}/webapps/{domain}/reload/"
    request = urllib.request.Request(
        url,
        method="POST",
        headers={"Authorization": f"Token {token}", "User-Agent": "wordquery-jp/0.1"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"PythonAnywhere reload failed: HTTP {response.status}")


def send_notification(subject: str, body: str, *, success: bool = False) -> bool:
    if success and os.environ.get("WORDQUERY_NOTIFY_SUCCESS", "0") != "1":
        return False
    required = ("WORDQUERY_SMTP_HOST", "WORDQUERY_SMTP_FROM", "WORDQUERY_SMTP_TO")
    if any(not os.environ.get(name) for name in required):
        return False
    message = email.message.EmailMessage()
    message["Subject"] = subject
    message["From"] = os.environ["WORDQUERY_SMTP_FROM"]
    message["To"] = os.environ["WORDQUERY_SMTP_TO"]
    message.set_content(body)
    host = os.environ["WORDQUERY_SMTP_HOST"]
    port = int(os.environ.get("WORDQUERY_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        username = os.environ.get("WORDQUERY_SMTP_USERNAME")
        password = os.environ.get("WORDQUERY_SMTP_PASSWORD")
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
    return True


def _safe_notification(subject: str, body: str, *, success: bool = False) -> bool:
    try:
        return send_notification(subject, body, success=success)
    except Exception as exc:
        logging.getLogger(__name__).error("WordQuery notification failed (%s)", type(exc).__name__)
        return False


def status_report(state_dir: Path) -> dict[str, Any]:
    state = read_state(state_dir)
    try:
        input_hash = _database_input_hash(state_dir / "current" / "lexicon.sqlite3")
    except (OSError, sqlite3.Error, KeyError):
        input_hash = None
    return {
        **state,
        "state_dir": str(state_dir.resolve()),
        "current": str(_read_link_target(state_dir / "current") or ""),
        "fresh": public_snapshot_is_fresh(state_dir, input_hash),
        "freshness_timestamp_valid": public_data_is_fresh(state),
        "notification_configured": all(
            os.environ.get(name)
            for name in ("WORDQUERY_SMTP_HOST", "WORDQUERY_SMTP_FROM", "WORDQUERY_SMTP_TO")
        ),
    }


def _build_candidate(
    state_dir: Path,
    root: Path,
    work: Path,
    jmdict: SourceDownload,
    *,
    run_id: str,
    now: datetime,
) -> dict[str, Any]:
    source_manifest = _candidate_source_manifest(root, work, jmdict)
    for folder in ("manual", "gold"):
        shutil.copytree(root / "data" / folder, work / folder)
    sudachi = _prepare_sudachi(state_dir, source_manifest)
    database = work / "lexicon.sqlite3"
    result = build_database(
        BuildConfig(
            output=database,
            additions=work / "manual/additions.tsv",
            corrections=work / "manual/corrections.tsv",
            exclusions=work / "manual/exclusions.tsv",
            tags=work / "manual/tags.tsv",
            jmdict=jmdict.path,
            sudachi=sudachi,
            source_manifest=source_manifest,
        )
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO metadata VALUES ('source.jmdict.sha256', ?)",
            (jmdict.sha256,),
        )
    quality = evaluate_database(
        database,
        accepted_gold=work / "gold/accepted.tsv",
        rejected_gold=work / "gold/rejected.tsv",
    )
    audit = audit_auxiliary_candidates(database)
    active_database = state_dir / "current" / "lexicon.sqlite3"
    before = active_database if active_database.is_file() else None
    diff = (
        compare_databases(before, database)
        if before
        else {"added": [], "removed": [], "changed": []}
    )
    failures = list(quality.report["failures"])
    if not audit.passed:
        failures.extend(f"candidate_audit:{item}" for item in audit.report["failures"])
    failures.extend(evaluate_diff_policy(before, database, diff))
    _write_json(work / "diff.json", diff)
    build_search_index(database)
    smoke = _run_smoke(database)
    failures.extend(smoke["failures"])
    with database.open("rb") as handle:
        database_sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
    manifest = {
        "release_id": run_id,
        "created_at": now.isoformat(),
        "component_version": "0.1.0",
        "input_hash": result.input_hash,
        "database_sha256": database_sha256,
        "search_index": {"filename": index_path(database).name,
                         "sha256": file_hash(index_path(database)),
                         "bytes": index_path(database).stat().st_size},
        "approved_policy_sha256": update_policy_fingerprint(root),
        "manual_data_sha256": manual_data_fingerprint(work),
        "manual_git_revision": read_state(state_dir).get("manual_git_revision"),
        "human_review_baseline": read_state(state_dir).get("human_review_baseline"),
        "counts": {"accepted": result.accepted, "candidates": result.candidates},
        "sources": {
            "jmdict": {"version": jmdict.version, "sha256": jmdict.sha256},
        },
        "quality": quality.report,
        "candidate_audit": audit.report,
        "diff": {
            "added": len(diff["added"]),
            "removed": len(diff["removed"]),
            "changed": len(diff["changed"]),
        },
        "smoke": smoke,
        "failures": failures,
    }
    _write_json(work / "manifest.json", manifest)
    _write_json(work / "quality-report.json", quality.report)
    return {"failures": failures, "manifest": manifest}


def _run_smoke(database: Path) -> dict[str, Any]:
    snapshot = load_snapshot(database)
    service = SearchService(snapshot, timeout_seconds=5, regex_timeout_seconds=0.05)
    cases = [
        {"version": SEARCH_REQUEST_VERSION, "mode": mode, "query": query,
         "vocabulary_layers": ["core", "auxiliary"], "include_proper": True}
        for mode, query in [("pattern", "とう*"), ("pattern", "?ねこ"),
                            ("pattern", "*ねこ"), ("pattern", "???"),
                            ("regex", "^とう.*$"), ("regex", "ねこ$"),
                            ("regex", "(とう|ねこ)$"), ("anagram", "ねこ")]
    ]
    durations = []
    failures = []
    results = []
    for payload in cases:
        started, cpu_started = time.monotonic(), time.process_time()
        result = {"mode": payload["mode"], "query": payload["query"]}
        try:
            response = service.execute(parse_search_request(payload, max_length=200, limit=3000))
            durations.append(response.duration_ms)
            result.update(status="completed", total=response.total)
            if response.duration_ms > 5000:
                failures.append(f"smoke_timeout:{payload['mode']}")
        except Exception as exc:
            failures.append(f"smoke:{payload['mode']}:{payload['query']}:{exc}")
            result.update(status="failed", error=str(exc))
        result.update(wall_ms=(time.monotonic() - started) * 1000,
                      cpu_ms=(time.process_time() - cpu_started) * 1000)
        results.append(result)
    return {"durations_ms": durations, "failures": failures, "cases": results}


def _download_latest_jmdict(root: Path, work: Path) -> SourceDownload:
    with (root / "data/sources.toml").open("rb") as handle:
        config = tomllib.load(handle)["jmdict"]
    target = work / "JMdict_e.gz"
    request = urllib.request.Request(config["url"], headers={"User-Agent": "wordquery-jp/0.1"})
    digest = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as output:
        modified = response.headers.get("Last-Modified")
        while block := response.read(1024 * 1024):
            digest.update(block)
            output.write(block)
    version = datetime.now(UTC).date().isoformat()
    if modified:
        version = parsedate_to_datetime(modified).date().isoformat()
    return SourceDownload(target, digest.hexdigest(), version)


def _candidate_source_manifest(root: Path, work: Path, jmdict: SourceDownload) -> Path:
    with (root / "data/sources.toml").open("rb") as handle:
        sources = tomllib.load(handle)
    sources["jmdict"]["version"] = jmdict.version
    sources["jmdict"]["sha256"] = jmdict.sha256
    path = work / "sources.toml"
    lines = []
    for name, values in sources.items():
        lines.append(f"[{name}]")
        for key, value in values.items():
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _prepare_sudachi(state_dir: Path, manifest: Path) -> Path:
    raw = state_dir / "sources"
    extracted = raw / "sudachidict"
    small = extracted / "small_lex.csv"
    core = extracted / "core_lex.csv"
    if small.is_file() and core.is_file():
        return extracted
    extracted.mkdir(parents=True, exist_ok=True)
    for name in ("sudachidict_small", "sudachidict_core"):
        result = fetch_source(name, manifest=manifest, destination=raw)
        with zipfile.ZipFile(result.path) as archive:
            member = "small_lex.csv" if name.endswith("small") else "core_lex.csv"
            with archive.open(member) as source, (extracted / member).open("wb") as target:
                shutil.copyfileobj(source, target)
    return extracted


def _prepare_state_directories(state_dir: Path) -> None:
    for name in ("releases", "work", "sources", "quarantine"):
        (state_dir / name).mkdir(parents=True, exist_ok=True)


def _record_failure(
    state_dir: Path,
    state: dict[str, Any],
    now: datetime,
    failures: list[str],
) -> None:
    state.update(
        {
            "last_checked_at": now.isoformat(),
            "last_status": "failed",
            "last_failures": failures,
            "consecutive_failures": int(state.get("consecutive_failures", 0)) + 1,
        }
    )
    write_state(state_dir, state)


def _notify_failure_if_due(
    state_dir: Path,
    state: dict[str, Any],
    now: datetime,
    subject: str,
    body: str,
) -> None:
    failures = int(state.get("consecutive_failures", 0))
    stage = "first" if failures and not state.get("last_failure_notification") else ""
    raw_success = state.get("last_success_at")
    if isinstance(raw_success, str):
        try:
            age = now - datetime.fromisoformat(raw_success).astimezone(UTC)
            if age >= PUBLIC_FRESHNESS_LIMIT:
                stage = "31-days"
            elif age >= timedelta(days=28):
                stage = "28-days"
        except ValueError:
            pass
    if not stage or state.get("last_failure_notification") == stage:
        return
    if _safe_notification(f"{subject} [{stage}]", body):
        state["last_failure_notification"] = stage
        write_state(state_dir, state)


def _count_status(database: Path, status: str) -> int:
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM words WHERE status = ?", (status,)
        ).fetchone()
        return int(row[0])


def _read_link_target(path: Path) -> Path | None:
    if not path.is_symlink():
        return None
    target = Path(os.readlink(path))
    return target if target.is_absolute() else (path.parent / target).resolve()


def _set_link(link: Path, target: Path) -> None:
    temporary = link.with_name(f".{link.name}.tmp")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    os.replace(temporary, link)


def _prune_releases(state_dir: Path) -> None:
    keep = {
        target.resolve()
        for name in ("current", "previous")
        if (target := _read_link_target(state_dir / name)) is not None
    }
    if baseline := read_state(state_dir).get("human_review_baseline"):
        keep.add(Path(baseline).resolve())
    for release in (state_dir / "releases").iterdir():
        if (not release.is_symlink() and release.is_dir()
                and not any(release.resolve() == item or release.resolve() in item.parents
                            for item in keep)):
            shutil.rmtree(release)


def _prune_quarantine(state_dir: Path) -> None:
    state = read_state(state_dir)
    protected = {
        target.resolve() for name in ("current", "previous")
        if (target := _read_link_target(state_dir / name)) is not None
    }
    if baseline := state.get("human_review_baseline"):
        protected.add(Path(baseline).resolve())
    entries = sorted(
        (path for path in (state_dir / "quarantine").iterdir()
         if _RUN_ID.fullmatch(path.name) and not path.is_symlink() and path.is_dir()
         and not any(path.resolve() == item or path.resolve() in item.parents
                     for item in protected)),
        reverse=True,
    )
    for path in entries[1:]:
        shutil.rmtree(path)
        logging.getLogger(__name__).info("Removed old quarantined update: %s", path.name)


def check_update_storage(state_dir: Path) -> dict[str, int | None]:
    """Read-only conservative preflight; filesystem free space is not a user quota."""
    database = state_dir / "current" / "lexicon.sqlite3"
    size = sum(path.stat().st_size for path in (database, index_path(database))
               if path.is_file())
    required = max(2 * 1024 ** 3, 2 * size + 512 * 1024 ** 2)
    available = shutil.disk_usage(state_dir).free
    quota = os.environ.get("WORDQUERY_STORAGE_QUOTA_BYTES")
    usage_root = os.environ.get("WORDQUERY_STORAGE_USAGE_ROOT")
    used = None
    if bool(quota) != bool(usage_root):
        raise ValueError("Set both WORDQUERY_STORAGE_QUOTA_BYTES and WORDQUERY_STORAGE_USAGE_ROOT")
    if quota and usage_root:
        quota_bytes = int(quota)
        account = Path(usage_root)
        if quota_bytes <= 0 or not account.is_absolute() or not account.is_dir():
            raise ValueError("Invalid storage quota or absolute account directory")
        if not state_dir.resolve().is_relative_to(account.resolve()):
            raise ValueError("Storage usage directory must contain the state directory")
        # GNU du counts allocated blocks, includes dotfiles, and deduplicates hard
        # links without following symlinks. Fail closed if measurement fails.
        result = subprocess.run(
            ["du", "-s", "-B1", "--", str(account)], check=True,
            capture_output=True, text=True, timeout=60,
        )
        used = int(result.stdout.split()[0])
        available = min(available, max(0, quota_bytes - used))
    else:
        logging.getLogger(__name__).warning(
            "Account quota is not configured; checking filesystem free space only"
        )
    if available < required:
        raise ValueError(
            f"Insufficient update storage: available={available} required={required} bytes"
        )
    return {"available_bytes": available, "required_bytes": required, "account_used_bytes": used}


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
