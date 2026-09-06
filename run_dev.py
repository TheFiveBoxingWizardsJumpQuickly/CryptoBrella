"""Start the local app with optional machine-local WordQuery configuration."""

import json
import os
import time
from pathlib import Path


def configure_wordquery(root: Path) -> None:
    if "WORDQUERY_DB" in os.environ:
        return
    config_path = root / "var/wordquery/dev.json"
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        os.environ["WORDQUERY_DB"] = str((root / config["database"]).resolve())
        os.environ.setdefault("WORDQUERY_RELEASE_MODE", config.get("release_mode", "updated"))


def main() -> None:
    configure_wordquery(Path(__file__).resolve().parent)
    print("Loading application and WordQuery dictionary...", flush=True)
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
