"""Release preparation must preserve reviewed bytes and reject failed evidence."""

import json
import sqlite3

import pytest
from wordquery_jp.lexicon.formal_review import write_formal_review_sample
from wordquery_jp.lexicon.review import JUDGMENT_FIELDS, write_judgment_template

from components.wordquery.tests.test_candidate_audit import (
    insert_proper_type,
    insert_provenance,
    insert_word,
)
from components.wordquery.tests.test_formal_review import (
    build_general_database,
    complete_human_judgment,
    read_rows,
    write_exploration_sample,
    write_rows,
)
from tools import prepare_wordquery_release as release


@pytest.fixture
def release_inputs(tmp_path, monkeypatch):
    database = tmp_path / "source.sqlite3"
    build_general_database(database, 310)
    with sqlite3.connect(database) as connection:
        insert_word(connection, word_id=1000, surface="東京", reading="とうきょう")
        insert_provenance(connection, 1000, "sudachidict", "fixture:1000")
        insert_proper_type(connection, 1000, "place", "地名")
    exploration = tmp_path / "exploration.tsv"
    write_exploration_sample(exploration)
    sample = tmp_path / "sample.tsv"
    write_formal_review_sample(database, sample, exploration_samples=[exploration], seed=11)
    judgment = tmp_path / "judgment.tsv"
    write_judgment_template(
        sample, judgment, reviewer="human-a", reviewer_kind="human",
        model_version="not-applicable", prompt_version="1.0",
    )
    rows = read_rows(judgment)
    for row in rows:
        complete_human_judgment(row)
    write_rows(judgment, JUDGMENT_FIELDS, rows)
    root = tmp_path / "repo"
    for directory in (
        "components/wordquery/data/manual", "components/wordquery/data/gold",
        "app/static/wordquery/legal", "docs/public/wordquery",
    ):
        (root / directory).mkdir(parents=True)
    (root / "components/wordquery/data/sources.toml").write_text("", encoding="utf-8")
    (root / "docs/public/wordquery/data_sources.md").write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(release, "ROOT", root)
    return database, sample, judgment, [exploration], tmp_path / "release"


def test_release_preserves_database_and_packages_self_contained_evidence(release_inputs):
    database, sample, judgment, exploration, output = release_inputs
    before = release.sha256(database)
    manifest = release.prepare_release(*release_inputs)
    assert release.sha256(database) == release.sha256(output / "lexicon.sqlite3") == before
    assert manifest["formal_human_review"]["passed"] is True
    assert manifest["source_freshness"]["last_success_at"] is None
    assert not (output.parent / "current").exists()
    for line in (output / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert release.sha256(output / name) == digest
    with pytest.raises(ValueError, match="already exists"):
        release.prepare_release(database, sample, judgment, exploration, output)


def test_release_rejects_one_invalid_judgment(release_inputs):
    judgment = release_inputs[2]
    rows = read_rows(judgment)
    complete_human_judgment(rows[0], valid=False)
    write_rows(judgment, JUDGMENT_FIELDS, rows)
    with pytest.raises(ValueError, match="Release rejected"):
        release.prepare_release(*release_inputs)
    output = release_inputs[-1]
    assert not (output / "manifest.json").exists()
    assert not (output / "SHA256SUMS").exists()
    gate = json.loads((output / "formal-human-gate.json").read_text())
    assert gate["review"]["invalid"] == 1


def test_release_rejects_changed_sample_membership(release_inputs):
    database = release_inputs[0]
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE words SET surface = surface || '変更' WHERE status='accepted'")
    with pytest.raises(ValueError):
        release.prepare_release(*release_inputs)
    assert not (release_inputs[-1] / "manifest.json").exists()
