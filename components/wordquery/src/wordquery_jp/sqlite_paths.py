"""SQLite URI filenames, including Windows UNC shares and reserved characters."""

from pathlib import Path, PurePath
from urllib.parse import quote


def read_only_uri(path: PurePath) -> str:
    filename = quote(path.as_posix(), safe="/:")
    options = "mode=ro"
    if filename.startswith("//"):
        # Encode the UNC prefix so SQLite doesn't interpret the server as a URI
        # authority (which most SQLite builds reject).
        filename = "%2F%2F" + filename[2:]
        # Search databases are immutable release snapshots. WSL's UNC bridge
        # does not support SQLite's normal locking reliably; immutable also
        # disables locking and journal creation. Replace releases by path, never
        # modify a database being served this way.
        options += "&immutable=1"
    return f"file:{filename}?{options}"


def absolute_read_only_uri(path: Path) -> str:
    return read_only_uri(path.resolve())
