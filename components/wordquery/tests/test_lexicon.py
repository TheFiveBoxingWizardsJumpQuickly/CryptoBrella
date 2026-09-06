import csv
import sqlite3
from pathlib import Path

import pytest

from wordquery_jp.lexicon.builder import BuildConfig, build_database
from wordquery_jp.lexicon.importers import (
    _decode_sudachi_field,
    classify_pos,
    iter_jmdict,
    iter_sudachi_csv,
)
from wordquery_jp.lexicon.quality import compare_databases, evaluate_database
from wordquery_jp.repository import LexiconUnavailable, load_snapshot

COMPONENT_ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def write_tsv(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def test_jmdict_importer_reads_categories_and_priority():
    words = list(iter_jmdict(FIXTURES / "jmdict.xml"))
    assert {(word.surface, word.reading) for word in words} >= {
        ("犬", "いぬ"),
        ("大阪", "おおさか"),
    }
    dog = next(word for word in words if word.surface == "犬")
    assert dog.priority == 90
    assert {(tag.axis, tag.value, tag.evidence) for tag in dog.tags} == {
        ("domain", "zoology", "zoology")
    }
    assert next(word for word in words if word.surface == "大阪").category == "proper"
    sawamular = next(word for word in words if word.surface == "サワムラー")
    assert sawamular.category == "proper"
    assert {(tag.axis, tag.value) for tag in sawamular.tags} == {("proper_type", "character")}
    assert next(word for word in words if word.surface == "へ").category == "function"
    assert any(word.surface == "かな" and word.reading == "かな" for word in words)
    assert not any(word.surface == "仮名" and word.reading == "かな" for word in words)


def test_jmdict_importer_applies_reading_and_sense_restrictions():
    words = list(iter_jmdict(FIXTURES / "jmdict.xml"))
    pairs_and_fields = {
        (word.surface, word.reading, tag.value)
        for word in words
        for tag in word.tags
        if tag.axis == "domain"
    }
    assert ("甲", "こう", "restricted") in pairs_and_fields
    assert ("乙", "こう", "inherited-pos") in pairs_and_fields
    assert ("乙", "おつ", "inherited-pos") in pairs_and_fields
    assert ("乙", "こう", "restricted") not in pairs_and_fields
    assert ("甲", "こう", "inherited-pos") not in pairs_and_fields
    assert not any(word.surface == "甲" and word.reading == "おつ" for word in words)
    inherited = next(
        word
        for word in words
        if word.surface == "乙"
        and word.reading == "こう"
        and word.source_entry_id.startswith("1007:sense-1:")
    )
    assert inherited.pos == "noun (common) (futsuumeishi)"


def test_sudachi_header_importer_uses_dictionary_forms():
    words = list(iter_sudachi_csv(FIXTURES / "sudachi.csv"))
    assert [(word.surface, word.reading) for word in words][:2] == [
        ("苺", "イチゴ"),
        ("京都", "キョウト"),
    ]
    assert words[1].category == "proper"


def test_sudachi_v1_raw_importer_uses_real_column_layout_and_skips_symbols():
    words = list(iter_sudachi_csv(FIXTURES / "sudachi_raw.csv"))
    assert [(word.surface, word.reading) for word in words] == [
        ("1000本", "センボン"),
        ("(n)ine", "ナイン"),
        ("a/m", "アンペアマイメートル"),
        ("東京", "トウキョウ"),
    ]
    assert words[3].category == "proper"


def test_sudachi_unicode_decoder_handles_pairs_and_rejects_isolated_surrogates():
    assert _decode_sudachi_field(r"顔\uD83D\uDE00") == "顔😀"
    with pytest.raises(ValueError, match="孤立サロゲート"):
        _decode_sudachi_field(r"壊れた\uD83D")


def test_pos_classification_does_not_mistake_descriptive_particle_text_for_function_word():
    assert (
        classify_pos(
            [
                "noun (common) (futsuumeishi)",
                "nouns which may take the genitive case particle 'no'",
            ]
        )
        == "general"
    )
    assert classify_pos(["particle"]) == "function"
    assert classify_pos(["particle", "noun (common) (futsuumeishi)"]) == "general"
    assert classify_pos(["noun (common) (futsuumeishi)", "character"]) == "proper"


def test_build_merge_exclusion_correction_and_quality(tmp_path):
    additions = tmp_path / "additions.tsv"
    corrections = tmp_path / "corrections.tsv"
    exclusions = tmp_path / "exclusions.tsv"
    accepted = tmp_path / "accepted.tsv"
    rejected = tmp_path / "rejected.tsv"
    database = tmp_path / "lexicon.sqlite3"
    write_tsv(
        additions,
        ["surface", "reading", "category", "pos", "priority", "reason", "reference"],
        [
            {
                "surface": "猫",
                "reading": "ネコ",
                "category": "general",
                "pos": "名詞",
                "priority": "50",
                "reason": "test",
                "reference": "test",
            },
            {
                "surface": "除外",
                "reading": "じょがい",
                "category": "general",
                "pos": "名詞",
                "priority": "1",
                "reason": "test",
                "reference": "test",
            },
        ],
    )
    write_tsv(
        corrections,
        [
            "source",
            "source_entry_id",
            "surface",
            "reading",
            "new_surface",
            "new_reading",
            "new_category",
            "new_pos",
            "new_priority",
            "reason",
            "reference",
        ],
        [
            {
                "source": "manual",
                "source_entry_id": "additions:2",
                "new_surface": "ねこ",
                "new_priority": "80",
                "reason": "fix",
                "reference": "test",
            }
        ],
    )
    write_tsv(
        exclusions,
        ["source", "source_entry_id", "surface", "reading", "reason", "reference"],
        [{"surface": "除外", "reading": "じょがい", "reason": "test", "reference": "test"}],
    )
    write_tsv(
        accepted,
        ["surface", "reading", "category"],
        [{"surface": "ねこ", "reading": "ねこ", "category": "general"}],
    )
    write_tsv(
        rejected,
        ["surface", "reading", "reason"],
        [{"surface": "除外", "reading": "じょがい", "reason": "test"}],
    )

    result = build_database(
        BuildConfig(
            output=database,
            additions=additions,
            corrections=corrections,
            exclusions=exclusions,
            source_manifest=tmp_path / "none.toml",
        )
    )
    assert result.accepted == 1
    snapshot = load_snapshot(database)
    assert snapshot.records[0].surface == "ねこ"
    assert snapshot.records[0].normalized_reading == "ねこ"
    assert snapshot.records[0].priority == 80
    assert evaluate_database(database, accepted_gold=accepted, rejected_gold=rejected).passed


def test_database_diff_reports_additions(tmp_path):
    first = tmp_path / "first.sqlite3"
    second = tmp_path / "second.sqlite3"
    empty = tmp_path / "empty.tsv"
    write_tsv(
        empty, ["surface", "reading", "category", "pos", "priority", "reason", "reference"], []
    )
    exclusions = tmp_path / "exclusions.tsv"
    corrections = tmp_path / "corrections.tsv"
    write_tsv(
        exclusions, ["source", "source_entry_id", "surface", "reading", "reason", "reference"], []
    )
    write_tsv(
        corrections,
        [
            "source",
            "source_entry_id",
            "surface",
            "reading",
            "new_surface",
            "new_reading",
            "new_category",
            "new_pos",
            "new_priority",
            "reason",
            "reference",
        ],
        [],
    )
    build_database(
        BuildConfig(first, empty, corrections, exclusions, source_manifest=tmp_path / "none")
    )
    with empty.open("a", encoding="utf-8") as handle:
        handle.write("猫\tねこ\tgeneral\t名詞\t1\ttest\ttest\n")
    build_database(
        BuildConfig(second, empty, corrections, exclusions, source_manifest=tmp_path / "none")
    )
    assert len(compare_databases(first, second)["added"]) == 1
    with sqlite3.connect(second) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_manual_category_and_priority_override_external_record(tmp_path):
    additions = tmp_path / "additions.tsv"
    write_tsv(
        additions,
        ["surface", "reading", "category", "pos", "priority", "reason", "reference"],
        [
            {
                "surface": "大阪",
                "reading": "おおさか",
                "category": "general",
                "pos": "開発者分類",
                "priority": "55",
                "reason": "override test",
                "reference": "test",
            }
        ],
    )
    database = tmp_path / "override.sqlite3"
    build_database(
        BuildConfig(output=database, additions=additions, jmdict=FIXTURES / "jmdict.xml")
    )
    snapshot = load_snapshot(database)
    osaka = next(record for record in snapshot.records if record.surface == "大阪")
    assert osaka.category == "general"
    assert osaka.priority == 55
    assert osaka.multiple_sources is True


def test_manual_tags_are_attached_with_required_evidence(tmp_path):
    additions = tmp_path / "additions.tsv"
    tags = tmp_path / "tags.tsv"
    write_tsv(
        additions,
        ["surface", "reading", "category", "pos", "priority", "reason", "reference"],
        [
            {
                "surface": "猫",
                "reading": "ねこ",
                "category": "general",
                "pos": "名詞",
                "priority": "50",
                "reason": "test word",
                "reference": "internal-fixture",
            }
        ],
    )
    write_tsv(
        tags,
        ["surface", "reading", "axis", "value", "evidence", "reason", "reference"],
        [
            {
                "surface": "猫",
                "reading": "ネコ",
                "axis": "suitability",
                "value": "crossword",
                "evidence": "human review",
                "reason": "test tag",
                "reference": "internal-fixture",
            },
            {
                "surface": "猫",
                "reading": "ねこ",
                "axis": "usage",
                "value": "test",
                "evidence": "",
                "reason": "",
                "reference": "",
            },
        ],
    )
    database = tmp_path / "manual-tags.sqlite3"
    result = build_database(
        BuildConfig(
            output=database,
            additions=additions,
            tags=tags,
            source_manifest=tmp_path / "none.toml",
        )
    )

    assert result.issues == 1
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            """
            SELECT t.axis, t.value, t.source, t.source_entry_id, t.evidence,
                   t.reason, t.reference
            FROM word_tags t JOIN words w ON w.id = t.word_id
            WHERE w.surface = '猫'
            """
        ).fetchall() == [
            (
                "suitability",
                "crossword",
                "manual",
                "tags:2",
                "human review",
                "test tag",
                "internal-fixture",
            )
        ]
        assert connection.execute("SELECT kind FROM build_issues").fetchall() == [
            ("missing_manual_tag_evidence",)
        ]


def test_sudachi_only_proper_noun_is_kept_in_on_demand_auxiliary_layer(tmp_path):
    database = tmp_path / "sudachi.sqlite3"
    build_database(
        BuildConfig(
            output=database,
            additions=tmp_path / "no-additions.tsv",
            sudachi=FIXTURES / "sudachi_raw.csv",
        )
    )
    with sqlite3.connect(database) as connection:
        assert (
            connection.execute("SELECT status FROM words WHERE surface = '東京'").fetchone()[0]
            == "candidate"
        )
        assert (
            connection.execute("SELECT priority FROM words WHERE surface = '1000本'").fetchone()[0]
            == 10
        )
        assert connection.execute(
            """
            SELECT t.axis, t.value, t.evidence
            FROM word_tags t JOIN words w ON w.id = t.word_id
            WHERE w.surface = '東京'
            """
        ).fetchall() == [("proper_type", "place", "地名")]
    snapshot = load_snapshot(database)
    assert {record.surface for record in snapshot.records} == {"1000本"}
    assert snapshot.auxiliary is not None
    assert snapshot.auxiliary.count == 3


def test_ascii_only_sudachi_headword_is_core_only_with_independent_evidence(tmp_path):
    sudachi_only = tmp_path / "sudachi-only.sqlite3"
    build_database(
        BuildConfig(
            output=sudachi_only,
            additions=tmp_path / "no-additions.tsv",
            sudachi=FIXTURES / "sudachi_raw.csv",
        )
    )
    snapshot = load_snapshot(sudachi_only)
    assert "(n)ine" not in {record.surface for record in snapshot.records}

    additions = tmp_path / "additions.tsv"
    write_tsv(
        additions,
        ["surface", "reading", "category", "pos", "priority", "reason", "reference"],
        [
            {
                "surface": "(n)ine",
                "reading": "ないん",
                "category": "general",
                "pos": "名詞",
                "priority": "50",
                "reason": "independent review",
                "reference": "test evidence",
            }
        ],
    )
    corroborated = tmp_path / "corroborated.sqlite3"
    build_database(
        BuildConfig(
            output=corroborated,
            additions=additions,
            sudachi=FIXTURES / "sudachi_raw.csv",
        )
    )
    snapshot = load_snapshot(corroborated)
    record = next(record for record in snapshot.records if record.surface == "(n)ine")
    assert record.status == "accepted"
    assert record.multiple_sources is True


def test_classification_regressions_are_enforced_by_import_and_manual_rules(tmp_path):
    database = tmp_path / "classification.sqlite3"
    build_database(
        BuildConfig(
            output=database,
            additions=tmp_path / "no-additions.tsv",
            corrections=COMPONENT_ROOT / "data/manual/corrections.tsv",
            exclusions=COMPONENT_ROOT / "data/manual/exclusions.tsv",
            jmdict=FIXTURES / "jmdict.xml",
            sudachi=FIXTURES / "classification_sudachi_raw.csv",
            source_manifest=tmp_path / "none.toml",
        )
    )
    snapshot = load_snapshot(database)
    records = {record.surface: record for record in snapshot.records}

    assert records["トランスアクセル"].category == "general"
    assert records["サワムラー"].category == "proper"
    assert records["レクリエーシヨン"].category == "general"
    assert "pyridylthio" not in records
    assert "おしかくせる" not in records
    assert "ねりなおせる" not in records
    assert "ソォ〜" not in records
    assert "おもしれ〜" not in records
    assert "toa" not in records
    assert {"灰いろ", "灰色", "ひざ上", "膝上", "きょごう", "倨傲"} <= records.keys()
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT category, status FROM words WHERE surface = 'toa'"
        ).fetchone() == ("general", "candidate")


def test_repository_rejects_an_unsupported_schema_before_loading(tmp_path):
    database = tmp_path / "unsupported.sqlite3"
    build_database(BuildConfig(output=database))
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE metadata SET value = '999' WHERE key = 'schema_version'"
        )

    with pytest.raises(LexiconUnavailable, match="未対応"):
        load_snapshot(database)
