"""Drive headless Blender to turn a scene spec into a grey blockout video."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = ROOT / "blender" / "build_scene.py"
VIEWS_SCRIPT = ROOT / "blender" / "render_views.py"

_CANDIDATES = [
    # The portable build this project fetches for itself wins over any system
    # install, so the pipeline is pinned to a known Blender version.
    str(ROOT / ".tools"),
    r"C:\Program Files\Blender Foundation",
    r"C:\Program Files (x86)\Blender Foundation",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation"),
    "/Applications/Blender.app/Contents/MacOS",
    "/usr/bin",
    "/usr/local/bin",
]


class BlenderNotFound(RuntimeError):
    pass


def find_blender():
    override = os.environ.get("AI_RENDER_BLENDER")
    if override:
        if not Path(override).exists():
            raise BlenderNotFound(f"AI_RENDER_BLENDER points at a missing file: {override}")
        return override

    exe = "blender.exe" if sys.platform == "win32" else "blender"
    for root in _CANDIDATES:
        base = Path(root)
        if not base.is_dir():
            continue
        direct = base / exe
        if direct.exists():
            return str(direct)
        # Portable and Windows installs both nest one version directory deep.
        for found in sorted(base.glob(f"*/{exe}"), reverse=True):
            return str(found)

    on_path = shutil.which("blender")
    if on_path:
        return on_path

    raise BlenderNotFound(
        "Blender not found. Install it, or set AI_RENDER_BLENDER to the executable.\n"
        "  winget install --id BlenderFoundation.Blender -e"
    )


def render_views(spec_path, out_dir, verbose=False):
    """Render top, front, side and three-quarter views with the camera path drawn."""
    blender = find_blender()
    # Absolute on this side too, so the path in the log is the path on disk.
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [blender, "-b", "-noaudio", "-P", str(VIEWS_SCRIPT), "--", str(spec_path), str(out_dir)]
    print(f"[views] {Path(blender).name} -> {out_dir}")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if verbose or proc.returncode != 0:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"Blender exited with code {proc.returncode}")

    made = sorted(out_dir.glob("view_*.png"))
    if not made:
        raise RuntimeError(f"Blender reported success but produced no views in {out_dir}")
    return made


def render(spec_path, out_path, verbose=False):
    """Render the blockout. Returns the path to the finished mp4."""
    blender = find_blender()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    cmd = [blender, "-b", "-noaudio", "-P", str(BUILD_SCRIPT), "--", str(spec_path), str(out_path)]
    print(f"[render] {Path(blender).name} -> {out_path}")
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if verbose or proc.returncode != 0:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"Blender exited with code {proc.returncode}")

    if not out_path.exists():
        # Older Blender builds still decorate video output with the frame range.
        strays = sorted(out_path.parent.glob(f"{out_path.stem}*.mp4"))
        if not strays:
            raise RuntimeError(f"Blender reported success but produced no file at {out_path}")
        strays[0].rename(out_path)

    size_mb = out_path.stat().st_size / 1e6
    print(f"[render] ok -- {out_path} ({size_mb:.1f} MB)")
    return out_path
