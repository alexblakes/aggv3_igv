"""Load aggv3_igv config file."""

import sys
import tomllib
from importlib import resources
from pathlib import Path

# User-overridable locations, searched in order. If none exist, the default
# config bundled with the package (src/aggv3_igv/config.toml) is used.
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

    # Fall back to the default config bundled with the package.
    bundled = resources.files("aggv3_igv").joinpath("config.toml")
    if bundled.is_file():
        with bundled.open("rb") as f:
            return tomllib.load(f)

    searched = "\n  ".join(str(p) for p in _SEARCH_PATHS)
    sys.exit(
        f"Config file not found. Searched:\n  {searched}\n"
        "Place config.toml at one of the above paths."
    )
