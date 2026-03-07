# Cipher Regression Baseline

`fixtures/regression_vectors.json` stores expected outputs generated from the current implementation.

- Purpose: detect behavioral regressions during refactors.
- Policy: this fixture is an explicit baseline; update it only when behavior changes are intentional.

## Regeneration

Regenerate only when intentionally updating cipher behavior:

```bash
.venv/bin/python tests/cipher/generate_regression_vectors.py
```
