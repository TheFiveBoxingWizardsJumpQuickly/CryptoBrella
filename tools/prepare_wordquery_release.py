"""Freeze an evaluated lexicon and its evidence without downloading or activating it."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_release(
    database: Path,
    sample: Path,
    judgment: Path,
    exploration: list[Path],
    output: Path,
) -> dict:
    from wordquery_jp.lexicon.candidate_audit import audit_auxiliary_candidates
    from wordquery_jp.lexicon.quality import evaluate_database

    for path in (database, sample, judgment, *exploration):
        if not path.is_file():
            raise ValueError(f"Missing input: {path}")
    if output.exists():
        raise ValueError(f"Output already exists; choose a new directory: {output}")
    output.mkdir(parents=True)
    # Copy first: all checks apply to the exact bytes handed to the operator.
    frozen_db = output / "lexicon.sqlite3"
    shutil.copyfile(database, frozen_db)
    evidence = output / "evidence"
    evidence.mkdir()
    frozen_sample = evidence / "formal-sample.tsv"
    frozen_judgment = evidence / "formal-human.completed.tsv"
    shutil.copyfile(sample, frozen_sample)
    shutil.copyfile(judgment, frozen_judgment)
    frozen_exploration = []
    for index, source in enumerate(exploration):
        destination = evidence / f"exploration-{index:02d}.tsv"
        shutil.copyfile(source, destination)
        frozen_exploration.append(destination)

    component = ROOT / "components/wordquery"
    quality = evaluate_database(
        frozen_db,
        accepted_gold=component / "data/gold/accepted.tsv",
        rejected_gold=component / "data/gold/rejected.tsv",
        formal_sample=frozen_sample,
        formal_judgment=frozen_judgment,
        exploration_samples=frozen_exploration,
    )
    audit = audit_auxiliary_candidates(frozen_db)
    write_json(output / "quality.json", quality.report)
    write_json(output / "candidate-audit.json", audit.report)
    gate = quality.report["formal_human_review"]
    write_json(output / "formal-human-gate.json", gate)
    if not (quality.passed and audit.passed and gate["active"] and gate["passed"]):
        raise ValueError(f"Release rejected; inspect reports in {output}")

    # A normal build/update manifest is intentionally not fabricated here:
    # human approval does not establish that JMdict is the latest download.
    with sqlite3.connect(f"{frozen_db.resolve().as_uri()}?mode=ro", uri=True) as connection:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    shutil.copytree(component / "data/manual", output / "manual")
    shutil.copytree(component / "data/gold", output / "gold")
    shutil.copyfile(component / "data/sources.toml", output / "sources.toml")
    shutil.copytree(ROOT / "app/static/wordquery/legal", output / "legal")
    shutil.copyfile(ROOT / "docs/public/wordquery/data_sources.md", output / "DATA_SOURCES.md")
    manifest = {
        "release_schema_version": 1,
        "release_id": output.name,
        "prepared_at": datetime.now(UTC).isoformat(),
        "release_state": "reviewed_not_activated",
        "database_input_hash": metadata["input_hash"],
        "database_sha256": sha256(frozen_db),
        "metadata": metadata,
        "counts": {key: quality.report["counts"][key] for key in ("accepted", "candidates")},
        "formal_human_review": {
            "passed": gate["passed"],
            "review": gate["review"],
            "one_sided_95_lower_bound": gate["one_sided_95_lower_bound"],
            "scope": "sampled accepted general vocabulary, excluding prior exploration",
        },
        "source_freshness": {
            "last_success_at": None,
            "note": "Not established by human review or database build time.",
        },
    }
    write_json(output / "manifest.json", manifest)
    files = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "SHA256SUMS").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(output).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from component_paths import activate_wordquery

    activate_wordquery()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--formal-sample", type=Path, required=True)
    parser.add_argument("--formal-judgment", type=Path, required=True)
    parser.add_argument("--exploration-sample", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = prepare_release(
            args.database, args.formal_sample, args.formal_judgment,
            args.exploration_sample, args.output,
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
