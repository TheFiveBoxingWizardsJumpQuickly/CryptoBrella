# CryptoBrella System Overview

Last updated: 2026-09-08

## 1. System Summary
- CryptoBrella is a Flask-based Crypto Functions service.
- Core logic lives in pure functions under `app/cipher/*`.
- Web request/response handling is implemented in `app/gear.py`.
- Top-page catalog metadata is managed in `app/tool_catalog.py`.
- Imported Niantic Wiki archive content is hosted under `app/niantic_wiki/`.
- UI pages under `app/templates/Tools/*.html` call `POST /gear/<function>`.

## 2. Runtime Flow
1. Open the top page `/` or a Crypto Functions page such as `/rot` or `/enigma`.
2. On `/`, the top-page catalog is rendered from metadata in `app/tool_catalog.py` and filtered client-side by in-page search.
3. Tool pages post JSON payloads to `POST /gear/<xxx_gen>`.
4. `app/app.py:cipher_gear` resolves the requested name from the explicit
   `app.gear.GEAR_HANDLERS` registry and invokes the registered handler.
5. `app/gear.py` calls core functions in `app/cipher/*` and returns formatted results.

## 3. Main Modules
- Routing and page rendering: `app/app.py`
- Niantic Wiki archive routing: `app/niantic_wiki/__init__.py`
- Crypto Functions API handlers: `app/gear.py`
- Compatibility exports for cipher/encoding functions: `app/cipher/fn.py`
- Function implementations: dedicated modules under `app/cipher/`; shared mathematics in `math_functions.py` and RSA-specific operations in `rsa.py`
- Shared math helpers for cipher modules: `app/cipher/math_functions.py`
- Transposition logic: `app/cipher/transposition.py`
- Enigma implementation: `app/cipher/enigma.py`
- Purple implementation: `app/cipher/purple.py`
- Kakushi implementation: `app/cipher/kakushi.py`
- SECOM implementation: `app/cipher/secom.py`
- Passcode/DB access: `app/cipher/ingress_passcode.py`
- Top-page metadata/catalog: `app/tool_catalog.py`

## 4. Endpoint Categories
- Pages: `/`, `/<page>`, `/about`, `/challenge/*`, `/passcode/*`, `/cipher_docs/*`, `/niantic_wiki/*`
- Crypto Functions API: `POST /gear/<function>`
- Image API: `POST /g/resize/`, `GET /upload/`, `GET /modified_image/`

## 5. Not-Found Handling
- Missing general pages and missing `challenge` / `cipher_docs` pages resolve to a shared custom 404 page.
- The 404 page returns HTTP 404 explicitly and includes a simple route back to the top page.
- Missing `niantic_wiki` pages and assets use a dedicated Niantic Wiki-themed 404 page that links back to `/niantic_wiki/page/start.html`.

## 6. WordQuery integration

WordQuery is part of this application. `app/app.py` registers its Blueprint;
`component_paths.py` locates the checked-out component source.

- `components/wordquery/src/wordquery_jp/` owns Flask-independent normalization,
  query/search services, lexicon construction, quality checks and the update CLI.
- `app/wordquery/` owns Flask configuration, request translation, rate limits,
  source pages and responses. UI assets live in `app/templates/wordquery/` and
  `app/static/wordquery/`.
- `/wordquery/` exposes patterns, exact anagrams and Regex. Search requests use
  the Blueprint JSON endpoints rather than the `/gear/<function>` registry.
- External dictionaries and justified manual inputs produce a versioned SQLite
  lexicon and search indexes. Generated databases are separate from source code.
- The application depends on the search component; the component does not depend
  on Flask. Dictionary construction is separate from serving requests.

See [WordQuery architecture](wordquery/architecture.md) for data flow and
[testing](testing.md) for the separate core and application test layers.

## 7. Ownership boundaries

`app/cipher/fn.py` preserves compatibility exports while dedicated modules own
algorithm implementations. Shared mathematical helpers belong in
`app/cipher/math_functions.py`; RSA functions consume those helpers.
Catalog metadata defines discoverability; it does not grant API dispatch access.
Passcode uses its own SQLite-backed functions. Cipher explanation text is loaded
by `app/cipher_docs/` and rendered through its template.
The Niantic Wiki tree contains imported artifacts; its integration boundary is
specified in [archive integration](archive_integration.md).
