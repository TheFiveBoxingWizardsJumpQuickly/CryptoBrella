# CryptoBrella Baseline Specification

Last updated: 2026-08-01

## 1. Purpose and Scope
- This document captures current implementation behavior as the baseline specification.
- Scope covers Web/API contracts in `app/app.py` and `app/gear.py`, with focus on P0 functions.
- Passcode DB internals are documented separately.

## 2. Common Contract for `/gear/<function>`
- Method: `POST` only.
- Request body: JSON expected.
- Handlers access payload fields directly via `request.json[...]`.
- Missing required keys currently raise uncaught exceptions (for example `KeyError`) and return HTTP 500.
- Dispatcher: `app/app.py:cipher_gear` resolves handlers through the explicit
  `app.gear.GEAR_HANDLERS` registry via `get_gear_handler(function)`.
- Only the 43 registered request handlers are dispatchable; other functions in
  `app.gear` are not exposed through `/gear/<function>`.
- Unknown or unregistered handler names currently raise `KeyError` and return HTTP 500.
- Response type:
  - Most handlers return `dict[int, str]` (Flask JSON serialization stringifies keys).
  - Some handlers return plain strings (for example `passcode_validate`).

## 2.1 Top Page (`/`)
- The home page renders a metadata-driven tool catalog from `app/tool_catalog.py`.
- In-page search filters tools client-side using `name`, `aliases`, and `tags`.
- If search yields no visible tools, the page shows `No matches`.
- Pressing `Enter` in the search field opens the first visible result in a new tab.

## 2.2 Not-Found Pages
- Missing pages return HTTP 404 through a shared custom 404 page.
- This applies to general missing routes and to missing `challenge` / `cipher_docs` pages.

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

### 3.7 SECOM (`secom_gen`)
- Inputs: `input_text`, `key`, `mode` (`Decode`/`Encode`), `detail_mode`
  (`ON`/`OFF`, omitted values default to `OFF`)
- Key normalization:
  - removes non-letters and uppercases
  - uses the first 20 letters
  - rejects keys containing fewer than 20 letters
- Encode:
  - accepts letters A-Z, digits, and whitespace
  - represents whitespace with the SECOM checkerboard space marker
  - applies the extended straddling checkerboard, normal columnar
    transposition, and disrupted columnar transposition
  - pads the digit stream with zeroes to a multiple of five and returns
    five-digit groups
- Transposition-width variants:
  - the internal cipher API accepts `width_mode="reset_each_width"` (default)
    or `width_mode="continue_across_widths"`
  - `reset_each_width` clears duplicate tracking before calculating each
    width; it is the default to provide interoperability with the referenced
    Java implementation
  - `continue_across_widths` retains duplicate tracking across both widths;
    it preserves the other plausible reading of "continue" in the published
    specification
  - both modes continue scanning digits from the point where the preceding
    width ended
  - the web UI does not expose this choice yet and therefore uses
    `reset_each_width`
- Decode:
  - accepts digits and whitespace; the digit count must be a multiple of five
  - restores checkerboard space markers as spaces in the handler response
  - warns that null padding can yield up to four ambiguous trailing characters
- Handler result messages:
  - `detail_mode == OFF` returns only `SECOM Encode:`/`SECOM Decode:` and the
    transformed text; it does not return a Note
  - `detail_mode == ON` additionally returns the normalized inputs, key halves
    and rankings, chain-addition seed, generated digits, checkerboard details,
    width calculations, transposition keys, padding information, and the
    intermediate outputs of each forward or reverse transposition
  - detailed steps are separated by blank lines for visual verification; the
    internal width-mode identifier is intentionally not displayed
  - a blank line separates the transformed result from `Detailed steps:`
  - Encode terminology and grouping follow the published four-step
    explanation: calculating key phrase digits, the straddling checkerboard,
    the first columnar transposition, and the second disrupted columnar
    transposition; Decode presents the transpositions in reverse order
  - successful detailed Decode ends with `Note: SECOM null padding can produce
    up to four ambiguous trailing characters.` Ciphertext alone does not reveal
    whether zero padding was added
  - detailed Encode does not return the padding Note because the exact padding
    count is included in its intermediate steps
  - invalid input returns an `Error: ...` result instead of the success heading
    and Note
- Invalid SECOM values return an error message in the normal result dictionary.

#### Specification rationale and references

- Published specification and worked example:
  https://www.ciphermachinesandcryptology.com/en/secom.htm
- Java reference implementation:
  https://github.com/asilichenko/secom-cipher-gui#the-secom-cipher
- The published example produces widths 12 and 11 without repeating a digit
  across the boundary, so it cannot determine whether duplicate tracking must
  reset for the second width. Both interpretations remain available internally.
- The default intentionally follows the Java interpretation so CryptoBrella can
  reproduce its additional test vector. The mode names describe behavior and
  do not identify an implementation.
- Disrupted transposition uses triangular-cell masks through a partial final
  row. This follows the published instruction to fill non-triangular cells
  first and triangular cells second while leaving unavailable trailing cells
  empty.
- Detailed labels and blocks intentionally follow the terminology and worked
  layout of the published specification rather than internal function or
  variable names.

## 4. Test Synchronization Rule
- Baseline fixtures lock current behavior.
- When intentional behavior changes are made, update in this order:
  1. `docs/public/spec_baseline.md`
  2. explicit spec tests
  3. regenerated baseline fixtures
