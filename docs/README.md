# CryptoBrella Documentation Guide

This repository separates documentation into public/shareable documents and local-only operation notes.

## Read This First

- GitHub/public readers:
  - Use `docs/public/`.
- Local maintainers:
  - Start here, then read `docs/local/README.md` if that directory exists in your local checkout.

## Scope

- `docs/public/`
  - Git-tracked and GitHub-shared.
  - Holds implementation-aligned technical documents that are safe to publish.
- `docs/local/`
  - Local-only operational notes.
  - Not intended for GitHub publication.
  - Holds handover notes, backlog, decisions, risk logs, and session-operation documents.

## Public Documents

- `system_overview.md`: runtime structure and endpoint flow.
- `archive_integration.md`: how imported archive content is hosted under the Flask app.
- `spec_baseline.md`: current implementation behavior used as the baseline spec.
- `crypto_function_inventory.md`: page/API/function inventory.
- `test_design_matrix.md`: test-layer goals and forward test plan.
- `test_coverage_audit.md`: current coverage state and next hardening focus.

## Local Documents

Local-only guidance is defined by:

- `docs/local/documentation_scope_policy.md`
- `docs/local/development_policy.md`
- `docs/local/README.md`

Do not add links from `docs/public/` documents to `docs/local/` documents.
