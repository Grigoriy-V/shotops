"""Output layout: one task, one directory, nothing ever overwritten.

    out/demo_room/
      20260824-153012/                        <- a take: one blockout render
        scene.json                            <- the exact spec that produced it
        preview.mp4
        frames/
        20260824-153500_seedance-2-mini_480p/ <- one generation from that take
          run.json
          final.mp4
          final_frames/

Generations nest under the take they were made from, because that is the
question you actually ask later: which blockout did this shot come from, and
what else did I try against it? Timestamps are lexicographically sortable, so
"newest" needs no index and no symlink -- the latter would need elevation on
Windows anyway.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
STAMP = "%Y%m%d-%H%M%S"
TAKE_RE = re.compile(r"^\d{8}-\d{6}$")


def _stamp():
    return datetime.now().strftime(STAMP)


def _unique(path):
    """Never clobber: append -2, -3 ... until the name is free."""
    if not path.exists():
        return path
    for n in range(2, 1000):
        candidate = path.with_name(f"{path.name}-{n}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"could not find a free name next to {path}")


def new_take(scene_name, spec=None, spec_path=None):
    """Start a take directory for a blockout render."""
    take = _unique(OUT / scene_name / _stamp())
    (take / "frames").mkdir(parents=True)
    if spec is not None:
        # Snapshot the spec, so a take stays reproducible even after the scene
        # file moves on.
        (take / "scene.json").write_text(
            json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    elif spec_path is not None:
        shutil.copyfile(spec_path, take / "scene.json")
    return take


def list_takes(scene_name):
    scene_dir = OUT / scene_name
    if not scene_dir.is_dir():
        return []
    return sorted(d for d in scene_dir.iterdir() if d.is_dir() and TAKE_RE.match(d.name[:15]))


def latest_take(scene_name):
    takes = list_takes(scene_name)
    if not takes:
        raise RuntimeError(
            f"no takes for {scene_name!r} in {OUT / scene_name} -- run `render` first"
        )
    return takes[-1]


def resolve_take(scene_name, wanted=None):
    if not wanted:
        return latest_take(scene_name)
    take = OUT / scene_name / wanted
    if not take.is_dir():
        available = [t.name for t in list_takes(scene_name)]
        raise RuntimeError(f"no take {wanted!r} for {scene_name!r}. Available: {available or 'none'}")
    return take


def new_generation(take, model, resolution):
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{model}_{resolution}")
    generation = _unique(take / f"{_stamp()}_{slug}")
    generation.mkdir(parents=True)
    return generation


def write_manifest(out_dir, **fields):
    """Record what produced this clip. Cheap now, priceless three weeks later.

    The parameter is `out_dir`, not `generation`: "generation" is one of the
    field names callers pass, and a collision here is a TypeError at the worst
    possible moment -- right before a paid API call.
    """
    manifest = out_dir / "run.json"
    existing = {}
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
    existing.update(fields)
    manifest.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def list_generations(take):
    return sorted(d for d in take.iterdir() if d.is_dir() and d.name != "frames")
