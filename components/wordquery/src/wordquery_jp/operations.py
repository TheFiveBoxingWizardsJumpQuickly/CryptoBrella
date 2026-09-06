"""PythonAnywhere-oriented, versioned lexicon release operations."""

from __future__ import annotations

import email.message
import fcntl
import hashlib
import json
import os
import shutil
import smtplib
import sqlite3
import tempfile
import tomllib
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

from .lexicon.builder import BuildConfig, build_database
from .lexicon.candidate_audit import audit_auxiliary_candidates
from .lexicon.fetch import fetch_source
from .lexicon.quality import compare_databases, evaluate_database
from .query import parse_search_request
from .repository import load_snapshot
from .search import SearchService

CHECK_INTERVAL = timedelta(days=21)
PUBLIC_FRESHNESS_LIMIT = timedelta(days=31)
MAX_ACCEPTED_COUNT_DELTA = 0.02
MAX_ACCEPTED_REMOVED = 0.005
MAX_ACCEPTED_TOUCHED = 0.05


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
) -> UpdateResult:
    """Check, build, validate, and atomically activate the latest JMdict."""

    root = (root or component_root()).resolve()
    state_dir = state_dir.resolve()
    now = (now or datetime.now(UTC)).astimezone(UTC)
    _prepare_state_directories(state_dir)
    lock_path = state_dir / "update.lock"
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read_state(state_dir)
        if not force and not update_due(state, now=now):
            return UpdateResult("not_due", detail="latest check is less than 21 days old")

        run_id = now.strftime("%Y%m%dT%H%M%SZ")
        work = state_dir / "work" / run_id
        work.mkdir(parents=True, exist_ok=False)
        try:
            candidate = _download_latest_jmdict(root, work)
            active_manifest = read_active_manifest(state_dir)
            active_jmdict_sha = (
                active_manifest.get("sources", {}).get("jmdict", {}).get("sha256")
            )
            if active_jmdict_sha == candidate.sha256:
                recovered = int(state.get("consecutive_failures", 0)) > 0
                state.update(
                    {
                        "last_checked_at": now.isoformat(),
                        "last_success_at": now.isoformat(),
                        "last_status": "already_current",
                        "consecutive_failures": 0,
                    }
                )
                write_state(state_dir, state)
                shutil.rmtree(work)
                if recovered:
                    send_notification(
                        "WordQuery JMdict update recovered",
                        "The active release is already the latest JMdict.",
                    )
                return UpdateResult("already_current", detail=candidate.sha256)

            result = _build_candidate(
                state_dir,
                root,
                work,
                candidate,
                run_id=run_id,
                now=now,
            )
            if result["failures"]:
                quarantine = state_dir / "quarantine" / run_id
                os.replace(work, quarantine)
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
            _set_link(state_dir / "current", release_dir)
            if old_target is not None:
                _set_link(state_dir / "previous", old_target)
            try:
                if reload_webapp:
                    reload_pythonanywhere_webapp()
            except Exception:
                if old_target is not None:
                    _set_link(state_dir / "current", old_target)
                    reload_pythonanywhere_webapp()
                raise
            recovered = int(state.get("consecutive_failures", 0)) > 0
            state.update(
                {
                    "last_checked_at": now.isoformat(),
                    "last_success_at": now.isoformat(),
                    "last_status": "activated",
                    "active_release": run_id,
                    "consecutive_failures": 0,
                }
            )
            write_state(state_dir, state)
            _prune_releases(state_dir)
            _prune_quarantine(state_dir)
            send_notification(
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
    raw = state.get("last_success_at") or state.get("last_checked_at")
    if not isinstance(raw, str):
        return True
    try:
        last = datetime.fromisoformat(raw).astimezone(UTC)
    except ValueError:
        return True
    return now - last >= CHECK_INTERVAL


def public_data_is_fresh(state: dict[str, Any], *, now: datetime | None = None) -> bool:
    raw = state.get("last_success_at")
    if not isinstance(raw, str):
        return False
    try:
        last = datetime.fromisoformat(raw).astimezone(UTC)
    except ValueError:
        return False
    return (now or datetime.now(UTC)).astimezone(UTC) - last <= PUBLIC_FRESHNESS_LIMIT


def read_state(state_dir: Path) -> dict[str, Any]:
    path = state_dir / "state.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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
    with sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True) as connection:
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


def status_report(state_dir: Path) -> dict[str, Any]:
    state = read_state(state_dir)
    return {
        **state,
        "state_dir": str(state_dir.resolve()),
        "current": str(_read_link_target(state_dir / "current") or ""),
        "fresh": public_data_is_fresh(state),
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
    sudachi = _prepare_sudachi(state_dir, source_manifest)
    database = work / "lexicon.sqlite3"
    result = build_database(
        BuildConfig(
            output=database,
            additions=root / "data/manual/additions.tsv",
            corrections=root / "data/manual/corrections.tsv",
            exclusions=root / "data/manual/exclusions.tsv",
            tags=root / "data/manual/tags.tsv",
            jmdict=jmdict.path,
            sudachi=sudachi,
            source_manifest=source_manifest,
        )
    )
    quality = evaluate_database(
        database,
        accepted_gold=root / "data/gold/accepted.tsv",
        rejected_gold=root / "data/gold/rejected.tsv",
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
    smoke = _run_smoke(database)
    failures.extend(smoke["failures"])
    manifest = {
        "release_id": run_id,
        "created_at": now.isoformat(),
        "component_version": "0.1.0",
        "input_hash": result.input_hash,
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
    service = SearchService(snapshot, timeout_seconds=1.5)
    cases = (
        {"version": 5, "mode": "pattern", "query": "ね?", "vocabulary_layers": ["core"]},
        {"version": 1, "mode": "anagram", "query": "ねこ"},
    )
    durations = []
    failures = []
    for payload in cases:
        try:
            response = service.execute(parse_search_request(payload, limit=10))
            durations.append(response.duration_ms)
            if response.duration_ms > 1500:
                failures.append(f"smoke_timeout:{payload['mode']}")
        except Exception as exc:
            failures.append(f"smoke:{payload['mode']}:{exc}")
    return {"durations_ms": durations, "failures": failures}


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
    stage = "first" if failures == 1 else ""
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
    if send_notification(f"{subject} [{stage}]", body):
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
    for release in (state_dir / "releases").iterdir():
        if release.is_dir() and release.resolve() not in keep:
            shutil.rmtree(release)


def _prune_quarantine(state_dir: Path) -> None:
    entries = sorted(
        (path for path in (state_dir / "quarantine").iterdir() if path.is_dir()),
        reverse=True,
    )
    for path in entries[1:]:
        shutil.rmtree(path)


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
