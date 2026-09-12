"""Shared immutable domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .units import LengthUnit

Category = Literal["general", "proper", "function"]
RecordStatus = Literal["accepted", "candidate"]
MatchType = Literal["contains", "prefix", "suffix", "exact"]
SearchMode = Literal["reading", "pattern", "regex", "anagram"]
SortMode = Literal["commonness", "dictionary_priority", "kana"]
VocabularyLayer = Literal["core", "auxiliary"]


@dataclass(frozen=True, slots=True)
class TagFilter:
    axis: str
    value: str


@dataclass(frozen=True, slots=True)
class TagEvidence:
    source: str
    source_entry_id: str
    evidence: str
    reason: str = ""
    reference: str = ""


@dataclass(frozen=True, slots=True)
class VocabularyTag:
    axis: str
    value: str
    evidence: tuple[TagEvidence, ...]


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source: str
    source_entry_id: str
    surface: str
    reading: str
    category: Category
    pos: str
    reason: str = ""
    reference: str = ""


@dataclass(frozen=True, slots=True)
class SearchRecord:
    id: int
    surface: str
    reading: str
    normalized_reading: str
    signature: str
    category: Category
    pos: str
    priority: int
    status: RecordStatus = "accepted"
    tags: tuple[VocabularyTag, ...] = ()
    sources: tuple[SourceRecord, ...] = ()
    multiple_sources: bool = False


@dataclass(frozen=True, slots=True)
class SearchOptions:
    include_proper: bool = False
    include_function: bool = False
    reading_length: int | None = None
    length_unit: LengthUnit = "kana"
    fold_small_kana: bool = False
    must_include: str | None = None
    must_exclude: str | None = None
    limit: int = 100
    sort_mode: SortMode = "dictionary_priority"
    vocabulary_layers: tuple[VocabularyLayer, ...] = ("core", "auxiliary")
    tag_filters: tuple[TagFilter, ...] = ()
    deprioritize_vocabulary_layers: tuple[VocabularyLayer, ...] = ()
    deprioritize_tag_filters: tuple[TagFilter, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchRequest:
    version: int
    mode: SearchMode
    query: str
    match_type: MatchType = "contains"
    length: int | None = None
    length_unit: LengthUnit = "kana"
    fold_small_kana: bool = False
    include_proper: bool = False
    include_function: bool = False
    must_include: str | None = None
    must_exclude: str | None = None
    limit: int = 100
    sort_mode: SortMode = "dictionary_priority"
    vocabulary_layers: tuple[VocabularyLayer, ...] = ("core", "auxiliary")
    tag_filters: tuple[TagFilter, ...] = ()
    deprioritize_vocabulary_layers: tuple[VocabularyLayer, ...] = ()
    deprioritize_tag_filters: tuple[TagFilter, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchResponse:
    normalized_query: str
    total: int
    results: tuple[SearchRecord, ...]
    match_spans: tuple[tuple[int, int] | None, ...]
    sort_scores: tuple[int | None, ...]
    sort_reasons: tuple[tuple[str, ...], ...]
    deprioritize_reasons: tuple[tuple[str, ...], ...]
    truncated: bool
    duration_ms: float
    condition_description: str | None = None
