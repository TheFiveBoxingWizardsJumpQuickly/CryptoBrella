# Niantic Wiki Archive

This directory contains imported static archive artifacts hosted by CryptoBrella at `/niantic_wiki/`.

## Contents

- `site/`: imported static files served by the Flask app
- `import_manifest.json`: import metadata for the current snapshot

## Notes

- The archive artifacts are imported from a separately maintained Niantic Wiki project.
- Hosting-specific path normalization is applied during import so the archive can run under `/niantic_wiki/`.
