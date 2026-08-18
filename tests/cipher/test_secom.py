import pytest

from app.cipher.secom import (
    DEFAULT_WIDTH_MODE,
    WIDTH_MODE_CONTINUE_ACROSS_WIDTHS,
    WIDTH_MODE_RESET_EACH_WIDTH,
    group_digits,
    make_checkerboard,
    make_key_digits,
    make_key_trans,
    make_transposition_widths,
    normalize_ciphertext,
    normalize_key_phrase,
    normalize_plaintext,
    secom_d,
    secom_e,
)


KEY_PHRASE = "MAKE NEW FRIENDS BUT KEEP THE OLD"
PLAINTEXT = "RV TOMORROW AT 1400PM TO COMPLETE TRANSACTION USE DEADDROP AS USUAL"
CIPHERTEXT = (
    "777193862200032042396003829683146080607178016736060606463536"
    "069686740369681890014021906662606660863160549"
)
JAVA_KEY_PHRASE = "SECURE COMMUNICATION KEY"
JAVA_PLAINTEXT = (
    "AN INTEGER VALUE REPRESENTING THE CHARACTER CODE CORRESPONDING TO A "
    "CHARACTER"
)
JAVA_CIPHERTEXT = (
    "249518525422895519594245192611513295821938835534385822992386"
    "3729894055352396225198525939583391328153311991826350525"
)


def test_published_key_schedule_matches_rijmenants_vector():
    key_b_digits, key_digits = make_key_digits(KEY_PHRASE)
    checkerboard_numbers, _, _ = make_checkerboard(key_digits[40:50])

    assert key_b_digits == [3, 7, 2, 8, 1, 0, 9, 6, 4, 5]
    assert checkerboard_numbers == [8, 1, 3, 9, 0, 6, 5, 4, 2, 7]
    assert make_key_trans(key_digits, key_b_digits, checkerboard_numbers) == (
        [8, 4, 8, 9, 8, 2, 4, 5, 8, 9, 8, 2],
        [0, 9, 7, 9, 2, 8, 5, 5, 8, 7, 8],
    )


def test_encrypt_matches_published_rijmenants_vector():
    assert secom_e(PLAINTEXT, KEY_PHRASE) == CIPHERTEXT


def test_default_reset_each_width_mode_matches_java_reference_vector():
    assert DEFAULT_WIDTH_MODE == WIDTH_MODE_RESET_EACH_WIDTH
    assert secom_e(JAVA_PLAINTEXT, JAVA_KEY_PHRASE) == JAVA_CIPHERTEXT
    assert secom_d(JAVA_CIPHERTEXT, JAVA_KEY_PHRASE) == JAVA_PLAINTEXT.replace(
        " ", "*"
    )


def test_width_modes_are_internally_selectable():
    key_b_digits, key_digits = make_key_digits(JAVA_KEY_PHRASE)
    checkerboard_numbers, _, _ = make_checkerboard(key_digits[40:50])

    assert make_transposition_widths(key_digits) == (14, 10)
    assert make_transposition_widths(
        key_digits, WIDTH_MODE_CONTINUE_ACROSS_WIDTHS) == (14, 18)
    assert tuple(map(len, make_key_trans(
        key_digits,
        key_b_digits,
        checkerboard_numbers,
        WIDTH_MODE_CONTINUE_ACROSS_WIDTHS,
    ))) == (14, 18)

    encoded = secom_e(
        JAVA_PLAINTEXT,
        JAVA_KEY_PHRASE,
        WIDTH_MODE_CONTINUE_ACROSS_WIDTHS,
    )
    assert encoded != JAVA_CIPHERTEXT
    assert secom_d(
        encoded, JAVA_KEY_PHRASE, WIDTH_MODE_CONTINUE_ACROSS_WIDTHS
    ) == JAVA_PLAINTEXT.replace(" ", "*")


def test_invalid_width_mode_is_rejected():
    with pytest.raises(ValueError, match="width mode"):
        secom_e("TEST", KEY_PHRASE, "unknown")


def test_encode_trace_exposes_verification_steps_without_changing_result():
    trace = []
    encoded = secom_e(PLAINTEXT, KEY_PHRASE, trace=trace)
    steps = dict(trace)

    assert encoded == CIPHERTEXT
    assert steps["1. Calculating the key phrase digits"] is None
    assert steps[
        "The two results added digit by digit, ignoring carries"
    ].endswith("0880939030")
    assert steps["Number of columns for the two transpositions"] == (
        "1st transposition: 7 + 2 + 3 = 12 columns\n"
        "2nd transposition: 5 + 6 = 11 columns"
    )
    checkerboard_lines = steps["Completed straddling checkerboard"].splitlines()
    assert checkerboard_lines[0] == " | 8 1 3 9 0 6 5 4 2 7"
    assert all(line.index("|") == 1 for line in checkerboard_lines if "|" in line)
    assert "Plaintext written with * for spaces" not in steps
    assert steps["Plaintext converted into numbers"].isdigit()
    assert steps["Digits read off in columns"].isdigit()
    assert steps[
        "Null digits appended to complete a five-digit group"
    ] == "1 digit(s)"
    assert steps["Digits read off in columns and grouped by five"].replace(
        " ", ""
    ) == CIPHERTEXT


def test_decode_trace_lists_reverse_transposition_steps():
    trace = []
    decoded = secom_d(CIPHERTEXT, KEY_PHRASE, trace=trace)
    steps = dict(trace)

    assert decoded.endswith("USUALO")
    assert "Ciphertext in five-digit groups" not in steps
    assert "Reversing the second disrupted transposition" in steps
    assert "Reversing the first columnar transposition" in steps
    assert steps[
        "Digits read row by row outside the triangular areas, then inside them"
    ].isdigit()
    assert steps["Digits read row by row"].isdigit()
    assert steps["Plaintext with * representing spaces"] == decoded


def test_decrypt_matches_published_vector_with_documented_null_padding():
    assert secom_d(group_digits(CIPHERTEXT), KEY_PHRASE) == (
        "RV*TOMORROW*AT*1400PM*TO*COMPLETE*TRANSACTION*USE*DEADDROP*AS*USUALO"
    )


def test_round_trip_without_padding_ambiguity():
    plaintext = "ATTACK AT DAWN"
    assert secom_d(secom_e(plaintext, KEY_PHRASE), KEY_PHRASE) == "ATTACK*AT*DAWN"


def test_key_uses_first_twenty_letters_and_ignores_separators():
    assert normalize_key_phrase("MAKE-NEW FRIENDS, BUT KEEP THE OLD") == "MAKENEWFRIENDSBUTKEE"


@pytest.mark.parametrize("key", ["", "SHORT KEY", "12345678901234567890"])
def test_key_requires_twenty_letters(key):
    with pytest.raises(ValueError, match="at least 20 letters"):
        secom_e("TEST", key)


def test_plaintext_removes_unsupported_characters():
    assert normalize_plaintext("Meet@Noon! 42") == "MEETNOON*42"
    assert secom_e("Meet@Noon! 42", KEY_PHRASE) == secom_e(
        "MEETNOON 42", KEY_PHRASE
    )


def test_ciphertext_removes_unsupported_characters_before_validation():
    assert normalize_ciphertext("75973-a09876 73066/39790") == (
        "75973098767306639790"
    )
    assert secom_d("75973-a09876 73066/39790", KEY_PHRASE) == (
        "ATTACK*AT*DAWN"
    )


@pytest.mark.parametrize("ciphertext", ["1234", "1234A", "NO DIGITS"])
def test_ciphertext_validation(ciphertext):
    with pytest.raises(ValueError):
        secom_d(ciphertext, KEY_PHRASE)
