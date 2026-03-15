# CryptoBrella Baseline Specification

Last updated: 2026-03-15

## 1. Purpose and Scope
- This document captures current implementation behavior as the baseline specification.
- Scope covers Web/API contracts in `app/app.py` and `app/gear.py`, with focus on P0 functions.
- Passcode DB internals are documented separately.

## 2. Common Contract for `/gear/<function>`
- Method: `POST` only.
- Request body: JSON expected.
- Handlers access payload fields directly via `request.json[...]`.
- Missing required keys currently raise uncaught exceptions (for example `KeyError`) and return HTTP 500.
- Dispatcher: `app/app.py:cipher_gear` resolves handlers via `gear.gear_globals()[function]`.
- Unknown handler names currently raise `KeyError` and return HTTP 500.
- Response type:
  - Most handlers return `dict[int, str]` (Flask JSON serialization stringifies keys).
  - Some handlers return plain strings (for example `passcode_validate`).

## 3. Input Normalization Rules (P0)

### 3.1 Vigenere (`vigenere_gen`)
- Inputs: `input_text`, `key`
- Normalization: key removes `[^a-zA-Z0-9]`.
- Output: one block with Text/Key/Decoded/Encoded/Beaufort/Auto-key Decoded/Auto-key Encoded.
- Known current behavior: if normalized key is empty, an uncaught `IndexError` occurs.

### 3.2 Enigma (`enigma_gen`)
- Inputs: `input_text`, `left_rotor`, `mid_rotor`, `right_rotor`, `reflector`, `rotor_key`, `ring_key`, `plug_board`
- Normalization:
  - `input_text` uppercased.
  - `rotor_key` and `ring_key` keep letters only, uppercase, and are right-padded to length 3 with `A`.
  - `plug_board` normalized by `plugboard_gen`.
- Output:
  - `results[0]`: settings summary.
  - `results[1]`: Enigma output.

### 3.3 Purple (`purple_gen`)
- Inputs: `input_text`, `sixes_switch_position`, `twenties_switch_1_position`, `twenties_switch_2_position`, `twenties_switch_3_position`, `plugboard_full`, `rotor_motion_key`
- Normalization:
  - `input_text` uppercased.
  - `plugboard_full` keeps letters only and uppercases.
  - switch positions and `rotor_motion_key` are converted with `int()`.
- Output includes both decode and encode results.

### 3.4 Affine (`affine_gen`)
- Inputs: `input_text`, `mode` (`Decode` or `Encode`)
- Behavior:
  - Fixed `a` set: `1,3,5,7,9,11,15,17,19,21,23,25`
  - `b` iterates `0..25`
  - Returns all 312 combinations.

### 3.5 Transposition (`railfence_gen`, `columnar_gen`, `skip_gen`, `swap_xy_gen`)
- `railfence_gen`:
  - `offset == ""` treated as `0`.
  - rail count iterates `2..min(len(input_text), 100)-1`.
- `columnar_gen`:
  - decode/encode computed from `assign_digits(key)`.
- `skip_gen`:
  - step iterates `2..min(len(input_text), 100)-1`.
- `swap_xy_gen`:
  - returns one-shot `swap_xy_axes(input_text)` result.

### 3.6 Kakushi (`kakushi_gen`)
- Inputs: `input_text`, `key`, `mode` (`Decode`/`Encode`), `debug_mode` (`ON`/`OFF`)
- Behavior:
  - `debug_mode == OFF`: returns result text only.
  - `debug_mode == ON`: returns detailed blocks including binary intermediates.

## 4. Test Synchronization Rule
- Baseline fixtures lock current behavior.
- When intentional behavior changes are made, update in this order:
  1. `docs/public/spec_baseline.md`
  2. explicit spec tests
  3. regenerated baseline fixtures
