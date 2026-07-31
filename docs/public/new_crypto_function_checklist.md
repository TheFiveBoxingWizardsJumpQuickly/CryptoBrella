# New Crypto Function Onboarding Checklist

Last updated: 2026-07-31

Use this checklist when shipping a new user-facing Crypto Function. Complete
the applicable items in the same development cycle.

## 1. Specification and Scope

- Identify a reliable algorithm specification and at least one independent
  worked example or known vector when available.
- Record supported characters, key rules, normalization, padding, and any
  inherently ambiguous output.
- Decide whether invalid input is rejected, normalized, or preserved.
- Keep the core transform deterministic and independent from Flask.

## 2. Core Implementation

- Put cipher logic in a focused module under `app/cipher/`.
- Export supported public functions through `app/cipher/fn.py` when they belong
  to the shared cipher facade.
- Add explicit known-vector, round-trip, boundary, and invalid-input tests.
- Do not generate regression expectations from the implementation until an
  independently derived expected result is pinned first.

## 3. Web Integration

- Add a request handler to `app/gear.py` with an explicit request and response contract.
- Register the handler in `app.gear.GEAR_HANDLERS`.
- Add the tool template under `app/templates/Tools/`.
- Add tool metadata, category placement, aliases, tags, path, and icon in
  `app/tool_catalog.py`.
- Add HTTP checks for the page, successful API behavior, and important invalid input.

## 4. Regression Fixtures

- Add representative handler cases to the appropriate fixture generator.
- Regenerate only the affected fixtures.
- Review generated differences separately from independent specification tests.
- Confirm the fixture covers the new registered handler.

## 5. User and Technical Documentation

- Add or update `app/cipher_docs/` user guidance when the algorithm needs explanation.
- Update `docs/public/crypto_function_inventory.md`.
- Update `docs/public/spec_baseline.md` for the new request/response behavior.
- Update test design and coverage documents when counts or supported scope change.
- Add a user-visible release entry to `app/templates/about.html`.

## 6. Completion Gate

- Run focused core and web tests.
- Run the full pytest suite.
- Confirm the page manually when presentation or interaction changed.
- Run `git diff --check` and review all generated artifacts.
- Update the local dashboard, backlog, development log, and handover notes.

## First Validated Use

SECOM was the first feature onboarded with this checklist. Its acceptance test
uses Dirk Rijmenants' published key schedule and complete encryption example,
then separately covers round trips and invalid inputs.
