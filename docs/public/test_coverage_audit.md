# Test Coverage Audit (Current State)

Last updated: 2026-08-22

## 1. Audit Scope
- Internal core functions called from `app/gear.py` request handlers
- API coverage for `/gear/<function>` and related HTTP paths
- Parameter branch reachability based on fixture values

## 2. Summary
- Registered `app.gear` request handlers covered by web fixture: **44/44**
- Previously audited core functions remain covered; Double Columnar adds
  explicit parser, encode, and decode coverage.
- Registry structure coverage confirms that every request handler is registered
  and that non-handler module functions are not dispatchable.
- Flask HTTP smoke coverage exists in `tests/web/test_http_api_smoke.py`
  - basic GET/POST success paths
  - custom 404 page path
  - unknown-handler 500 path
  - unregistered module-function 500 path
  - missing-required-key 500 path
  - SECOM published-vector success path, result-only default responses, and
    detailed Encode/Decode response paths
  - Double Columnar page, catalog/icon discovery, known-vector API response,
    and invalid-input response

## 3. Remaining Gaps

### 3.1 HTTP Layer Depth
- `test_client` coverage is currently smoke-level.
- Full response-contract checks (payload schema/content-type/error body details) are not yet comprehensive for all endpoints.

### 3.2 Branch Reachability Status
- Previously missing branches were added and are now covered in fixture execution:
  - `railfence_gen`: `offset == ""`
  - `number_conv_gen`: `base == ""`
  - `pwgen_gen`: `char_type` range `0..8`
  - `split_text_gen`: `mode` values `space/comma/newline`
- SECOM onboarding adds explicit published and Java-reference vectors,
  width-interpretation, intermediate-trace, round-trip, invalid-input,
  registry, page-rendering, and HTTP success coverage.
- Double Columnar onboarding adds an independent published vector, all four
  Standard/Disrupted combinations, round trips, mixed and duplicate key
  ranking, visible grids, invalid input, registry, page, catalog, icon, and
  HTTP coverage.

### 3.3 Input Diversity
- Several handlers still rely on one or few representative cases (for example `enigma_gen`, `purple_gen`, `vigenere_gen`, `columnar_gen`, `playfair_gen`).
- This is acceptable for baseline locking but limited for boundary exploration.

## 4. Interpretation
- For the current phase (clarifying present behavior), coverage is strong at reachability level.
- Next-phase hardening should focus on richer HTTP contract assertions and expanded boundary-case diversity.
