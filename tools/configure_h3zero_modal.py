"""Create a Modal proxy token and store H3Zero settings without printing secrets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
DEFAULT_MODAL_PYTHON = ROOT / ".tools" / "h3zero" / ".venv" / "Scripts" / "python.exe"
MANAGED = {
    "AI_RENDER_H3ZERO_URL",
    "AI_RENDER_H3ZERO_AUTH",
    "AI_RENDER_H3ZERO_MODAL_KEY",
    "AI_RENDER_H3ZERO_MODAL_SECRET",
}


def _replace_env(values):
    lines = ENV_FILE.read_text(encoding="utf-8-sig").splitlines() if ENV_FILE.exists() else []
    kept = [line for line in lines if line.partition("=")[0].strip() not in MANAGED]
    if kept and kept[-1].strip():
        kept.append("")
    kept.extend(f"{key}={values[key]}" for key in sorted(values))
    ENV_FILE.write_text("\n".join(kept) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--modal-python", type=Path, default=DEFAULT_MODAL_PYTHON)
    args = parser.parse_args()
    completed = subprocess.run(
        [
            str(args.modal_python),
            "-m",
            "modal",
            "workspace",
            "proxy-tokens",
            "create",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    token = json.loads(completed.stdout)
    key = token.get("Modal-Key")
    secret = token.get("Modal-Secret")
    if not key or not secret:
        raise RuntimeError("Modal did not return a proxy token id and secret")
    _replace_env(
        {
            "AI_RENDER_H3ZERO_AUTH": "modal-proxy",
            "AI_RENDER_H3ZERO_MODAL_KEY": key,
            "AI_RENDER_H3ZERO_MODAL_SECRET": secret,
            "AI_RENDER_H3ZERO_URL": args.url.rstrip("/"),
        }
    )
    print("H3Zero URL and dedicated Modal proxy credentials were stored in .env.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print("Could not create the Modal proxy token.", file=sys.stderr)
        raise SystemExit(exc.returncode) from None
