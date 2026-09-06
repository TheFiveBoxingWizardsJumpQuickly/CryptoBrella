# WordQuery: JP architecture

## Components

- `normalization`: strict storage normalization and search-time comparison profiles.
- `units`: tokenization and counting for kana characters, morae, and written characters.
- `query`: conversion from task-specific inputs into a shared `SearchRequest` and search plan.
- `search`: Flask-independent services for reading matches, patterns, Regex, and anagrams.
- `sorting`: keys, scores, and explanations for user-selected result ordering.
- `repository`: loading search snapshots from SQLite.
- `lexicon`: merging external dictionaries and manual data into SQLite with provenance and validation results.
- `app/wordquery`: the application Blueprint, three-mode UI, and JSON boundary.

`units` provides one API for kana, mora, and written-character units. `query`
validates versioned `SearchRequest` objects and provides a stable JSON
representation. Request version 5
represents readable patterns separately from Regex as `mode=pattern` and
converts validated tokens into a safe predicate over the complete reading.
`repository` expands `accepted` entries into the resident snapshot and fetches
`candidate` entries on demand from the auxiliary SQLite layer. Vocabulary tags
and their evidence remain in SQLite and are attached only to top results after
searching.

`sorting` implements commonness, dictionary priority, and normalized-reading
order. Commonness is a provisional signal based only on dictionary priority
and corroboration across sources; it is neither observed usage frequency nor a
recommendation. Data status, word type, and domain remain separate attributes
and do not implicitly reduce commonness. Request version 3 selects resident and
auxiliary vocabulary layers independently of categories and applies tag
axis/value conditions with AND semantics. Auxiliary-layer tag conditions are
passed to SQLite so nonmatching candidates are not expanded into Python.
Version 4 applies vocabulary-layer and tag deprioritization as separate ranking
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

Readable-pattern conditions are represented as token predicates over the
selected search unit. A condition may be optimized to Regex when it is
equivalent in single-kana-character units. API search conditions carry an
explicit schema version.

## Error boundaries

- Syntax and input errors map to HTTP 400, search timeouts to 408, and rate-limit failures to 429.
- A missing or corrupt lexicon makes the search page and API return a service-unavailable state.
- An invalid dictionary row is recorded as a build error or quality-report finding rather than silently discarded.
