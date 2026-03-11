from .code_tables import bacon1_table, morse_code_table, morse_wabun_code_table
from .code_tables import code_table_d, code_table_e
from .text_utils import hiragana_to_katakana, split_dakuten


def morse_e(text, bin_code=False, delimiter=" "):
    text = text.upper()
    return code_table_e(text, morse_code_table, {"-": "0", ".": "1"}, bin_code, delimiter)


def morse_d(text, bin_code=False, delimiter=" "):
    return code_table_d(text, morse_code_table, {"-": "0", ".": "1"}, bin_code, delimiter)


def morse_wabun_e(text, bin_code=False, delimiter=" "):
    text = hiragana_to_katakana(text)
    text = split_dakuten(text)
    return code_table_e(text, morse_wabun_code_table, {"-": "0", ".": "1"}, bin_code, delimiter)


def morse_wabun_d(text, bin_code=False, delimiter=" "):
    return code_table_d(text, morse_wabun_code_table, {"-": "0", ".": "1"}, bin_code, delimiter)


def bacon1_e(text, bin_code=False, delimiter=" "):
    text = text.upper()
    return code_table_e(text, bacon1_table, {"a": "0", "b": "1"}, bin_code, delimiter)


def bacon1_d(text, bin_code=False, delimiter=" "):
    return code_table_d(text, bacon1_table, {"a": "0", "b": "1"}, bin_code, delimiter)


def bacon2_e(text, bin_code=False, delimiter=" "):
    text = text.upper()
    return code_table_e(text, bacon1_table, {"a": "0", "b": "1"}, bin_code, delimiter)


def bacon2_d(text, bin_code=False, delimiter=" "):
    return code_table_d(text, bacon1_table, {"a": "0", "b": "1"}, bin_code, delimiter)
