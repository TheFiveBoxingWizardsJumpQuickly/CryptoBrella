import app.cipher.fn as fn


EXPECTED_EXPORTS = {
    "affine_d",
    "affine_e",
    "assign_digits",
    "atbash",
    "auto_split_number_string",
    "base_a_to_base_b",
    "base_a_to_base_b_onenumber",
    "beaufort",
    "bifid_d",
    "bifid_e",
    "bigram_frequency",
    "braille_d",
    "braille_ja_d",
    "char_to_codepoint",
    "codepoint_to_char",
    "columnar_d",
    "columnar_e",
    "enigma",
    "factorize",
    "kakushi_decode",
    "kakushi_encode",
    "letter_frequency",
    "mixed_alphabet",
    "morse_d",
    "morse_e",
    "password_generate",
    "phonetic_alphabet_d",
    "phonetic_alphabet_e",
    "playfair_d",
    "playfair_e",
    "plugboard_gen",
    "polybius_d",
    "polybius_e",
    "purple_decode",
    "purple_encode",
    "railfence_d",
    "railfence_e",
    "replace_all",
    "replace_all_case_insensitive",
    "rev",
    "rot",
    "rsa_decode",
    "rsa_encode",
    "skip_d",
    "skip_e",
    "spelling_alphabet_icao_2008",
    "swap_xy_axes",
    "table_subtitution",
    "text_split",
    "unique",
    "uu_decode",
    "uu_encode",
    "valid_chars_for_base_n",
    "vanity_d",
    "vanity_e",
    "vig_d",
    "vig_d_auto",
    "vig_e",
    "vig_e_auto",
}

UNEXPECTED_EXPORTS = {"base64", "binascii", "hashlib", "importlib"}


def test_fn_explicit_exports_are_present():
    exported = set(fn.__all__)
    assert EXPECTED_EXPORTS <= exported
    for name in EXPECTED_EXPORTS:
        assert hasattr(fn, name)


def test_fn_explicit_exports_do_not_include_stdlib_modules():
    exported = set(fn.__all__)
    assert UNEXPECTED_EXPORTS.isdisjoint(exported)
