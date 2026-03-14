from .common import assign_digits, mixed_alphabet, mixed_alphanumeric
from .transposition import columnar_d, columnar_e


def adfgx_e(text, table_keyword, transposition_keyword):
    table = mixed_alphabet(table_keyword, True)
    letter_set = "ADFGX"
    trimmed_text = text.replace(" ", "").upper().replace("J", "I")

    fractionated = ""
    for s in trimmed_text:
        index = table.index(s)
        row_num = int(index / 5)
        col_num = index % 5
        fractionated += letter_set[row_num]
        fractionated += letter_set[col_num]

    return "".join(columnar_e(fractionated, assign_digits(transposition_keyword)))


def adfgx_d(text, table_keyword, transposition_keyword):
    fractionated = columnar_d(text, assign_digits(transposition_keyword))
    table = mixed_alphabet(table_keyword, True)
    letter_set = "ADFGX"

    plain_text = ""
    for i, s in enumerate(fractionated):
        if i % 2 == 0:
            row_num = letter_set.index(s)
        else:
            col_num = letter_set.index(s)
            plain_text += table[row_num * 5 + col_num]

    return plain_text


def adfgvx_e(text, table_keyword, transposition_keyword):
    table = mixed_alphanumeric(table_keyword)
    letter_set = "ADFGVX"
    trimmed_text = text.replace(" ", "").upper()

    fractionated = ""
    for s in trimmed_text:
        index = table.index(s)
        row_num = int(index / 6)
        col_num = index % 6
        fractionated += letter_set[row_num]
        fractionated += letter_set[col_num]

    return "".join(columnar_e(fractionated, assign_digits(transposition_keyword)))


def adfgvx_d(text, table_keyword, transposition_keyword):
    fractionated = columnar_d(text, assign_digits(transposition_keyword))
    table = mixed_alphanumeric(table_keyword)
    letter_set = "ADFGVX"

    plain_text = ""
    for i, s in enumerate(fractionated):
        if i % 2 == 0:
            row_num = letter_set.index(s)
        else:
            col_num = letter_set.index(s)
            plain_text += table[row_num * 6 + col_num]

    return plain_text
