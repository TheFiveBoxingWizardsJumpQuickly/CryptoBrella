# Crypto Function Inventory

Last updated: 2026-03-28

## 1. Management Term
- This project manages cipher transforms, analysis utilities, and encoding helpers under one term: **Crypto Functions**.
- Utility pages previously treated as "Other Tools" are included in the same management scope.

## 2. Top-Page Counts
- Managed pages: 39
- `gear/<function>` based pages: 36
- Non-`gear` API page: 1 (`/resize` -> `POST /g/resize/`)
- Client-only page: 1 (`/memo`)
- Top-page organization is metadata-driven from `app/tool_catalog.py`.
- Current top-page groups are: `Cryptography`, `Encoding`, `Utility`, `Remember Ingress`, `Extra`.

## 3. Inventory (Page -> API -> Inputs -> Internal Functions)

| Category | Page | API | Request keys | Internal core functions (signature) |
|---|---|---|---|---|
| Substitution ciphers | `rot` | `rot_gen` | `input_text` | `rot(c, k, nc=False)` |
| Substitution ciphers | `vigenere` | `vigenere_gen` | `input_text`, `key` | `vig_d(c, k, nc=False)`, `vig_e(c, k, nc=False)`, `beaufort(c, k, nc=False)`, `vig_d_auto(c, k, nc=False)`, `vig_e_auto(c, k, nc=False)` |
| Substitution ciphers | `simplesub` | `simplesub_gen` | `input_text` | `table_subtitution(text, method)` |
| Substitution ciphers | `affine` | `affine_gen` | `input_text`, `mode` | `affine_d(text, a, b)`, `affine_e(text, a, b)` |
| Substitution ciphers | `polybius` | `polybius_gen` | `input_text`, `mode` | `polybius_d(text, table_keyword='')`, `polybius_e(text, table_keyword='')` |
| Substitution ciphers | `playfair` | `playfair_gen` | `input_text` | `playfair_d(c)`, `playfair_e(c)` |
| Substitution ciphers | `bifid` | `bifid_gen` | `input_text`, `key` | `bifid_d(text, table_keyword='')`, `bifid_e(text, table_keyword='')`, `mixed_alphabet(keyword, combined=False)` |
| Substitution ciphers | `purple` | `purple_gen` | `input_text`, `plugboard_full`, `sixes_switch_position`, `twenties_switch_1_position`, `twenties_switch_2_position`, `twenties_switch_3_position`, `rotor_motion_key` | `purple_decode(...)`, `purple_encode(...)` |
| Substitution ciphers | `enigma` | `enigma_gen` | `input_text`, `left_rotor`, `mid_rotor`, `right_rotor`, `reflector`, `rotor_key`, `ring_key`, `plug_board` | `plugboard_gen(txt)`, `enigma(text, rotor_left_id, rotor_mid_id, rotor_right_id, reflector_id, rotor_key, ringsetting_key, plugboard)` |
| Transposition ciphers | `reverse` | `reverse_gen` | `input_text` | `rev(c)` |
| Transposition ciphers | `rectangle` | `rectangle_gen` | `input_text`, `mode` | `rect(text, col)` |
| Transposition ciphers | `railfence` | `railfence_gen` | `input_text`, `mode`, `offset` | `railfence_d(text, rails, offset=0)`, `railfence_e(text, rails, offset=0)` |
| Transposition ciphers | `columnar` | `columnar_gen` | `input_text`, `key` | `assign_digits(x)`, `columnar_d(c, col)`, `columnar_e(c, col)` |
| Transposition ciphers | `skip` | `skip_gen` | `input_text`, `mode` | `skip_d(text, step)`, `skip_e(text, step)` |
| Transposition ciphers | `swap_xy` | `swap_xy_gen` | `input_text` | `swap_xy_axes(text)` |
| Encodings | `base64` | `base64_gen` | `input_text`, `mode` | `uu_decode(text)`, `uu_encode(byte)` + Python `base64` stdlib |
| Encodings | `morse` | `morse_gen` | `input_text`, `mode` | `morse_d(...)`, `morse_e(...)`, `morse_wabun_d(...)`, `morse_wabun_e(...)` |
| Encodings | `charcode` | `charcode_gen` | `input_text`, `mode`, `base` | `base_a_to_base_b_onenumber(n, a, b)`, `char_to_codepoint(...)`, `codepoint_to_char(...)`, `valid_chars_for_base_n(n)` |
| Encodings | `braille` | `braille_gen` | `b1`, `b2`, `b3`, `b4`, `b5`, `b6` | `braille_d(braille_dots)` |
| Encodings | `braille_ja` | `braille_ja_gen` | `bl1`, `bl2`, `bl3`, `bl4`, `bl5`, `bl6`, `br1`, `br2`, `br3`, `br4`, `br5`, `br6` | `braille_ja_d(braille_dots)` |
| Encodings | `phonetic` | `phonetic_gen` | `input_text`, `mode` | `phonetic_alphabet_d(text, dic)`, `phonetic_alphabet_e(text, dic)`, `return_phonetic_alphabet_values(dic)` |
| Encodings | `vanity` | `vanity_gen` | `input_text`, `mode` | `vanity_d(text, style)`, `vanity_e(text, style)`, `auto_split_number_string(text, pattern)` |
| Encodings | `kakushi` | `kakushi_gen` | `input_text`, `key`, `mode`, `debug_mode` | `kakushi_encode(text: str, keyword: str, debug: bool=True)`, `kakushi_decode(encoded: str, keyword: str, debug: bool=False)` |
| Crypto utilities | `frequency` | `frequency_gen` | `input_text` | `letter_frequency(text, sortkey=0, reverse_flag=False)`, `unique(text, sort=False)` |
| Crypto utilities | `hash` | `hash_gen` | `input_text` | `hashlib.md5/sha1/sha224/sha256/sha384/sha512/blake2b/blake2s` |
| Crypto utilities | `prime` | `prime_gen` | `input_text` | `extract_integer_only(text)`, `factorize(num)` |
| Crypto utilities | `pwgen` | `pwgen_gen` | `char_type`, `length` | `password_generate(length, table)` |
| Crypto utilities | `charreplace` | `charreplace_gen` | `input_text`, `replace_from`, `replace_to` | `unique(text, sort=False)`, `replace_all(text, table_from, table_to)` |
| Crypto utilities | `resize` | `POST /g/resize/` | multipart: `image`, `img_width`, `img_height`, `bgcolor`, `output_name` | `resize_image(...)` |
| Crypto utilities | `rsa` | `rsa_gen` | `m`, `e`, `n`, `p`, `q` | `rsa_encode(m, e, n)`, `rsa_decode(c, e, n, p, q)` |
| Crypto utilities | `split_text` | `split_text_gen` | `input_text`, `length`, `mode` | `text_split(text, step, sep=' ')` |
| Crypto utilities | `number_conv` | `number_conv_gen` | `input_text`, `base` | `base_a_to_base_b(nlist, a, b)` |
| Crypto utilities | `riddle_tables` | `riddle_tables_gen` | `mode` | `return_japan_traditional_month_names_list()`, `return_zodiac_list()`, `return_japanese_zodiac_list()` |
| Crypto utilities | `memo` | client-only | none | browser-only behavior |
| Remember Ingress | `rot_ex` | `rot_ex_gen` | `input_text`, `mode` | `rot(c, k, nc=False)`, `atbash(c, nc=False)` |
| Remember Ingress | `vigenere_ex` | `vigenere_ex_gen` | `input_text`, `key` | `vig_d(...)`, `vig_e(...)`, `beaufort(...)`, `vig_d_auto(...)`, `vig_e_auto(...)` |
| Remember Ingress | `rectangle_ex` | `rectangle_ex_gen` | `input_text`, `mode`, `mode_ex` | `rect(text, col)`, `rect_reverse_even(text, col)` |
| Remember Ingress | `charcode_ex` | `charcode_ex_gen` | `input_text` | `auto_split_number_string(text, pattern)`, `base_a_to_base_b_onenumber(n, a, b)` |
| Remember Ingress | `ingress_keywords` | `ingress_keywords_gen` | `pattern` | `passcode_get_filtered_keywords(pattern)` |

## 4. Notes
- `challenge`, `passcode`, `about`, `link`, and `niantic_wiki` are top-page entries but excluded from this inventory because they are not crypto transform APIs.
- The top page also provides in-page search over tool `name`, `aliases`, and `tags`.
