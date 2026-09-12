# WordQuery: JP architecture

## Components

- `normalization`: strict storage normalization.
- `comparison`: search-only small/full-size kana equivalence.
- `units`: tokenization and counting for kana characters, morae, and written characters.
- `query`: conversion from task-specific inputs into a shared `SearchRequest` and search plan.
- `search`: Flask-independent services for reading matches, patterns, Regex, and anagrams.
- `sorting`: keys, scores, and explanations for user-selected result ordering.
- `repository`: loading search snapshots from SQLite.
- `lexicon`: merging external dictionaries and manual data into SQLite with provenance and validation results.
- `app/wordquery`: the application Blueprint, three-mode UI, and JSON boundary.

`units` provides one API for kana, mora, and written-character units. `query`
validates the current `SearchRequest` and serializes its effective conditions.
Search requests use version 7 and readable patterns use `mode=pattern`, which
converts validated tokens into a safe predicate over the complete reading.
`repository` expands `accepted` entries into the resident snapshot and fetches
`candidate` entries on demand from the auxiliary SQLite layer. Vocabulary tags
and their evidence remain in SQLite and are attached only to top results after
searching.

`sorting` implements commonness, dictionary priority, and normalized-reading
order. Commonness is a provisional signal based only on dictionary priority
and corroboration across sources; it is neither observed usage frequency nor a
recommendation. Data status, word type, and domain remain separate attributes
and do not implicitly reduce commonness. Search conditions select resident and
auxiliary vocabulary layers independently of categories and applies tag
axis/value conditions with AND semantics. Auxiliary-layer tag conditions are
passed to SQLite so nonmatching candidates are not expanded into Python.
Vocabulary-layer and tag deprioritization apply as separate ranking
groups while preserving the selected sort within each group.

The application Blueprint converts three Japanese UI tabs—`パターン`,
`アナグラム`, and `Regex`—into the shared API.
Search state is kept only within the page and is not persisted in the browser
URL.

## Data flow

```text
external dictionaries + data/manual + source manifest
                  │
                  ▼
        import → normalize → validate
                  │
                  ▼
      merge/provenance → SQLite + report
                  │
                  ▼
       indexed lexicon + vocabulary layers
                  │
                  ▼
       SearchRequest → search plan
          ├─ unit/token predicate
          ├─ Regex scan with timeout
          ├─ anagram/frequency index
          └─ vocabulary/tag filters
                  │
                  ▼
       sort + reason + grouped results
                  │
                  ▼
       Flask purpose-specific UI/API
```

The generated SQLite database is a build artifact, not source data. A fast,
primarily general-vocabulary `accepted` layer stays resident, while a
`candidate` auxiliary layer serves proper-name and Sudachi-only ASCII-headword
candidates on demand. The
application never expands every candidate into resident memory unconditionally.
The Flask layer is limited to translating task-oriented input into shared
conditions and presenting results, preserving a one-way dependency from the
application boundary to the search core.

Readable patterns are compiled into safe expressions over kana characters;
selected length units are additional filters. Small-kana equivalence expands
literal and set matches without changing stored readings. Prefilters retain
only necessary conditions that cannot discard equivalent matches.

## Search API

All UI and operational callers use `POST /wordquery/api/search` with integer
`version: 7`, `mode` (`reading`, `pattern`, `regex`, or `anagram`), and a string
`query`. Reading mode accepts `match_type`: `contains` (default), `prefix`,
`suffix`, or `exact`. Regex is selected by its own mode.

Optional shared conditions include `length`, `length_unit` (`kana`, `mora`,
`surface`), `must_include`, `must_exclude`, category flags, vocabulary layers,
tag filters, sorting, deprioritization, and result limit. Defaults are
`length_unit: kana`, `sort: commonness`, vocabulary layer `core`, and false
category flags. `fold_small_kana` defaults to false and enables small/full-size
kana equivalence in reading and pattern searches. The response includes the
effective request. See [pattern search](pattern_search.md) for matching rules.

## Error boundaries

- Syntax and input errors map to HTTP 400, search timeouts to 408, and rate-limit failures to 429.
- A missing or corrupt lexicon makes the search page and API return a service-unavailable state.
- An invalid dictionary row is recorded as a build error or quality-report finding rather than silently discarded.

## Reviewed snapshots

A deployment may explicitly select a pinned reviewed snapshot. Its adjacent
release manifest must record a passing formal human gate and match the database
byte hash and input hash. The application verifies these at startup and makes
search unavailable if verification fails. This mode serves an evaluated version
without treating human-review evidence as proof of upstream freshness. Both reviewed and updated public modes enforce source freshness on requests.
Approval of a reviewed snapshot does not exempt it from that check. Switching modes is an operator choice; preparing
a release bundle does not activate it.
