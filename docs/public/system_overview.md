# CryptoBrella System Overview

Last updated: 2026-03-07

## 1. System Summary
- CryptoBrella is a Flask-based Crypto Functions service.
- Core logic lives in pure functions under `app/cipher/*`.
- Web request/response handling is implemented in `app/gear.py`.
- UI pages under `app/templates/Tools/*.html` call `POST /gear/<function>`.

## 2. Runtime Flow
1. Open a Crypto Functions page such as `/rot` or `/enigma`.
2. Page JavaScript posts JSON payloads to `POST /gear/<xxx_gen>`.
3. `app/app.py:cipher_gear` dispatches via `gear.gear_globals()[function](request)`.
4. `app/gear.py` calls core functions in `app/cipher/*` and returns formatted results.

## 3. Main Modules
- Routing and page rendering: `app/app.py`
- Crypto Functions API handlers: `app/gear.py`
- General cipher/encoding logic: `app/cipher/fn.py`
- Shared math helpers for cipher modules: `app/cipher/math_functions.py`
- Transposition logic: `app/cipher/transposition.py`
- Enigma implementation: `app/cipher/enigma.py`
- Purple implementation: `app/cipher/purple.py`
- Kakushi implementation: `app/cipher/kakushi.py`
- Passcode/DB access: `app/cipher/ingress_passcode.py`
- LINE webhook blueprint: `app/line_bot_blueprint.py`

## 4. Endpoint Categories
- Pages: `/`, `/<page>`, `/about`, `/challenge/*`, `/passcode/*`, `/prosaic/*`
- Crypto Functions API: `POST /gear/<function>`
- Image API: `POST /g/resize/`, `GET /upload/`, `GET /modified_image/`
- Webhook API: `POST /line/webhook`
