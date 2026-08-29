from wordquery_jp.crossword import describe_crossword, fixed_prefix, matches_crossword
from wordquery_jp.models import CrosswordCell
from wordquery_jp.units import GRID_COMBINE_PHONETIC, GRID_SEPARATE


def test_crossword_cells_match_exact_unknown_candidates_and_exclusions():
    cells = (
        CrosswordCell("exact", ("きゃ",)),
        CrosswordCell("unknown"),
        CrosswordCell("include", ("と", "ど")),
        CrosswordCell("exclude", ("ん",)),
    )

    assert matches_crossword(
        "きゃっとー",
        cells,
        GRID_COMBINE_PHONETIC,
    )
    assert not matches_crossword(
        "きゃっどん",
        cells,
        GRID_COMBINE_PHONETIC,
    )
    assert not matches_crossword(
        "きゃとー",
        cells,
        GRID_COMBINE_PHONETIC,
    )
    assert not matches_crossword(
        "きゃっとー",
        cells,
        GRID_SEPARATE,
    )


def test_crossword_description_and_fixed_prefix_are_stable():
    cells = (
        CrosswordCell("exact", ("と",)),
        CrosswordCell("exact", ("う",)),
        CrosswordCell("unknown"),
        CrosswordCell("include", ("ょ", "お")),
        CrosswordCell("exclude", ("ん",)),
    )

    assert fixed_prefix(cells) == ("とう", "prefix")
    assert fixed_prefix(cells[:2]) == ("とう", "exact")
    assert fixed_prefix((CrosswordCell("unknown"),)) == (None, None)
    assert describe_crossword(cells) == (
        "クロスワード5マス: 1マス目 「と」 / 2マス目 「う」 / "
        "3マス目 不明 / 4マス目 「ょ・お」の候補 / 5マス目 「ん」以外"
    )
