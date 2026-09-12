# Test strategy and coverage boundaries

Last reviewed: 2026-09-08. This describes test responsibilities, not a claim that all tests ran on this date.

## Test layers

| Layer | Responsibility | Entry points |
|---|---|---|
| Cipher specifications | Independent known vectors, key schedules, intermediate steps, invalid inputs | `tests/cipher/`, [behavior baseline](spec_baseline.md) |
| Cipher regression | Preserve established behavior across broad fixture inputs | `tests/cipher/test_regression_vectors.py`, `test_gear_called_vectors.py`, `test_enigma_purple_vectors.py`, `test_transposition_kakushi_vectors.py` in the same directory |
| Web contracts and catalog | Dispatch registration, response behavior, page discovery and rendering | `tests/web/test_gear_registry.py`, `test_gear_regression_vectors.py`, `test_http_api_smoke.py`, `test_tool_catalog.py` in the same directory |
| WordQuery core | Normalization, query semantics, lexicon construction, auditing and update lifecycle | `components/wordquery/tests/` |
| WordQuery integration | Flask/API/UI behavior, unavailable and stale states, release bundles and diagnostics | `tests/wordquery/` |
| Repository documentation | Public content boundaries, required document paths and ignore behavior | `tests/test_repository_readme.py`, `tests/test_repository_gitignore.py` |

The repository suite and WordQuery component suite are separate. Their responsibilities
are both required when a change crosses the application/component boundary.
A small test dictionary does not establish real-dictionary memory use or concurrent search performance.

## Acceptance and regression

Independent specification examples establish expected results. Implementation-generated
fixtures lock behavior but do not independently prove algorithm correctness.
Intentional behavior changes require rationale and aligned specification/tests; do not
regenerate fixtures merely to accept a failure. See the
[new-function checklist](new_crypto_function_checklist.md).

Cipher acceptance emphasizes Enigma, PURPLE, Vigenere, Affine, transposition,
Kakushi and SECOM. Encoding and analysis helpers also require boundary coverage;
DB-backed Passcode behavior needs tests at the appropriate data boundary.
SECOM tests include published and reference vectors, width interpretations,
intermediate traces and padding ambiguity. Double Columnar tests include all four
Standard/Disrupted combinations, duplicate and mixed keys, visible grids and errors.
Registry tests prevent non-handler functions from becoming dispatchable.

## Coverage limits

Fixture reachability is not comprehensive branch or response-contract coverage.
Some handlers still have few representative inputs. Broader malformed-input,
Unicode, boundary and response-schema checks should be justified by the change.
Existing fixture branches include empty railfence offset and number-conversion base,
password character-type variants and split-text separators.

HTTP smoke checks cover normal GET/POST requests, 404 handling, unknown/unregistered
handlers, missing keys and representative cipher pages. These do not establish a
complete response schema for every endpoint or replace browser rendering checks.
Do not infer current coverage percentages or passing totals from old audit counts.
Inspect the tests and report results for the revision actually checked.

WordQuery distinguishes structural candidate audits, independent human lexicon review,
automated search benchmarks and human usefulness observations. Success in one does
not imply success in the others. See [lexicon policy](wordquery/lexicon_policy.md).
