# CryptoBrella technical documentation

This index describes the architecture, supported tools, behavior, and test
strategy of CryptoBrella.

## System and application

- [System overview](public/system_overview.md): application structure and endpoint flow.
- [Specification baseline](public/spec_baseline.md): current implementation behavior.
- [Archive integration](public/archive_integration.md): separation and hosting of imported archive content.

## Crypto functions

- [Crypto function inventory](public/crypto_function_inventory.md): pages, APIs, inputs, and core functions.
- [New crypto function checklist](public/new_crypto_function_checklist.md): implementation and compatibility requirements for adding a tool.

## Testing

- [Test design matrix](public/test_design_matrix.md): test-layer responsibilities and goals.
- [Test coverage audit](public/test_coverage_audit.md): current coverage and identified hardening areas.

## WordQuery: JP

- [WordQuery documentation](public/wordquery/README.md): product scope and document index.
- [Architecture](public/wordquery/architecture.md): component and data boundaries.
- [Pattern search](public/wordquery/pattern_search.md): readable pattern grammar.
- [Lexicon policy](public/wordquery/lexicon_policy.md): inclusion and evidence rules.
- [Data sources and licenses](public/wordquery/data_sources.md): sources, transformations, and third-party terms.
