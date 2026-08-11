# CryptoBrella

Flask-based crypto utility application with regression tests for cipher and web handler behavior.

## Documentation

Start with `docs/README.md`.

- Public/shareable technical docs live in `docs/public/`.
- Local-only operation and handover docs live in `docs/local/` and are intentionally not pushed to GitHub.
- If you are working locally, read `docs/local/README.md` first when it exists.

## Development Environment

The supported runtime and development target is CPython 3.13, matching the
PythonAnywhere web app. The host system Python does not need to be changed.

Create the project virtual environment with Python 3.13 and install the
development requirements:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If `python3.13` is not provided by the host OS, an isolated Python 3.13 can be
downloaded with `uv` without replacing the system Python:

```bash
uv venv --python 3.13 --seed
uv pip install -r requirements-dev.txt
```

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

## Continuous Integration

GitHub Actions runs the full pytest suite for pull requests and pushes to the
default `master` branch using Python 3.13.

The production baseline is PythonAnywhere's `innit` system image with the web
app configured for Python 3.13. Production currently uses the PythonAnywhere
system environment rather than a project virtualenv; dependency changes must
therefore remain compatible with the packages available for that image.

## Notes

- The system Python on this machine may not have required packages such as `Pillow`.
- Test and app verification should be run with the interpreter from `.venv`.
