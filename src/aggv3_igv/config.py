"""Load aggv3_igv config file."""

import sys
import tomllib
from pathlib import Path

_SEARCH_PATHS = [
    Path("config.toml"),
    Path(".config/aggv3_igv/config.toml"),
    Path.home() / ".config" / "aggv3_igv" / "config.toml",
]


def load_config() -> dict:
    for path in _SEARCH_PATHS:
        if path.exists():
            with open(path, "rb") as f:
                return tomllib.load(f)

    searched = "\n  ".join(str(p) for p in _SEARCH_PATHS)
    sys.exit(
        f"Config file not found. Searched:\n  {searched}\n"
        "Place config.toml at one of the above paths."
    )
