"""Start the local app with optional machine-local WordQuery configuration."""

import argparse
import json
import os
import time
from pathlib import Path


def configure_wordquery(root: Path, *, load_mode: str | None = None) -> None:
    config_path = root / "var/wordquery/dev.json"
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        os.environ.setdefault(
            "WORDQUERY_DB", str((root / config["database"]).resolve())
        )
        os.environ.setdefault("WORDQUERY_RELEASE_MODE", config.get("release_mode", "updated"))
        for config_key, environment_key in (
            ("load_mode", "WORDQUERY_LOAD_MODE"),
            ("show_on_home", "WORDQUERY_SHOW_ON_HOME"),
            ("enforce_freshness", "WORDQUERY_ENFORCE_FRESHNESS"),
        ):
            if config_key in config:
                value = config[config_key]
                if isinstance(value, bool):
                    value = "1" if value else "0"
                os.environ.setdefault(environment_key, str(value))
    if load_mode is not None:
        os.environ["WORDQUERY_LOAD_MODE"] = load_mode
        if load_mode == "disabled":
            os.environ["WORDQUERY_SHOW_ON_HOME"] = "0"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wordquery", choices=("eager", "lazy", "disabled"),
        help="Override the local WordQuery dictionary loading mode",
    )
    args = parser.parse_args()
    configure_wordquery(Path(__file__).resolve().parent, load_mode=args.wordquery)
    print("Loading application...", flush=True)
    started = time.monotonic()
    from app.app import app

    error = app.extensions.get("wordquery_error")
    if error:
        app.logger.warning("WordQuery could not load its dictionary: %s", error)
    print(f"Application loaded in {time.monotonic() - started:.1f}s.", flush=True)
    # The debug reloader imports the app in a second process and would load the
    # large dictionary twice, particularly costly over Windows/WSL UNC paths.
    app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    main()
