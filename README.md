# CryptoBrella

Flask-based crypto utility application with regression tests for cipher and web handler behavior.

## Documentation

Start with `docs/README.md`.

- Public/shareable technical docs live in `docs/public/`.
- Local-only operation and handover docs live in `docs/local/` and are intentionally not pushed to GitHub.
- If you are working locally, read `docs/local/README.md` first when it exists.

## Development Environment

Use the project virtual environment for all local commands.

```bash
source .venv/bin/activate
```

If you do not want to activate the shell environment, call tools through `.venv/bin/...` directly.

Examples:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python run_dev.py
```

## Notes

- The system Python on this machine may not have required packages such as `Pillow`.
- Test and app verification should be run with the interpreter from `.venv`.
