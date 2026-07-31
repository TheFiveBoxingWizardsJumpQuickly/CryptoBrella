"""SECOM hand cipher.

Specification and worked vector:
https://www.ciphermachinesandcryptology.com/en/secom.htm

Reference implementation used for the default width interpretation:
https://github.com/asilichenko/secom-cipher-gui#the-secom-cipher
"""

import re

from .common import assign_digits
from .transposition import (
    columnar_d,
    columnar_e,
    disrupted_columnar_d,
    disrupted_columnar_e,
    make_disrupted_columnar_block,
)


SUPPORTED_PLAINTEXT = re.compile(r"^[A-Z0-9\s]*$")
WIDTH_MODE_RESET_EACH_WIDTH = "reset_each_width"
WIDTH_MODE_CONTINUE_ACROSS_WIDTHS = "continue_across_widths"
DEFAULT_WIDTH_MODE = WIDTH_MODE_RESET_EACH_WIDTH
WIDTH_MODES = (
    WIDTH_MODE_RESET_EACH_WIDTH,
    WIDTH_MODE_CONTINUE_ACROSS_WIDTHS,
)


def normalize_key_phrase(key):
    normalized = re.sub(r"[^A-Z]", "", key.upper())
    if len(normalized) < 20:
        raise ValueError("SECOM key phrase must contain at least 20 letters.")
    return normalized[:20]


def normalize_plaintext(text):
    normalized = text.upper()
    if not SUPPORTED_PLAINTEXT.fullmatch(normalized):
        raise ValueError("SECOM plaintext supports only letters, digits, and spaces.")
    return re.sub(r"\s", "*", normalized)


def normalize_ciphertext(text):
    normalized = re.sub(r"\s", "", text)
    if not re.fullmatch(r"[0-9]+", normalized):
        raise ValueError("SECOM ciphertext must contain digits and whitespace only.")
    if len(normalized) % 5:
        raise ValueError("SECOM ciphertext length must be a multiple of five digits.")
    return normalized


def group_digits(text, size=5):
    return " ".join(text[i:i + size] for i in range(0, len(text), size))


def _trace_step(trace, label, value=None):
    if trace is not None:
        trace.append((label, None if value is None else str(value)))


def _digit_rows(digits, width=10):
    value = "".join(str(digit) for digit in digits)
    return "\n".join(
        value[i:i + width] for i in range(0, len(value), width)
    )


def _digits(digits):
    return "".join(str(digit) for digit in digits)


def _format_checkerboard(checkerboard_numbers, checkerboard):
    rows = [checkerboard[i:i + 10] for i in range(0, 40, 10)]
    prefixes = [" ", str(checkerboard_numbers[2]),
                str(checkerboard_numbers[5]), str(checkerboard_numbers[8])]
    lines = ["  | " + " ".join(str(x) for x in checkerboard_numbers)]
    lines.append("  +-" + "-" * 19)
    lines.extend(
        f"{prefix}| " + " ".join(row)
        for prefix, row in zip(prefixes, rows)
    )
    return "\n".join(lines)


def _format_transposition_block(digits, key):
    width = len(key)
    value = "".join(str(digit) for digit in digits)
    rows = []
    for index in range(0, len(value), width):
        row = value[index:index + width]
        rows.append(row + "X" * (width - len(row)))
    return _digits(key) + "\n" + "-" * width + "\n" + "\n".join(rows)


def _trace_key_phrase_digits(trace, key, key_b_digits, key_digits):
    if trace is None:
        return

    normalized_key = normalize_key_phrase(key)
    key_a = normalized_key[:10]
    key_b = normalized_key[10:20]
    key_a_digits = ten2zero(assign_digits(key_a))
    seed = [(x + y) % 10 for x, y in zip(key_a_digits, key_b_digits)]

    _trace_step(trace, "1. Calculating the key phrase digits")
    _trace_step(trace, "First 20 letters of the key phrase", normalized_key)
    _trace_step(trace, "Key phrase divided into two halves", f"{key_a}\n{key_b}")
    _trace_step(
        trace,
        "Digits assigned within each half",
        f"{key_a}\n{_digits(key_a_digits)}\n{key_b}\n{_digits(key_b_digits)}",
    )
    _trace_step(
        trace,
        "The two results added digit by digit, ignoring carries",
        f" {_digits(key_a_digits)}\n+{_digits(key_b_digits)}\n"
        f" ----------\n {_digits(seed)}",
    )
    _trace_step(
        trace, "50 digits generated through chain addition",
        _digit_rows(key_digits))


def _trace_checkerboard(trace, checkerboard_numbers, checkerboard):
    _trace_step(trace, "2. The straddling checkerboard")
    _trace_step(
        trace, "Top row of numbers", _digits(checkerboard_numbers))
    _trace_step(
        trace,
        "Completed straddling checkerboard",
        _format_checkerboard(checkerboard_numbers, checkerboard),
    )


def _trace_transposition_keys(
        trace, key_b_digits, key_digits, checkerboard_numbers,
        first_trans_key, second_trans_key, width_mode):
    width_terms = _make_transposition_width_terms(key_digits, width_mode)
    width_calculations = "\n".join(
        f"{ordinal} transposition: "
        + " + ".join(str(digit) for digit in terms)
        + f" = {sum(terms)} columns"
        for ordinal, terms in zip(("1st", "2nd"), width_terms)
    )
    transposition_order = [
        (x + y) % 10 for x, y in zip(key_b_digits, checkerboard_numbers)
    ]

    _trace_step(trace, "Preparing the two columnar transpositions")
    _trace_step(
        trace,
        "Number of columns for the two transpositions",
        width_calculations,
    )
    _trace_step(
        trace,
        "Key for reading the 50 generated digits by columns",
        f" {_digits(key_b_digits)}  second half of key phrase\n"
        f"+{_digits(checkerboard_numbers)}  checkerboard top row\n"
        f" ----------\n {_digits(transposition_order)}",
    )
    _trace_step(
        trace,
        "Digits for the two transpositions",
        f"1st: {_digits(first_trans_key)}\n2nd: {_digits(second_trans_key)}",
    )


def chain_addition(x):
    y = [0]*10
    for i in range(9):
        y[i] = (x[i]+x[i+1]) % 10
    y[9] = (x[9]+y[0]) % 10
    return y


def zero2ten(ls):
    return [10 if x == 0 else int(x) for x in ls]


def ten2zero(ls):
    return [0 if x == 10 else x for x in ls]


def make_key_digits(key):
    key = normalize_key_phrase(key)
    key_a = key[0:10]
    key_b = key[10:20]
    key_a_digits = ten2zero(assign_digits(key_a))
    key_b_digits = ten2zero(assign_digits(key_b))
    key_digits0 = [(x+y) % 10 for(x, y) in zip(key_a_digits, key_b_digits)]

    key_digits1 = chain_addition(key_digits0)
    key_digits2 = chain_addition(key_digits1)
    key_digits3 = chain_addition(key_digits2)
    key_digits4 = chain_addition(key_digits3)
    key_digits5 = chain_addition(key_digits4)
    key_digits = key_digits1+key_digits2+key_digits3+key_digits4+key_digits5

    return key_b_digits, key_digits


def make_checkerboard(key_digits):
    checkerboard_numbers = ten2zero(assign_digits(zero2ten(key_digits)))

    checkerboard = [0]*40
    checkerboard_index = [0]*40
    row0 = "ES TO NI A"
    row1 = "BCDFGHJKLM"
    row2 = "PQRUVWXYZ*"
    row3 = "1234567890"
    offset1 = int(checkerboard_numbers[2])-1
    offset2 = int(checkerboard_numbers[5])-1
    offset3 = int(checkerboard_numbers[8])-1

    for i in range(0, 10):
        checkerboard[i] = row0[i]
        checkerboard_index[i] = str(checkerboard_numbers[i])
    for i in range(0, 10):
        checkerboard[10+((i+offset1) % 10)] = row1[i]
        checkerboard_index[10+i] = str(checkerboard_numbers[2]) + \
            str(checkerboard_numbers[i])
    for i in range(0, 10):
        checkerboard[20+((i+offset2) % 10)] = row2[i]
        checkerboard_index[20+i] = str(checkerboard_numbers[5]) + \
            str(checkerboard_numbers[i])
    for i in range(0, 10):
        checkerboard[30+((i+offset3) % 10)] = row3[i]
        checkerboard_index[30+i] = str(checkerboard_numbers[8]) + \
            str(checkerboard_numbers[i])

    return checkerboard_numbers, checkerboard, checkerboard_index


def _make_transposition_width_terms(key_digits, width_mode):
    if width_mode not in WIDTH_MODES:
        raise ValueError(
            "SECOM width mode must be one of: " + ", ".join(WIDTH_MODES)
        )

    width_terms = []
    encountered = set()
    index = len(key_digits)

    for _ in range(2):
        if width_mode == WIDTH_MODE_RESET_EACH_WIDTH:
            encountered = set()

        terms = []
        while sum(terms) <= 9:
            if index == 0:
                raise ValueError(
                    "SECOM key digits cannot produce two transposition widths."
                )
            index -= 1
            digit = key_digits[index]
            if digit not in encountered:
                encountered.add(digit)
                terms.append(digit)
        width_terms.append(terms)

    return width_terms


def make_transposition_widths(key_digits, width_mode=DEFAULT_WIDTH_MODE):
    """Derive both transposition widths using the selected SECOM variant.

    ``reset_each_width`` resets the set of encountered digits before deriving
    the second width. ``continue_across_widths`` keeps the set across both
    widths. In both modes, scanning continues from the previous position.
    """
    width_terms = _make_transposition_width_terms(key_digits, width_mode)

    return tuple(sum(terms) for terms in width_terms)


def make_key_trans(
        key_digits, key_b_digits, checkerboard_numbers,
        width_mode=DEFAULT_WIDTH_MODE):
    key_trans_pre = [(x+y) % 10 for(x, y)
                     in zip(key_b_digits, checkerboard_numbers)]
    key_trans = columnar_e(key_digits, assign_digits(zero2ten(key_trans_pre)))

    first_trans_len, second_trans_len = make_transposition_widths(
        key_digits, width_mode)

    first_trans_key = key_trans[0:first_trans_len]
    second_trans_key = key_trans[first_trans_len:first_trans_len+second_trans_len]
    return first_trans_key, second_trans_key


def secom_e(c, key, width_mode=DEFAULT_WIDTH_MODE, trace=None):
    # Checkerboard and transposition keys
    c = normalize_plaintext(c)
    key_b_digits, key_digits = make_key_digits(key)
    checkerboard_numbers, checkerboard, checkerboard_index = make_checkerboard(
        key_digits[40:50])
    first_trans_key, second_trans_key = make_key_trans(
        key_digits, key_b_digits, checkerboard_numbers, width_mode)
    _trace_key_phrase_digits(trace, key, key_b_digits, key_digits)
    _trace_checkerboard(trace, checkerboard_numbers, checkerboard)
    _trace_step(trace, "Plaintext written with * for spaces", c)

    # Checkerboard
    plain_numbers = ""
    for s in c:
        ind = checkerboard.index(s)
        c_ind = checkerboard_index[ind]
        plain_numbers += c_ind

    padding = "0" * (-len(plain_numbers) % 5)
    _trace_step(
        trace, "Plaintext converted into numbers",
        group_digits(plain_numbers))
    _trace_transposition_keys(
        trace,
        key_b_digits,
        key_digits,
        checkerboard_numbers,
        first_trans_key,
        second_trans_key,
        width_mode,
    )
    _trace_step(trace, "3. The first columnar transposition")
    _trace_step(
        trace,
        "Null digits appended to complete a five-digit group",
        f"{len(padding)} digit(s)" if padding else "None",
    )
    plain_numbers += padding
    _trace_step(
        trace,
        "First transposition block filled row by row",
        _format_transposition_block(plain_numbers, first_trans_key),
    )

    # First columnar transposition
    numbers_trans1 = columnar_e(
        plain_numbers, assign_digits(zero2ten(first_trans_key)))
    _trace_step(
        trace, "Digits read off in columns",
        group_digits("".join(numbers_trans1)))

    # Second disrupted columnar transposition
    second_key_order = assign_digits(zero2ten(second_trans_key))
    disrupted_block = make_disrupted_columnar_block(
        numbers_trans1, second_key_order)
    _trace_step(trace, "4. The second disrupted columnar transposition")
    _trace_step(
        trace,
        "Block filled outside the triangular areas, then inside them",
        _format_transposition_block(disrupted_block, second_trans_key),
    )
    numbers_trans2 = disrupted_columnar_e(numbers_trans1, second_key_order)
    _trace_step(
        trace, "Digits read off in columns and grouped by five",
        group_digits("".join(numbers_trans2)))

    return "".join(numbers_trans2)


def secom_d(c, key, width_mode=DEFAULT_WIDTH_MODE, trace=None):
    # Checkerboard and transposition keys
    c = normalize_ciphertext(c)
    key_b_digits, key_digits = make_key_digits(key)
    checkerboard_numbers, checkerboard, checkerboard_index = make_checkerboard(
        key_digits[40:50])
    first_trans_key, second_trans_key = make_key_trans(
        key_digits, key_b_digits, checkerboard_numbers, width_mode)
    _trace_key_phrase_digits(trace, key, key_b_digits, key_digits)
    _trace_checkerboard(trace, checkerboard_numbers, checkerboard)
    _trace_transposition_keys(
        trace,
        key_b_digits,
        key_digits,
        checkerboard_numbers,
        first_trans_key,
        second_trans_key,
        width_mode,
    )
    _trace_step(trace, "Ciphertext in five-digit groups", group_digits(c))

    # Second disrupted columnar transposition
    second_key_order = assign_digits(zero2ten(second_trans_key))
    disrupted_block = columnar_d(c, second_key_order)
    _trace_step(trace, "Reversing the second disrupted transposition")
    _trace_step(
        trace,
        "Disrupted block reconstructed column by column",
        _format_transposition_block(disrupted_block, second_trans_key),
    )
    numbers_trans1 = disrupted_columnar_d(c, second_key_order)
    _trace_step(
        trace,
        "Digits read row by row outside the triangular areas, then inside them",
        group_digits("".join(numbers_trans1)))

    # First columnar transposition
    first_key_order = assign_digits(zero2ten(first_trans_key))
    plain_numbers = columnar_d(numbers_trans1, first_key_order)
    _trace_step(trace, "Reversing the first columnar transposition")
    _trace_step(
        trace,
        "First transposition block reconstructed column by column",
        _format_transposition_block(plain_numbers, first_trans_key),
    )
    _trace_step(
        trace, "Digits read row by row", group_digits("".join(plain_numbers)))

    # Checkerboard
    p = ""
    k = ""
    for i in range(len(plain_numbers)):
        k += plain_numbers[i]
        if (int(k) != checkerboard_numbers[2] and int(k) != checkerboard_numbers[5] and int(k) != checkerboard_numbers[8]):
            ind = checkerboard_index.index(k)
            p += checkerboard[ind]
            k = ""
        elif len(k) == 2:
            ind = checkerboard_index.index(k)
            p += checkerboard[ind]
            k = ""

    _trace_step(trace, "Converting the numbers with the straddling checkerboard")
    _trace_step(trace, "Plaintext with * representing spaces", p)
    return "".join(p)
