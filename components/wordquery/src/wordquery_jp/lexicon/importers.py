"""Streaming adapters for supported lexicon inputs."""

from __future__ import annotations

import csv
import gzip
import re
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache
from itertools import chain
from pathlib import Path

from lxml import etree

_SUDACHI_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


@dataclass(frozen=True, slots=True)
class ImportedTag:
    axis: str
    value: str
    evidence: str
    reason: str = ""
    reference: str = ""


@dataclass(frozen=True, slots=True)
class ImportedWord:
    surface: str
    reading: str
    category: str
    pos: str
    priority: int
    source: str
    source_entry_id: str
    reason: str = ""
    reference: str = ""
    tags: tuple[ImportedTag, ...] = ()


def iter_jmdict(path: str | Path) -> Iterator[ImportedWord]:
    """Yield surface/reading pairs while respecting JMdict reading restrictions."""
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as source:
        context = etree.iterparse(
            source,
            events=("end",),
            tag="entry",
            load_dtd=True,
            resolve_entities=True,
            no_network=True,
            huge_tree=True,
        )
        for _event, entry in context:
            entry_id = _text(entry.find("ent_seq"))
            forms = {
                _text(node.find("keb")): [_text(value) for value in node.findall("ke_pri")]
                for node in entry.findall("k_ele")
            }
            senses = _jmdict_senses(entry)
            for reading_index, reading_node in enumerate(entry.findall("r_ele")):
                reading = _text(reading_node.find("reb"))
                restrictions = {_text(value) for value in reading_node.findall("re_restr")}
                reading_priorities = [_text(value) for value in reading_node.findall("re_pri")]
                no_kanji = reading_node.find("re_nokanji") is not None
                applicable = {reading} if no_kanji else restrictions or set(forms) or {reading}
                for surface in applicable:
                    priorities = reading_priorities + forms.get(surface, [])
                    for sense_index, sense in senses:
                        if not _sense_applies(sense, surface, reading):
                            continue
                        pos_values = sense["pos"]
                        misc_values = sense["misc"]
                        yield ImportedWord(
                            surface=surface,
                            reading=reading,
                            category=classify_pos(pos_values + misc_values),
                            pos=", ".join(dict.fromkeys(pos_values)),
                            priority=_jmdict_priority(priorities),
                            source="jmdict",
                            source_entry_id=(
                                f"{entry_id}:sense-{sense_index}:reading-{reading_index}:"
                                f"{surface}"
                            ),
                            tags=classify_tags(
                                tuple(pos_values),
                                fields=tuple(sense["field"]),
                                misc=tuple(misc_values),
                                dialects=tuple(sense["dial"]),
                            ),
                        )
            entry.clear()
            while entry.getprevious() is not None:
                del entry.getparent()[0]


def _jmdict_senses(entry: etree._Element) -> list[tuple[int, dict[str, list[str]]]]:
    """Return sense-local attributes, including JMdict's inherited POS rule."""

    result = []
    inherited_pos: list[str] = []
    for sense_index, sense in enumerate(entry.findall("sense")):
        explicit_pos = [_text(value) for value in sense.findall("pos") if _text(value)]
        if explicit_pos:
            inherited_pos = explicit_pos
        result.append(
            (
                sense_index,
                {
                    "pos": list(inherited_pos),
                    "misc": [_text(value) for value in sense.findall("misc") if _text(value)],
                    "field": [_text(value) for value in sense.findall("field") if _text(value)],
                    "dial": [_text(value) for value in sense.findall("dial") if _text(value)],
                    "stagk": [_text(value) for value in sense.findall("stagk") if _text(value)],
                    "stagr": [_text(value) for value in sense.findall("stagr") if _text(value)],
                },
            )
        )
    return result


def _sense_applies(sense: dict[str, list[str]], surface: str, reading: str) -> bool:
    return (not sense["stagk"] or surface in sense["stagk"]) and (
        not sense["stagr"] or reading in sense["stagr"]
    )


def iter_sudachi_csv(path: str | Path) -> Iterator[ImportedWord]:
    """Read an exported Sudachi lexicon CSV.

    A header with surface, reading, dictionary_form and pos columns is preferred.
    Headerless standard Sudachi source rows are also accepted.
    """
    path = Path(path)
    files = sorted(path.rglob("*.csv")) if path.is_dir() else [path]
    seen: set[tuple[str, str, str]] = set()
    for file_path in files:
        with file_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            first = next(reader, None)
            if first is None:
                continue
            lowered = [cell.strip().lower() for cell in first]
            if "surface" in lowered and ("reading" in lowered or "reading_form" in lowered):
                words = _iter_sudachi_header_rows(file_path, lowered, reader)
            else:
                words = _iter_sudachi_raw_rows(file_path, chain([first], reader))
            for word in words:
                key = (word.surface, word.reading, word.category)
                if key not in seen:
                    seen.add(key)
                    yield word


def _iter_sudachi_header_rows(
    file_path: Path, header: list[str], rows: Iterator[list[str]]
) -> Iterator[ImportedWord]:
    indexes = {name: index for index, name in enumerate(header)}
    reading_key = "reading" if "reading" in indexes else "reading_form"
    form_key = "dictionary_form" if "dictionary_form" in indexes else "surface"
    pos_keys = [key for key in header if key == "pos" or key.startswith("pos_")]
    for row_number, row in enumerate(rows, 2):
        if not row or row[0].startswith("#"):
            continue
        surface = _column(row, indexes[form_key]) or _column(row, indexes["surface"])
        reading = _column(row, indexes[reading_key])
        pos_values = [_column(row, indexes[key]) for key in pos_keys]
        yield ImportedWord(
            surface=surface,
            reading=reading,
            category=classify_pos(pos_values),
            pos=", ".join(filter(None, pos_values)),
            priority=10,
            source="sudachidict",
            source_entry_id=f"{file_path.name}:{row_number}",
            tags=classify_tags(tuple(pos_values)),
        )


def _iter_sudachi_raw_rows(file_path: Path, rows: Iterator[list[str]]) -> Iterator[ImportedWord]:
    for row_number, row in enumerate(rows, 1):
        if not row or row[0].startswith("#"):
            continue
        if len(row) < 12:
            raise ValueError(f"{file_path}:{row_number}: Sudachi CSVの列数が不足しています")
        row = [_decode_sudachi_field(value) for value in row]
        surface = row[0]
        pos_values = row[5:11]
        if pos_values and pos_values[0] in {"補助記号", "記号"}:
            continue
        conjugation_form = row[10]
        if conjugation_form not in {"*", "終止形-一般"}:
            continue
        # Sudachi V1 source format: surface, IDs/cost, normalized form, six POS
        # columns, reading form, normalized dictionary form, then split metadata.
        # Reading belongs to the surface form, so inflections must not be paired
        # with the normalized dictionary form.
        reading = row[11]
        if not reading or reading == "*" or not _wordlike_surface(surface):
            continue
        yield ImportedWord(
            surface=surface,
            reading=reading,
            category=classify_pos(pos_values),
            pos=", ".join(value for value in pos_values if value and value != "*"),
            priority=10,
            source="sudachidict",
            source_entry_id=f"{file_path.name}:{row_number}",
            tags=classify_tags(tuple(pos_values)),
        )


def classify_pos(values: list[str]) -> str:
    normalized = [value.strip().lower() for value in values if value and value != "*"]
    function_markers = (
        "助詞",
        "助動詞",
        "接頭辞",
        "接尾辞",
        "particle",
        "auxiliary verb",
        "auxiliary adjective",
        "prefix",
        "suffix",
        "copula",
        "conjunction",
    )
    if any(
        tag.axis == "proper_type"
        for tag in classify_tags(tuple(values), misc=tuple(values))
    ):
        return "proper"
    japanese_content_pos = {"名詞", "動詞", "形容詞", "形状詞", "副詞", "感動詞"}
    english_content_markers = (
        "noun",
        "verb",
        "adjective",
        "adverb",
        "interjection",
        "pronoun",
        "expressions",
    )
    has_content_pos = any(
        value in japanese_content_pos
        or any(value.startswith(marker) for marker in english_content_markers)
        for value in normalized
    )
    has_function_pos = any(
        any(value.startswith(marker) for marker in function_markers) for value in normalized
    )
    if has_function_pos and not has_content_pos:
        return "function"
    return "general"


_PROPER_TYPE_VALUES = {
    "proper noun": "other",
    "character": "character",
    "place name": "place",
    "family or surname": "person",
    "full name of a particular person": "person",
    "given name or forename, gender not specified": "person",
    "organization name": "organization",
    "company name": "organization",
    "group": "organization",
    "work of art, literature, music, etc. name": "work",
    "product name": "product",
    "event": "other",
    "deity": "other",
    "unclassified name": "other",
    "ship name": "other",
}
_FORM_VALUES = {
    "word usually written using kana alone",
    "onomatopoeic or mimetic word",
    "yojijukugo",
    "idiomatic expression",
    "proverb",
}


@cache
def classify_tags(
    pos_values: tuple[str, ...],
    *,
    fields: tuple[str, ...] = (),
    misc: tuple[str, ...] = (),
    dialects: tuple[str, ...] = (),
) -> tuple[ImportedTag, ...]:
    """Map only explicit source attributes while retaining their original value."""

    tags: set[ImportedTag] = set()
    normalized_pos = tuple(value.strip() for value in pos_values if value and value != "*")
    for value in normalized_pos:
        proper_type = _PROPER_TYPE_VALUES.get(value.lower())
        if proper_type:
            tags.add(ImportedTag("proper_type", proper_type, value))
    if "人名" in normalized_pos:
        tags.add(ImportedTag("proper_type", "person", "人名"))
    if "地名" in normalized_pos:
        tags.add(ImportedTag("proper_type", "place", "地名"))
    if "組織名" in normalized_pos:
        tags.add(ImportedTag("proper_type", "organization", "組織名"))
    if "固有名詞" in normalized_pos and not any(
        tag.axis == "proper_type" for tag in tags
    ):
        tags.add(ImportedTag("proper_type", "other", "固有名詞"))

    proper_misc = set()
    for raw_value in misc:
        value = raw_value.strip()
        normalized = value.lower()
        proper_type = _PROPER_TYPE_VALUES.get(normalized)
        if proper_type:
            tags.add(ImportedTag("proper_type", proper_type, value))
            proper_misc.add(value)
    for raw_value in fields:
        value = raw_value.strip()
        if value:
            tags.add(ImportedTag("domain", value, value))
    for raw_value in dialects:
        value = raw_value.strip()
        if value:
            tags.add(ImportedTag("dialect", value, value))
    for raw_value in misc:
        value = raw_value.strip()
        if not value or value in proper_misc:
            continue
        axis = "form" if value.lower() in _FORM_VALUES else "usage"
        tags.add(ImportedTag(axis, value, value))
    return tuple(sorted(tags, key=lambda tag: (tag.axis, tag.value, tag.evidence)))


def _jmdict_priority(tags: list[str]) -> int:
    priority = 20
    for tag in tags:
        if tag in {"ichi1", "news1", "spec1", "gai1"}:
            priority = max(priority, 90)
        elif tag in {"ichi2", "news2", "spec2", "gai2"}:
            priority = max(priority, 70)
        elif tag.startswith("nf") and tag[2:].isdigit():
            priority = max(priority, 70 - int(tag[2:]))
    return priority


def _column(row: list[str], index: int) -> str:
    return row[index].strip() if index < len(row) else ""


def _decode_sudachi_field(value: str) -> str:
    """Decode Unicode literals used by the Sudachi V1 source format."""

    output = []
    cursor = 0
    matches = list(_SUDACHI_UNICODE_ESCAPE.finditer(value))
    index = 0
    while index < len(matches):
        match = matches[index]
        output.append(value[cursor : match.start()])
        code_point = int(match.group(1), 16)
        if 0xD800 <= code_point <= 0xDBFF:
            if index + 1 >= len(matches) or matches[index + 1].start() != match.end():
                raise ValueError(f"Sudachi CSVの孤立サロゲートです: {match.group(0)}")
            low_match = matches[index + 1]
            low = int(low_match.group(1), 16)
            if not 0xDC00 <= low <= 0xDFFF:
                raise ValueError(f"Sudachi CSVの孤立サロゲートです: {match.group(0)}")
            code_point = 0x10000 + ((code_point - 0xD800) << 10) + (low - 0xDC00)
            cursor = low_match.end()
            index += 2
        elif 0xDC00 <= code_point <= 0xDFFF:
            raise ValueError(f"Sudachi CSVの孤立サロゲートです: {match.group(0)}")
        else:
            cursor = match.end()
            index += 1
        output.append(chr(code_point))
    output.append(value[cursor:])
    return "".join(output)


def _text(element: etree._Element | None) -> str:
    return element.text.strip() if element is not None and element.text else ""


def _wordlike_surface(value: str) -> bool:
    return any(character.isalpha() or "\u3040" <= character <= "\u9fff" for character in value)
