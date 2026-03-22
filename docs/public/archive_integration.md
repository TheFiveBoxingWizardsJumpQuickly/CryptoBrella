# Archive Integration Notes

Last updated: 2026-03-22

## Scope
- CryptoBrella hosts an imported static archive of the Niantic Wiki under `/niantic_wiki/`.
- This archive is separate from the native CryptoBrella tool pages and APIs.

## Hosting Model
- Archive content is served from imported static artifacts stored under `app/niantic_wiki/`.
- Routing for the archive is isolated from the normal CryptoBrella page/template flow.
- Archive-specific paths are served under the `/niantic_wiki/` prefix.

## Operational Shape
- The imported archive remains distinct from native CryptoBrella templates, CSS, and JavaScript.
- Hosting-specific path normalization is applied so imported pages and assets resolve correctly under `/niantic_wiki/`.
- Archive-specific not-found routes use a dedicated Niantic Wiki-style 404 page rather than the main CryptoBrella 404 page.
