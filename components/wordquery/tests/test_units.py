import pytest

from wordquery_jp.normalization import InvalidReading
from wordquery_jp.units import (
    GRID_COMBINE_ALL_SMALL,
    GRID_COMBINE_PHONETIC,
    GRID_SEPARATE,
    count_normalized_reading_units,
    count_units,
    tokenize,
    tokenize_normalized_reading,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("とうきょう", ("と", "う", "き", "ょ", "う")),
        ("キャット", ("き", "ゃ", "っ", "と")),
        ("か\u3099", ("が",)),
        ("ｳﾞｧ", ("ゔ", "ぁ")),
    ],
)
def test_kana_tokens_use_strict_normalization_and_graphemes(value, expected):
    assert tokenize(value, "kana") == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("とうきょう", ("と", "う", "きょ", "う")),
        ("キャット", ("きゃ", "っ", "と")),
        ("ゲーム", ("げ", "ー", "む")),
        ("ヴァイオリン", ("ゔぁ", "い", "お", "り", "ん")),
    ],
)
def test_mora_tokens_join_phonetic_small_kana(value, expected):
    assert tokenize(value, "mora") == expected


def test_surface_tokens_preserve_script_and_count_graphemes():
    assert tokenize("東京", "surface") == ("東", "京")
    assert tokenize("ｶﾞ", "surface") == ("ガ",)
    assert count_units("キャット", "surface") == 4


def test_grid_profiles_make_small_kana_rules_explicit():
    value = "きゃっと"

    assert tokenize(value, "grid", grid_profile=GRID_SEPARATE) == ("き", "ゃ", "っ", "と")
    assert tokenize(value, "grid", grid_profile=GRID_COMBINE_PHONETIC) == (
        "きゃ",
        "っ",
        "と",
    )
    assert tokenize(value, "grid", grid_profile=GRID_COMBINE_ALL_SMALL) == ("きゃっ", "と")


def test_leading_small_kana_remains_an_independent_token():
    assert tokenize("ゃく", "mora") == ("ゃ", "く")


def test_canonical_reading_fast_path_matches_public_api():
    assert tokenize_normalized_reading("とうきょう", "mora") == tokenize(
        "トウキョウ", "mora"
    )
    assert count_normalized_reading_units("とうきょう", "kana") == 5
    assert count_normalized_reading_units("とうきょう", "mora") == 4


def test_reading_units_reject_non_reading_text():
    with pytest.raises(InvalidReading):
        tokenize("東京", "kana")


def test_unknown_unit_is_rejected():
    with pytest.raises(ValueError, match="未対応"):
        tokenize("ねこ", "codepoint")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="この検索では使えない数え方"):
        tokenize_normalized_reading("ねこ", "surface")  # type: ignore[arg-type]
