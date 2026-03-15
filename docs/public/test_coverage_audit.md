# Test Coverage Audit (Current State)

Last updated: 2026-03-16

## 1. Audit Scope
- Internal core functions called from `app/gear.py` request handlers
- API coverage for `/gear/<function>` and related HTTP paths
- Parameter branch reachability based on fixture values

## 2. Summary
- `app.gear` request handlers covered by web fixture: **44/44**
- Core functions reached through handler execution: **66/66**
- Flask HTTP smoke coverage exists in `tests/web/test_http_api_smoke.py`
  - basic GET/POST success paths
  - custom 404 page path
  - unknown-handler 500 path
  - missing-required-key 500 path

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

### 3.3 Input Diversity
- Several handlers still rely on one or few representative cases (for example `enigma_gen`, `purple_gen`, `vigenere_gen`, `columnar_gen`, `playfair_gen`).
- This is acceptable for baseline locking but limited for boundary exploration.

## 4. Interpretation
- For the current phase (clarifying present behavior), coverage is strong at reachability level.
- Next-phase hardening should focus on richer HTTP contract assertions and expanded boundary-case diversity.
