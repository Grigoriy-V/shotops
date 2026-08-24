"""Minimal .env loader.

Keys belong in a gitignored file, not in shell history and not in a global user
environment variable. Real environment variables still win, so CI or a one-off
`$env:COMETAPI_KEY=...` can override the file without editing it.

Deliberately dependency-free: this runs before anything else and should never be
the reason a fresh checkout fails to start.
"""

from __future__ import annotations

from pathlib import Path
import os

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load(path=ENV_FILE):
    path = Path(path)
    if not path.exists():
        return {}

    loaded = {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        if "=" not in line:
            raise ValueError(f"{path}:{lineno}: expected KEY=VALUE, got {raw!r}")

        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]

        loaded[key] = value
        os.environ.setdefault(key, value)
    return loaded
