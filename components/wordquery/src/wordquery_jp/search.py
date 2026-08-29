"""Framework-independent regex and exact-anagram search."""

from __future__ import annotations

import time
from bisect import insort
from collections.abc import Callable, Iterable, Iterator
from dataclasses import replace

import regex

from .crossword import describe_crossword, fixed_prefix, matches_crossword
from .models import (
    CrosswordCell,
    MatchType,
    SearchOptions,
    SearchRecord,
    SearchRequest,
    SearchResponse,
)
from .normalization import anagram_signature, normalize_pattern, normalize_reading, normalize_text
from .pattern import PatternSyntaxError, compile_reading_pattern
from .repository import SearchSnapshot, load_sources, load_tagged_word_ids, load_tags
from .sorting import explain_sort, sort_key
from .units import (
    GridProfileName,
    ReadingUnit,
    count_normalized_reading_units,
    count_units,
    resolve_grid_profile,
)


class QueryValidationError(ValueError):
    def __init__(self, message: str, *, position: int | None = None) -> None:
        super().__init__(message)
        self.position = position


class SearchTimedOut(TimeoutError):
    pass


class SearchService:
    def __init__(
        self,
        snapshot: SearchSnapshot,
        *,
        max_query_length: int = 200,
        timeout_seconds: float = 1.5,
    ) -> None:
        self.snapshot = snapshot
        self.max_query_length = max_query_length
        self.timeout_seconds = timeout_seconds

    def execute(self, search_request: SearchRequest) -> SearchResponse:
        """Execute a validated versioned request through the framework-independent core."""

        options = SearchOptions(
            include_proper=search_request.include_proper,
            include_function=search_request.include_function,
            reading_length=search_request.length,
            length_unit=search_request.length_unit,
            grid_profile=search_request.grid_profile,
            must_include=search_request.must_include,
            must_exclude=search_request.must_exclude,
            limit=search_request.limit,
            sort_mode=search_request.sort_mode,
            vocabulary_layers=search_request.vocabulary_layers,
            tag_filters=search_request.tag_filters,
            deprioritize_vocabulary_layers=search_request.deprioritize_vocabulary_layers,
            deprioritize_tag_filters=search_request.deprioritize_tag_filters,
        )
        if search_request.mode == "anagram":
            return self.anagram_search(search_request.query, options)
        if search_request.mode == "pattern":
            return self.pattern_search(search_request.query, options)
        if search_request.mode == "crossword":
            return self.crossword_search(
                search_request.grid_cells,
                search_request.grid_profile,
                options,
            )
        if search_request.mode == "regex":
            return self.regex_search(search_request.query, options)
        return self.reading_search(search_request.query, search_request.match_type, options)

    def pattern_search(
        self,
        pattern: str,
        options: SearchOptions | None = None,
    ) -> SearchResponse:
        options = options or SearchOptions()
        self._validate_length(pattern)
        try:
            plan = compile_reading_pattern(pattern)
        except PatternSyntaxError as exc:
            raise QueryValidationError(
                str(exc),
                position=exc.position,
            ) from exc
        auxiliary_records = self._auxiliary_records(
            options,
            normalized_query=plan.prefilter_query,
            match_type=plan.prefilter_match_type,
        )
        return self._search_compiled(
            plan.compiled,
            plan.normalized_pattern,
            options,
            auxiliary_records=auxiliary_records,
            include_match_spans=False,
            condition_description=plan.description,
        )

    def crossword_search(
        self,
        cells: tuple[CrosswordCell, ...],
        grid_profile: GridProfileName,
        options: SearchOptions | None = None,
    ) -> SearchResponse:
        if not cells:
            raise QueryValidationError("クロスワードのマスを1つ以上指定してください。")
        try:
            profile = resolve_grid_profile(grid_profile)
        except ValueError as exc:
            raise QueryValidationError(str(exc)) from exc
        options = replace(
            options or SearchOptions(),
            reading_length=len(cells),
            length_unit="grid",
            grid_profile=grid_profile,
        )
        prefilter_query, prefilter_match_type = fixed_prefix(cells)
        auxiliary_records = self._auxiliary_records(
            options,
            normalized_query=prefilter_query,
            match_type=prefilter_match_type,
        )

        def matcher(
            record: SearchRecord,
            _remaining: float,
        ) -> tuple[bool, tuple[int, int] | None]:
            return matches_crossword(
                record.normalized_reading,
                cells,
                profile,
            ), None

        return self._search_matching(
            matcher,
            "",
            options,
            auxiliary_records=auxiliary_records,
            condition_description=describe_crossword(cells),
        )

    def regex_search(self, pattern: str, options: SearchOptions | None = None) -> SearchResponse:
        options = options or SearchOptions()
        normalized = normalize_pattern(pattern)
        self._validate_length(normalized)
        try:
            compiled = regex.compile(normalized, regex.VERSION0)
        except regex.error as exc:
            raise QueryValidationError(f"Regex構文が正しくありません: {exc}") from exc

        return self._search_compiled(
            compiled,
            normalized,
            options,
            auxiliary_records=self._auxiliary_records(options),
        )

    def reading_search(
        self,
        text: str,
        match_type: MatchType = "contains",
        options: SearchOptions | None = None,
    ) -> SearchResponse:
        options = options or SearchOptions()
        if not text.strip() and (options.reading_length is not None or options.tag_filters):
            return self._search_compiled(
                regex.compile("", regex.VERSION0),
                "",
                options,
                auxiliary_records=self._auxiliary_records(
                    options,
                    normalized_query="",
                    match_type=match_type,
                ),
            )
        if match_type == "regex":
            return self.regex_search(text, options)
        if match_type not in {"contains", "prefix", "suffix", "exact"}:
            raise QueryValidationError("一致の指定が正しくありません。")
        try:
            normalized = normalize_reading(text)
        except ValueError as exc:
            raise QueryValidationError(str(exc)) from exc
        self._validate_length(normalized)
        escaped = regex.escape(normalized)
        patterns = {
            "contains": escaped,
            "prefix": f"^{escaped}",
            "suffix": f"{escaped}$",
            "exact": f"^{escaped}$",
        }
        compiled = regex.compile(patterns[match_type], regex.VERSION0)
        return self._search_compiled(
            compiled,
            normalized,
            options,
            auxiliary_records=self._auxiliary_records(
                options,
                normalized_query=normalized,
                match_type=match_type,
            ),
        )

    def _search_compiled(
        self,
        compiled: regex.Pattern,
        normalized_query: str,
        options: SearchOptions,
        *,
        auxiliary_records: Iterator[SearchRecord] | None = None,
        include_match_spans: bool = True,
        condition_description: str | None = None,
    ) -> SearchResponse:
        def matcher(
            record: SearchRecord,
            remaining: float,
        ) -> tuple[bool, tuple[int, int] | None]:
            match = compiled.search(record.normalized_reading, timeout=remaining)
            if match is None:
                return False, None
            span = (
                _display_match_span(record, match.span())
                if include_match_spans
                else None
            )
            return True, span

        return self._search_matching(
            matcher,
            normalized_query,
            options,
            auxiliary_records=auxiliary_records,
            condition_description=condition_description,
        )

    def _search_matching(
        self,
        matcher: Callable[
            [SearchRecord, float],
            tuple[bool, tuple[int, int] | None],
        ],
        normalized_query: str,
        options: SearchOptions,
        *,
        auxiliary_records: Iterator[SearchRecord] | None = None,
        condition_description: str | None = None,
    ) -> SearchResponse:
        started = time.monotonic()
        deadline = started + self.timeout_seconds
        top_matches: list[
            tuple[
                tuple[object, ...],
                int,
                SearchRecord,
                tuple[int, int] | None,
                tuple[str, ...],
            ]
        ] = []
        total = 0
        tagged_core_ids = load_tagged_word_ids(
            self.snapshot.database, options.tag_filters, status="accepted"
        )
        deprioritized_ids = self._deprioritized_tag_ids(options)
        sources: list[Iterable[SearchRecord]] = []
        if "core" in options.vocabulary_layers:
            sources.append(self._filtered(self.snapshot.records, options, tagged_core_ids))
        if auxiliary_records is not None:
            sources.append(self._filtered(auxiliary_records, options, tags_pre_filtered=True))
        try:
            for source in sources:
                for record in source:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise SearchTimedOut(self._timeout_message())
                    matched, span = matcher(record, remaining)
                    if matched:
                        total += 1
                        deprioritize_reasons = _deprioritize_reasons(
                            record, options, deprioritized_ids
                        )
                        insort(
                            top_matches,
                            (
                                (bool(deprioritize_reasons), *sort_key(record, options.sort_mode)),
                                record.id,
                                record,
                                span,
                                deprioritize_reasons,
                            ),
                        )
                        if len(top_matches) > options.limit:
                            top_matches.pop()
        except TimeoutError as exc:
            raise SearchTimedOut(self._timeout_message()) from exc
        finally:
            if auxiliary_records is not None:
                auxiliary_records.close()

        sorted_records = self._attach_tags([item[2] for item in top_matches])
        sort_explanations = tuple(
            explain_sort(record, options.sort_mode) for record in sorted_records
        )
        return SearchResponse(
            normalized_query=normalized_query,
            total=total,
            results=tuple(sorted_records),
            match_spans=tuple(item[3] for item in top_matches),
            sort_scores=tuple(item[0] for item in sort_explanations),
            sort_reasons=tuple(item[1] for item in sort_explanations),
            deprioritize_reasons=tuple(item[4] for item in top_matches),
            truncated=total > len(sorted_records),
            duration_ms=(time.monotonic() - started) * 1000,
            condition_description=condition_description,
        )

    def anagram_search(self, text: str, options: SearchOptions | None = None) -> SearchResponse:
        options = options or SearchOptions()
        started = time.monotonic()
        try:
            normalized = normalize_reading(text)
        except ValueError as exc:
            raise QueryValidationError(str(exc)) from exc
        self._validate_length(normalized)
        candidates = self.snapshot.anagrams.get(anagram_signature(normalized), ())
        auxiliary_records = self._auxiliary_records(
            options, signature=anagram_signature(normalized)
        )
        tagged_core_ids = load_tagged_word_ids(
            self.snapshot.database, options.tag_filters, status="accepted"
        )
        deprioritized_ids = self._deprioritized_tag_ids(options)
        sources: list[Iterable[SearchRecord]] = []
        if "core" in options.vocabulary_layers:
            sources.append(self._filtered(candidates, options, tagged_core_ids))
        if auxiliary_records is not None:
            sources.append(self._filtered(auxiliary_records, options, tags_pre_filtered=True))
        try:
            matches = [record for source in sources for record in source]
        finally:
            if auxiliary_records is not None:
                auxiliary_records.close()
        ranked_matches = [
            (
                record,
                _deprioritize_reasons(record, options, deprioritized_ids),
            )
            for record in matches
        ]
        ranked_matches.sort(
            key=lambda item: (
                bool(item[1]),
                *sort_key(item[0], options.sort_mode),
            )
        )
        selected = ranked_matches[: options.limit]
        sorted_records = self._attach_tags([item[0] for item in selected])
        sort_explanations = tuple(
            explain_sort(record, options.sort_mode) for record in sorted_records
        )
        return SearchResponse(
            normalized_query=normalized,
            total=len(matches),
            results=tuple(sorted_records),
            match_spans=tuple(None for _ in sorted_records),
            sort_scores=tuple(item[0] for item in sort_explanations),
            sort_reasons=tuple(item[1] for item in sort_explanations),
            deprioritize_reasons=tuple(item[1] for item in selected),
            truncated=len(matches) > len(sorted_records),
            duration_ms=(time.monotonic() - started) * 1000,
        )

    def _attach_tags(self, records: list[SearchRecord]) -> list[SearchRecord]:
        word_ids = [record.id for record in records]
        tags = load_tags(self.snapshot.database, word_ids)
        sources = load_sources(self.snapshot.database, word_ids)
        return [
            replace(
                record,
                tags=tags.get(record.id, record.tags),
                sources=sources.get(record.id, record.sources),
            )
            for record in records
        ]

    def _auxiliary_records(
        self,
        options: SearchOptions,
        *,
        normalized_query: str | None = None,
        match_type: MatchType | None = None,
        signature: str | None = None,
    ) -> Iterator[SearchRecord] | None:
        if (
            not options.include_proper
            or "auxiliary" not in options.vocabulary_layers
            or self.snapshot.auxiliary is None
        ):
            return None
        return self.snapshot.auxiliary.iter_records(
            normalized_query=normalized_query,
            match_type=match_type,
            signature=signature,
            options=options,
        )

    def _deprioritized_tag_ids(
        self, options: SearchOptions
    ) -> dict[str, set[int] | None]:
        return {
            status: load_tagged_word_ids(
                self.snapshot.database,
                options.deprioritize_tag_filters,
                status=status,
            )
            for status in ("accepted", "candidate")
        }

    def _validate_length(self, query: str) -> None:
        if len(query) > self.max_query_length:
            raise QueryValidationError(f"入力は{self.max_query_length}文字までです。")

    def _timeout_message(self) -> str:
        seconds = f"{self.timeout_seconds:g}"
        return f"検索処理を{seconds}秒で打ち切りました。条件を絞ってください。"

    @staticmethod
    def _filtered(
        records: Iterable[SearchRecord],
        options: SearchOptions,
        tagged_word_ids: set[int] | None = None,
        *,
        tags_pre_filtered: bool = False,
    ) -> Iterable[SearchRecord]:
        length_counter = (
            _length_counter(options) if options.reading_length is not None else None
        )
        for record in records:
            if tagged_word_ids is not None and record.id not in tagged_word_ids:
                continue
            if (
                not tags_pre_filtered
                and tagged_word_ids is None
                and options.tag_filters
                and not _record_matches_tags(record, options)
            ):
                continue
            if record.category == "proper" and not options.include_proper:
                continue
            if record.category == "function" and not options.include_function:
                continue
            if options.must_include and options.must_include not in record.normalized_reading:
                continue
            if options.must_exclude and options.must_exclude in record.normalized_reading:
                continue
            if (
                length_counter is not None
                and length_counter(record) != options.reading_length
            ):
                continue
            yield record


def _record_matches_tags(record: SearchRecord, options: SearchOptions) -> bool:
    available = {(tag.axis, tag.value) for tag in record.tags}
    return all(
        (tag_filter.axis, tag_filter.value) in available for tag_filter in options.tag_filters
    )


def _deprioritize_reasons(
    record: SearchRecord,
    options: SearchOptions,
    tagged_ids: dict[str, set[int] | None],
) -> tuple[str, ...]:
    reasons: list[str] = []
    layer = "auxiliary" if record.status == "candidate" else "core"
    if layer in options.deprioritize_vocabulary_layers:
        reasons.append("補助候補" if layer == "auxiliary" else "常駐語彙")

    if options.deprioritize_tag_filters:
        ids_for_status = tagged_ids[record.status]
        if ids_for_status is None:
            available = {(tag.axis, tag.value) for tag in record.tags}
            matches_tags = all(
                (tag.axis, tag.value) in available
                for tag in options.deprioritize_tag_filters
            )
        else:
            matches_tags = record.id in ids_for_status
        if matches_tags:
            reasons.extend(
                f"タグ {tag.axis}={tag.value}"
                for tag in options.deprioritize_tag_filters
            )
    return tuple(reasons)


def _length_counter(options: SearchOptions) -> Callable[[SearchRecord], int]:
    if options.length_unit == "surface":
        return lambda record: count_units(record.surface, "surface")
    if options.length_unit == "grid":
        grid_profile = resolve_grid_profile(options.grid_profile)
        return lambda record: count_normalized_reading_units(
            record.normalized_reading, "grid", grid_profile=grid_profile
        )
    reading_unit: ReadingUnit = options.length_unit
    return lambda record: count_normalized_reading_units(
        record.normalized_reading, reading_unit
    )


def _display_match_span(
    record: SearchRecord, span: tuple[int, int]
) -> tuple[int, int] | None:
    start, end = span
    if start == end:
        return None
    if len(record.reading) != len(record.normalized_reading):
        return None
    if normalize_text(record.reading) != record.normalized_reading:
        return None
    return span
