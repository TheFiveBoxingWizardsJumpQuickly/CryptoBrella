import re
from dataclasses import dataclass

from .common import assign_digits
from .transposition import (
    _disrupted_columnar_mask,
    columnar_d,
    columnar_e,
    disrupted_columnar_d,
    disrupted_columnar_e,
    make_disrupted_columnar_block,
)


STANDARD = "standard"
DISRUPTED = "disrupted"
SUPPORTED_COLUMNAR_TYPES = (STANDARD, DISRUPTED)


@dataclass(frozen=True)
class DoubleColumnarTrace:
    output: str
    intermediate: str
    key1_order: tuple[int, ...]
    key2_order: tuple[int, ...]
    first_table: str
    second_table: str


def _normalize_key_symbols(key: str) -> list[str]:
    if not isinstance(key, str):
        raise ValueError("Key must be text.")

    key = key.strip()
    if not key:
        raise ValueError("Key must not be empty.")

    if not re.fullmatch(r"[A-Za-z0-9,\s]+", key):
        raise ValueError(
            "Key may contain letters, digits, spaces, and commas only."
        )

    symbols = list(re.sub(r"[,\s]+", "", key).upper())
    if len(symbols) < 2:
        raise ValueError("Key must contain at least two letters or digits.")
    return symbols


def parse_columnar_key(key: str) -> list[int]:
    """Rank key symbols as 0-9 then A-Z, breaking ties left-to-right."""
    return assign_digits("".join(_normalize_key_symbols(key)))


def _validate_columnar_type(columnar_type: str) -> str:
    if columnar_type not in SUPPORTED_COLUMNAR_TYPES:
        supported = ", ".join(SUPPORTED_COLUMNAR_TYPES)
        raise ValueError(f"Columnar type must be one of: {supported}.")
    return columnar_type


def _encode_stage(text: str, order: list[int], columnar_type: str) -> str:
    if columnar_type == STANDARD:
        return "".join(columnar_e(text, order))
    return "".join(disrupted_columnar_e(text, order))


def _decode_stage(text: str, order: list[int], columnar_type: str) -> str:
    if columnar_type == STANDARD:
        return "".join(columnar_d(text, order))
    return "".join(disrupted_columnar_d(text, order))


def _display_character(character: str) -> str:
    return {
        " ": "SP",
        "\n": "NL",
        "\r": "CR",
        "\t": "TB",
    }.get(character, character)


def _key_symbols(key: str) -> list[str]:
    return _normalize_key_symbols(key)


def _format_rows(
    values: list[str],
    width: int,
    cell_width: int,
) -> list[str]:
    rows = []
    for start in range(0, len(values), width):
        row = values[start:start + width]
        row += ["--"] * (width - len(row))
        rows.append(
            " ".join(value.ljust(cell_width) for value in row).rstrip()
        )
    return rows


def format_columnar_table(
    block: str | list[str],
    key: str,
    order: list[int],
    columnar_type: str,
) -> str:
    """Format the actual transposition grid and any disrupted fill mask."""
    columnar_type = _validate_columnar_type(columnar_type)
    width = len(order)
    values = [_display_character(character) for character in block]
    key_symbols = _key_symbols(key)
    cell_width = max(
        2,
        *(len(symbol) for symbol in key_symbols),
        *(len(str(value)) for value in order),
        *(len(value) for value in values),
    )
    lines = [
        "Key:",
        _format_rows(key_symbols, width, cell_width)[0],
        "Key order:",
        _format_rows(
            [str(value) for value in order], width, cell_width
        )[0],
    ]
    lines.extend([
        "Data grid:",
        *_format_rows(values, width, cell_width),
    ])

    if columnar_type == DISRUPTED:
        mask = _disrupted_columnar_mask(len(values), order)
        fill_passes = ["2" if second_pass else "1" for second_pass in mask]
        lines.extend([
            (
                "Disrupted fill order "
                "(1 = outside triangular areas, 2 = triangular areas):"
            ),
            *_format_rows(fill_passes, width, cell_width),
        ])

    return "\n".join(lines)


def _encode_table(
    text: str,
    key: str,
    order: list[int],
    columnar_type: str,
) -> str:
    if columnar_type == STANDARD:
        block = text
    else:
        block = make_disrupted_columnar_block(text, order)
    return format_columnar_table(block, key, order, columnar_type)


def _decode_table(
    text: str,
    key: str,
    order: list[int],
    columnar_type: str,
) -> str:
    block = columnar_d(text, order)
    return format_columnar_table(block, key, order, columnar_type)


def double_columnar_encode(
    text: str,
    key1: str,
    key2: str,
    type1: str = STANDARD,
    type2: str = STANDARD,
) -> DoubleColumnarTrace:
    """Apply the selected first and second columnar transpositions."""
    order1 = parse_columnar_key(key1)
    order2 = parse_columnar_key(key2)
    type1 = _validate_columnar_type(type1)
    type2 = _validate_columnar_type(type2)

    intermediate = _encode_stage(text, order1, type1)
    output = _encode_stage(intermediate, order2, type2)
    return DoubleColumnarTrace(
        output=output,
        intermediate=intermediate,
        key1_order=tuple(order1),
        key2_order=tuple(order2),
        first_table=_encode_table(text, key1, order1, type1),
        second_table=_encode_table(intermediate, key2, order2, type2),
    )


def double_columnar_decode(
    text: str,
    key1: str,
    key2: str,
    type1: str = STANDARD,
    type2: str = STANDARD,
) -> DoubleColumnarTrace:
    """Reverse the second transposition and then the first transposition."""
    order1 = parse_columnar_key(key1)
    order2 = parse_columnar_key(key2)
    type1 = _validate_columnar_type(type1)
    type2 = _validate_columnar_type(type2)

    intermediate = _decode_stage(text, order2, type2)
    output = _decode_stage(intermediate, order1, type1)
    return DoubleColumnarTrace(
        output=output,
        intermediate=intermediate,
        key1_order=tuple(order1),
        key2_order=tuple(order2),
        first_table=_decode_table(intermediate, key1, order1, type1),
        second_table=_decode_table(text, key2, order2, type2),
    )
