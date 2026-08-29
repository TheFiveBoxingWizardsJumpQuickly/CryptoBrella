"""A small non-Regex reading pattern grammar for ordinary users."""

from __future__ import annotations

from dataclasses import dataclass

import regex

from .normalization import normalize_reading, normalize_text


class PatternSyntaxError(ValueError):
    def __init__(self, message: str, position: int) -> None:
        super().__init__(f"検索パターンの{position + 1}文字目: {message}")
        self.position = position


@dataclass(frozen=True, slots=True)
class PatternPlan:
    compiled: regex.Pattern
    normalized_pattern: str
    description: str
    prefilter_query: str | None
    prefilter_match_type: str | None


@dataclass(frozen=True, slots=True)
class _Token:
    kind: str
    value: str
    position: int


def compile_reading_pattern(pattern: str) -> PatternPlan:
    """Compile the documented glob-like grammar to an anchored safe Regex."""

    if not pattern:
        raise PatternSyntaxError("パターンを入力してください。", 0)
    tokens = _parse(pattern)
    regex_parts: list[str] = []
    normalized_parts: list[str] = []
    descriptions: list[str] = []
    for token in tokens:
        if token.kind == "literal":
            regex_parts.append(regex.escape(token.value))
            normalized_parts.append(token.value)
            descriptions.append(f"「{token.value}」")
        elif token.kind == "one":
            regex_parts.append(".")
            normalized_parts.append("?")
            descriptions.append("任意の1文字")
        elif token.kind == "many":
            regex_parts.append(".*")
            normalized_parts.append("*")
            descriptions.append("任意の0文字以上")
        elif token.kind == "include":
            escaped = "".join(regex.escape(character) for character in token.value)
            regex_parts.append(f"[{escaped}]")
            normalized_parts.append(f"[{token.value}]")
            descriptions.append(
                f"「{'・'.join(token.value)}」のいずれか1文字"
            )
        else:
            escaped = "".join(regex.escape(character) for character in token.value)
            regex_parts.append(f"[^{escaped}]")
            normalized_parts.append(f"[!{token.value}]")
            descriptions.append(f"「{'・'.join(token.value)}」以外の1文字")

    literal_prefix = ""
    for token in tokens:
        if token.kind != "literal":
            break
        literal_prefix += token.value
    all_literal = all(token.kind == "literal" for token in tokens)
    return PatternPlan(
        compiled=regex.compile(r"\A" + "".join(regex_parts) + r"\Z", regex.VERSION0),
        normalized_pattern="".join(normalized_parts),
        description="パターン全体: " + " → ".join(descriptions),
        prefilter_query=literal_prefix or None,
        prefilter_match_type=(
            "exact" if all_literal else "prefix" if literal_prefix else None
        ),
    )


def _parse(pattern: str) -> list[_Token]:
    tokens: list[_Token] = []
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if character == "?":
            tokens.append(_Token("one", "", index))
            index += 1
            continue
        if character == "*":
            if not tokens or tokens[-1].kind != "many":
                tokens.append(_Token("many", "", index))
            index += 1
            continue
        if character == "[":
            closing = pattern.find("]", index + 1)
            if closing < 0:
                raise PatternSyntaxError("対応する ] がありません。", index)
            raw_content = pattern[index + 1 : closing]
            exclusion = raw_content.startswith("!")
            content = raw_content[1:] if exclusion else raw_content
            content_start = index + 2 if exclusion else index + 1
            if not content:
                raise PatternSyntaxError("候補または除外するかながありません。", closing)
            for offset, reserved in enumerate(content):
                if reserved in "?*[]!":
                    raise PatternSyntaxError(
                        "候補・除外の中にはかなだけを入力してください。",
                        content_start + offset,
                    )
            normalized = _normalize_literal(content, content_start)
            unique = "".join(dict.fromkeys(normalized))
            tokens.append(
                _Token("exclude" if exclusion else "include", unique, index)
            )
            index = closing + 1
            continue
        if character in "]!":
            raise PatternSyntaxError(
                f"{character} は候補・除外の記法の中で使用してください。",
                index,
            )

        end = index
        while end < len(pattern) and pattern[end] not in "?*[]!":
            end += 1
        normalized = _normalize_literal(pattern[index:end], index)
        tokens.append(_Token("literal", normalized, index))
        index = end
    return tokens


def _normalize_literal(value: str, position: int) -> str:
    normalized_text = normalize_text(value)
    try:
        normalized = normalize_reading(normalized_text)
    except ValueError as exc:
        invalid_position = _first_invalid_position(value, position)
        raise PatternSyntaxError(
            "かな、?、*、[かき]、[!かき]だけを使用してください。",
            invalid_position,
        ) from exc
    if normalized != normalized_text:
        raise PatternSyntaxError(
            "空白は使用できません。",
            position,
        )
    return normalized


def _first_invalid_position(value: str, start: int) -> int:
    for offset, character in enumerate(value):
        normalized = normalize_text(character)
        try:
            if normalize_reading(normalized) != normalized:
                return start + offset
        except ValueError:
            return start + offset
    return start
