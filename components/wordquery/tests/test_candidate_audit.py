import sqlite3

from wordquery_jp.lexicon.candidate_audit import (
    audit_auxiliary_candidates,
    write_candidate_audit_report,
)
from wordquery_jp.lexicon.schema import SCHEMA
from wordquery_jp.normalization import anagram_signature


def insert_word(
    connection,
    *,
    word_id,
    surface,
    reading,
    category="proper",
    pos="名詞, 固有名詞, 地名, 一般",
    status="candidate",
):
    connection.execute(
        """
        INSERT INTO words(
            id, surface, reading, normalized_reading, signature,
            category, pos, priority, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 10, ?)
        """,
        (
            word_id,
            surface,
            reading,
            reading,
            anagram_signature(reading),
            category,
            pos,
            status,
        ),
    )


def insert_provenance(connection, word_id, source, entry_id):
    connection.execute(
        """
        INSERT INTO provenance(word_id, source, source_entry_id, reason, reference)
        VALUES (?, ?, ?, '', '')
        """,
        (word_id, source, entry_id),
    )


def insert_proper_type(connection, word_id, value, evidence):
    connection.execute(
        """
        INSERT INTO word_tags(
            word_id, axis, value, source, source_entry_id, evidence, reason, reference
        ) VALUES (?, 'proper_type', ?, 'sudachidict', ?, ?, '', '')
        """,
        (word_id, value, f"sudachi:{word_id}", evidence),
    )


def build_database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO metadata VALUES ('input_hash', 'audit-test-hash')")
        connection.execute("INSERT INTO metadata VALUES ('schema_version', '2')")


def test_candidate_audit_reports_completeness_classification_and_adoption_unit(
    tmp_path,
):
    database = tmp_path / "lexicon.sqlite3"
    build_database(database)
    with sqlite3.connect(database) as connection:
        insert_word(
            connection,
            word_id=1,
            surface="東京",
            reading="とうきょう",
        )
        insert_provenance(connection, 1, "sudachidict", "sudachi:1")
        insert_proper_type(connection, 1, "place", "地名")
        insert_proper_type(connection, 1, "other", "固有名詞")

        insert_word(
            connection,
            word_id=2,
            surface="試験名",
            reading="しけんめい",
            pos="名詞, 固有名詞, 一般",
        )
        insert_provenance(connection, 2, "sudachidict", "sudachi:2a")
        insert_provenance(connection, 2, "sudachidict", "sudachi:2b")
        insert_proper_type(connection, 2, "other", "固有名詞")

        insert_word(
            connection,
            word_id=3,
            surface="一般語",
            reading="いっぱんご",
            category="general",
            pos="名詞, 普通名詞, 一般",
            status="accepted",
        )
        insert_provenance(connection, 3, "sudachidict", "sudachi:3")

        insert_word(
            connection,
            word_id=4,
            surface="polling",
            reading="ぽーりんぐ",
            category="general",
            pos="名詞, 普通名詞, 一般",
        )
        insert_provenance(connection, 4, "sudachidict", "sudachi:4")

    result = audit_auxiliary_candidates(database)

    assert result.passed is True
    assert result.report["failures"] == []
    assert result.report["counts"]["candidate_records"] == 3
    assert result.report["counts"]["source_entries"] == 4
    assert result.report["counts"]["records_with_multiple_source_entries"] == 1
    assert result.report["counts"]["candidate_kinds"] == {
        "proper": 2,
        "ascii_only_headword": 1,
        "overlap": 0,
    }
    assert result.report["classification"]["proper_type_records"] == {
        "other": 2,
        "place": 1,
    }
    assert result.report["classification"]["specifically_classified_records"] == 1
    assert result.report["classification"]["only_other_records"] == 1
    assert result.report["classification"]["multiple_proper_types"] == 1
    assert result.report["classification"]["specific_coverage"] == 0.5
    assert result.report["adoption_unit"]["key"] == [
        "surface",
        "normalized_reading",
    ]
    assert result.report["adoption_unit"]["search_layer"] == "auxiliary"

    output = tmp_path / "audit.json"
    write_candidate_audit_report(result, output)
    assert output.read_text(encoding="utf-8").endswith("\n")


def test_candidate_audit_fails_on_scope_and_completeness_drift(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_database(database)
    with sqlite3.connect(database) as connection:
        insert_word(
            connection,
            word_id=1,
            surface="不正候補",
            reading="漢字",
            category="general",
            pos="",
        )
        insert_provenance(connection, 1, "jmdict", "jmdict:1")

    result = audit_auxiliary_candidates(database)

    assert result.passed is False
    assert set(result.report["failures"]) == {
        "candidate_out_of_scope:1",
        "candidate_without_sudachi_provenance:1",
        "candidate_with_non_sudachi_provenance:1",
        "invalid_readings:1",
        "missing_pos:1",
    }


def test_candidate_audit_requires_type_evidence_for_proper_candidates(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_database(database)
    with sqlite3.connect(database) as connection:
        insert_word(
            connection,
            word_id=1,
            surface="未分類名",
            reading="みぶんるいめい",
        )
        insert_provenance(connection, 1, "sudachidict", "sudachi:1")

    result = audit_auxiliary_candidates(database)

    assert result.passed is False
    assert result.report["failures"] == ["missing_proper_type:1"]
