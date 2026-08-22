import pytest

from app.cipher.common import assign_digits
from app.cipher.double_columnar import (
    double_columnar_decode,
    double_columnar_encode,
    parse_columnar_key,
)


PBS_PLAINTEXT = "YOURMOTHERWASAHAMSTERANDYOURFATHERSMELTOFELDERBERRIES"
PBS_CIPHERTEXT = "NDODRWTRFHASEERAERMROFLBEOERSAYEAEIHMRALUTERHMTTYSOSU"


def test_standard_double_columnar_matches_pbs_nova_example():
    trace = double_columnar_encode(
        PBS_PLAINTEXT,
        "DESCRIBE",
        "COASTLINE",
    )

    assert trace.intermediate == (
        "THNTTBRAERMDEYEMYEFRORSORERHADHOEOAAALRMSRFEESUWTUSLI"
    )
    assert trace.output == PBS_CIPHERTEXT
    assert "Key:\nD  E  S  C  R  I  B  E" in trace.first_table
    assert "Key order:\n3  4  8  2  7  6  1  5" in trace.first_table
    assert "Data grid:\nY  O  U  R  M  O  T  H" in trace.first_table
    assert "Key order:\n2  7  1  8  9  5  4  6  3" in trace.second_table
    assert double_columnar_decode(
        PBS_CIPHERTEXT,
        "DESCRIBE",
        "COASTLINE",
    ).output == PBS_PLAINTEXT


@pytest.mark.parametrize(
    ("type1", "type2"),
    [
        ("standard", "standard"),
        ("standard", "disrupted"),
        ("disrupted", "standard"),
        ("disrupted", "disrupted"),
    ],
)
def test_each_type_combination_round_trips(type1, type2):
    plaintext = "Meet at 09:30, west gate."
    encoded = double_columnar_encode(
        plaintext, "ZEBRA", "4 1 3 2", type1, type2)
    decoded = double_columnar_decode(
        encoded.output, "ZEBRA", "4 1 3 2", type1, type2)

    assert decoded.output == plaintext


def test_numeric_and_alphabetic_keys_can_describe_the_same_order():
    assert parse_columnar_key("ZEBRA") == [5, 3, 2, 4, 1]
    assert parse_columnar_key("53241") == [5, 3, 2, 4, 1]
    assert parse_columnar_key("5 3 2 4 1") == [5, 3, 2, 4, 1]
    assert parse_columnar_key("5,3,2,4,1") == [5, 3, 2, 4, 1]


def test_duplicate_keyword_letters_are_ranked_left_to_right():
    assert parse_columnar_key("LETTER") == [3, 1, 5, 6, 2, 4]
    assert parse_columnar_key("LETTER") == assign_digits("LETTER")

    trace = double_columnar_encode("DUPLICATE KEY TEST", "LETTER", "KEY")
    assert "Key:\nL  E  T  T  E  R" in trace.first_table
    assert "Key order:\n3  1  5  6  2  4" in trace.first_table


def test_digits_and_mixed_keys_use_symbol_ranking_rules():
    assert parse_columnar_key("3030") == [3, 1, 4, 2]
    assert parse_columnar_key("1 0 2") == [2, 1, 3]
    assert parse_columnar_key("A0B1A0") == [4, 1, 6, 3, 5, 2]

    trace = double_columnar_encode("MIXED KEY", "A0B1A0", "3030")
    assert "Key:\nA  0  B  1  A  0" in trace.first_table
    assert "Key order:\n4  1  6  3  5  2" in trace.first_table


@pytest.mark.parametrize("key", ["", "A", "1", " , ", "AB-12", "A_1"])
def test_invalid_keys_are_rejected(key):
    with pytest.raises(ValueError):
        parse_columnar_key(key)


def test_unknown_columnar_type_is_rejected():
    with pytest.raises(ValueError, match="Columnar type"):
        double_columnar_encode("TEXT", "KEY", "WORD", "myszkowski")


def test_disrupted_table_exposes_fill_pass_mask():
    trace = double_columnar_encode(
        "WEAREDISCOVERED", "ZEBRA", "3 1 4 2", "standard", "disrupted"
    )

    assert (
        "Disrupted fill order "
        "(1 = outside triangular areas, 2 = triangular areas):"
        in trace.second_table
    )
    assert "1" in trace.second_table
    assert "2" in trace.second_table


def test_table_uses_fixed_width_ascii_whitespace_markers():
    trace = double_columnar_encode("A B\nC\t", "KEY", "3 1 2")

    assert "A  SP B" in trace.first_table
    assert "NL C  TB" in trace.first_table
    assert "␠" not in trace.first_table
