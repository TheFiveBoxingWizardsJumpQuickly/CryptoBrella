"""Conservative necessary conditions; unsupported Regex always falls back to scanning."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchHints:
    prefix: str = ""
    suffix: str = ""
    contains: str = ""
    minimum_length: int = 0
    exact_length: int | None = None
    suffixes: tuple[str, ...] = ()


# Deliberately excludes groups, flags, escapes, alternation and advanced classes.
# The original Regex still performs the final match, including span selection.
_ATOM = re.compile(r"([ぁ-ゖー]|\.|\[[ぁ-ゖー-]+\])([*+?]|\{[0-9]+(?:,[0-9]*)?\})?")


def regex_hints(pattern: str) -> SearchHints:
    # Only a complete, unquantified literal alternative group at the end.
    # Keep the original Regex for matching and capture/span semantics.
    alternative = re.fullmatch(r"\^?\((?:\?:)?([ぁ-ゖー]+(?:\|[ぁ-ゖー]+)+)\)\$", pattern)
    if alternative:
        suffixes = tuple(dict.fromkeys(alternative[1].split("|")))
        if len(suffixes) <= 32:
            return SearchHints(suffixes=suffixes)
    anchored_start, anchored_end = pattern.startswith("^"), pattern.endswith("$")
    body = pattern[1:] if anchored_start else pattern
    body = body[:-1] if anchored_end else body
    atoms = []
    position = 0
    while position < len(body):
        match = _ATOM.match(body, position)
        if match is None:
            return SearchHints()
        atom, repeat = match.groups()
        low = high = 1
        if repeat in ("*", "+", "?"):
            low = 1 if repeat == "+" else 0
            high = 1 if repeat == "?" else None
        elif repeat:
            bounds = repeat[1:-1].split(",")
            low = int(bounds[0])
            high = low if len(bounds) == 1 else int(bounds[1]) if bounds[1] else None
        literal = atom if len(atom) == 1 and atom != "." else ""
        # Avoid allocating enormous strings for large but syntactically valid repeats.
        if low > 200 or (high is not None and high > 200):
            return SearchHints()
        atoms.append((literal, low, high))
        position = match.end()

    def edge(items):
        value = ""
        for literal, low, high in items:
            if not literal or not low:
                break
            value += literal * low
            if high != low:
                break
        return value

    runs, run = [], ""
    for literal, low, high in atoms:
        if literal and low:
            run += literal * low
        else:
            runs.append(run)
            run = ""
        if low != high:
            runs.append(run)
            run = ""
    required = max([*runs, run], key=len)
    minimum = sum(low for _, low, _ in atoms)
    exact = (minimum if anchored_start and anchored_end
             and all(low == high for _, low, high in atoms) else None)
    return SearchHints(
        prefix=edge(atoms) if anchored_start else "",
        suffix=edge(reversed(atoms))[::-1] if anchored_end else "",
        contains=required, minimum_length=minimum, exact_length=exact,
    )
