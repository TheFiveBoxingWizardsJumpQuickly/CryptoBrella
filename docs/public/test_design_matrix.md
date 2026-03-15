# Test Design Matrix

Last updated: 2026-03-16

## 1. Goals
- Layer 1: regression detection for Crypto Functions logic (known vectors, boundaries, exception behavior).
- Layer 2: web-handler behavior checks (response shape and main branches of `gear_*`).
- Layer 3: explicit spec tests for required behavior in `docs/public/spec_baseline.md`.

## 2. Priority Matrix

| Priority | Scope | Goal |
|---|---|---|
| P0 | `enigma`, `purple`, `vigenere`, `affine`, transposition, `kakushi` | Immediate detection of core logic breakage |
| P1 | `morse`, `braille`, `phonetic`, `polybius`, `bifid`, `vanity`, frequency utilities | Prevent regressions in surrounding crypto utilities |
| P2 | passcode DB-dependent features | Staged checks for external dependency paths |

## 3. Implemented Tests (Summary)

### Layer 1 (logic regression)
- `tests/cipher/test_regression_vectors.py`
  - `regression_vectors.json` (4405 cases)
- `tests/cipher/test_gear_called_vectors.py`
  - `gear_called_vectors.json` (725 cases)
- `tests/cipher/test_enigma_purple_vectors.py`
  - `enigma_purple_vectors.json` (1711 cases)
- `tests/cipher/test_transposition_kakushi_vectors.py`
  - `transposition_kakushi_vectors.json` (1116 cases)

### Layer 2 (web regression)
- `tests/web/test_gear_regression_vectors.py`
  - `gear_regression_vectors.json` (82 cases)
  - also validates fixture coverage of all request handlers
- `tests/web/test_http_api_smoke.py`
  - Flask `test_client` smoke checks for representative GET/POST, custom 404 behavior, and HTTP 500 paths

## 4. Constraints and Current Policy
- Large fixture baselines lock current behavior; intentional behavior changes require fixture regeneration.
- Fixture baselines do not replace explicit specification; P0 acceptance should converge to explicit spec tests.

## 5. Forward Plan
1. Add explicit P0 spec tests based on `docs/public/spec_baseline.md`.
2. Keep fixture baselines for not-yet-specified behavior and reduce them over time.
3. Expand HTTP-level smoke/integration coverage for key routes and representative error payloads.
4. Keep fixtures and public docs aligned with the currently supported feature set.
