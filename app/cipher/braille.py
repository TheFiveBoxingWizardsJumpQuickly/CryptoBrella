from .code_tables import braille_ja_table, braille_table


def braille_d(braille_dots):
    ascii_hex = braille_table[braille_dots]
    return chr(int(ascii_hex, 16))


def braille_ja_d(braille_dots):
    return braille_ja_table.get(braille_dots, "")
