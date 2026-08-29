import csv
import sqlite3

from wordquery_jp.lexicon.review import (
    JUDGMENT_FIELDS,
    compare_judgments,
    write_judgment_template,
)
from wordquery_jp.lexicon.risk_review import (
    RISK_SAMPLE_FIELDS,
    compare_risk_judgments,
    write_risk_review_sample,
)
from wordquery_jp.lexicon.schema import SCHEMA
from wordquery_jp.normalization import anagram_signature


def write_word(
    connection,
    *,
    word_id,
    surface,
    reading,
    category="general",
    pos="名詞, 普通名詞, 一般",
    status="accepted",
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
    connection.execute(
        """
        INSERT INTO provenance(
            word_id, source, source_entry_id, surface, reading, category, pos,
            reason, reference
        ) VALUES (?, 'sudachidict', ?, ?, ?, ?, ?, '', '')
        """,
        (word_id, f"sudachi:{word_id}", surface, reading, category, pos),
    )


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_rows(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def complete_valid(row):
    row.update(
        {
            "lexicality": "pass",
            "reading_match": "pass",
            "headword_form": "pass",
            "form_integrity": "pass",
            "expected_category": row["claimed_category"],
            "category_match": "pass",
            "overall_label": "valid",
            "confidence": "1.0",
            "reason_codes": "VALID_COMMON_KNOWLEDGE",
            "review_note": "risk fixture",
        }
    )


def build_risk_database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO metadata VALUES ('input_hash', 'risk-test-hash')")
        write_word(
            connection,
            word_id=1,
            surface="A-語",
            reading="あ" * 15,
        )
        write_word(
            connection,
            word_id=2,
            surface="固有語",
            reading="こゆうご",
            pos="名詞, 固有名詞, 一般",
        )
        write_word(
            connection,
            word_id=3,
            surface="通常語",
            reading="つうじょうご",
        )
        write_word(
            connection,
            word_id=4,
            surface="候補名",
            reading="こうほめい",
            category="proper",
            pos="名詞, 固有名詞, 一般",
            status="candidate",
        )
        connection.execute(
            """
            INSERT INTO word_tags(
                word_id, axis, value, source, source_entry_id, evidence, reason, reference
            ) VALUES (4, 'proper_type', 'other', 'sudachidict',
                      'sudachi:4', '固有名詞', '', '')
            """
        )


def test_risk_sample_is_reproducible_deduplicated_and_diagnostic_only(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_risk_database(database)
    first = tmp_path / "risk-a.tsv"
    second = tmp_path / "risk-b.tsv"

    summary = write_risk_review_sample(
        database,
        first,
        per_panel=1,
        seed=17,
    )
    write_risk_review_sample(
        database,
        second,
        per_panel=1,
        seed=17,
    )

    assert first.read_bytes() == second.read_bytes()
    assert summary["populations"] == {
        "alnum_or_symbol_general": 1,
        "candidate_other": 1,
        "long_reading_general": 1,
        "proper_pos_general": 1,
    }
    assert summary["drawn"] == {
        "alnum_or_symbol_general": 1,
        "candidate_other": 1,
        "long_reading_general": 1,
        "proper_pos_general": 1,
    }
    assert summary["draw_count"] == 4
    assert summary["unique_selected"] == 3
    assert summary["selection_overlap"] == 1
    assert summary["risk_flag_sample_counts"] == {
        "alnum_or_symbol_general": 1,
        "candidate_other": 1,
        "long_reading_general": 1,
        "proper_pos_general": 1,
    }
    assert summary["multi_flag_records"] == 1

    rows = read_rows(first)
    assert len(rows) == 3
    assert len({row["sample_id"] for row in rows}) == 3
    assert all(row["diagnostic_only"] == "true" for row in rows)
    assert all(row["sample_weight"] == "1" for row in rows)
    overlapping = next(row for row in rows if row["surface"] == "A-語")
    assert overlapping["risk_flags"] == (
        "alnum_or_symbol_general|long_reading_general"
    )
    assert overlapping["selected_for"] == (
        "alnum_or_symbol_general|long_reading_general"
    )


def test_risk_comparison_counts_overlapping_flags_without_population_estimate(
    tmp_path,
):
    database = tmp_path / "lexicon.sqlite3"
    build_risk_database(database)
    sample = tmp_path / "risk.tsv"
    write_risk_review_sample(database, sample, per_panel=1, seed=17)

    judgments = []
    for reviewer in ("judge-a", "judge-b"):
        judgment = tmp_path / f"{reviewer}.tsv"
        write_judgment_template(
            sample,
            judgment,
            reviewer=reviewer,
            reviewer_kind="llm",
            model_version="fixture-model",
            prompt_version="1.0",
        )
        rows = read_rows(judgment)
        for row in rows:
            complete_valid(row)
        write_rows(judgment, JUDGMENT_FIELDS, rows)
        judgments.append(judgment)

    report = compare_risk_judgments(sample, judgments)
    generic_report = compare_judgments(sample, judgments)

    assert report["diagnostic_only"] is True
    assert report["sample_kind"] == "risk_panel"
    assert report["diagnostic"]["population_estimate"] is False
    assert "population_weighted_record_precision" not in report["diagnostic"]
    assert "population_weighted_record_precision" not in generic_report["diagnostic"]
    assert set(report["per_risk_flag"]) == {
        "alnum_or_symbol_general",
        "candidate_other",
        "long_reading_general",
        "proper_pos_general",
    }
    assert all(
        counts == {"valid": 1}
        for counts in report["per_risk_flag"].values()
    )
    assert set(read_rows(sample)[0]) == set(RISK_SAMPLE_FIELDS)
