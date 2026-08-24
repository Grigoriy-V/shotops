"""Project → sequence → shot → scene.

A scene file does not carry its own identity; its **path** does. That is the
whole trick of this module: `projects/nyc/sequences/seq_010/sh_0010/street_a.json`
says which project, sequence and shot it belongs to without repeating any of it
inside the file, and the output path mirrors it exactly so any artifact can be
read backwards to the thing that made it.

Three shapes are recognised:

    projects/<proj>/sequences/<seq>/<shot>/<scene>.json   a shot scene
    projects/<proj>/assets/<name>.json                    project-level work
    <anything else>.json                                  standalone

Standalone exists because a bare file should still work -- for a scratch test or
a doctest fixture. It is not where real shots live.

Several scenes in one shot are *parallel variants*, never segments of it: a shot
is one of its scenes, never an assembly of them. `shot.json` names the one it
currently is.

See docs/design/pipeline-structure.md for the reasoning.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECTS_DIR = "projects"
SEQUENCES_DIR = "sequences"
ASSETS_DIR = "assets"

PROJECT_FILE = "project.json"
SEQUENCE_FILE = "sequence.json"
SHOT_FILE = "shot.json"

# Files that describe a level rather than a scene, so listing scenes skips them.
LEVEL_FILES = {PROJECT_FILE, SEQUENCE_FILE, SHOT_FILE}

KNOWN_ROLES = {"variant", "asset"}


class ProjectError(ValueError):
    """Raised when a path does not resolve to something renderable."""


class Target:
    """A scene, and where it sits in the hierarchy.

    `out_parts` is the identity as a path: it is what `out/` mirrors, and it is
    deliberately derived from the file's location rather than from any `name`
    field inside it. Two scenes may not disagree with their own directory.
    """

    __slots__ = ("scene_path", "scene", "project", "sequence", "shot", "kind")

    def __init__(self, scene_path, scene, kind, project=None, sequence=None, shot=None):
        self.scene_path = Path(scene_path)
        self.scene = scene
        self.kind = kind
        self.project = project
        self.sequence = sequence
        self.shot = shot

    @property
    def out_parts(self):
        if self.kind == "shot":
            return (self.project, self.sequence, self.shot, self.scene)
        if self.kind == "asset":
            return (self.project, ASSETS_DIR, self.scene)
        return (self.scene,)

    @property
    def artifacts_dir(self):
        """Where views, sheets and debug renders are kept.

        Inside the shot, not in `out/`: these are the record of how a decision
        was reached, and they are meant to be committed. An image that exists
        only in a chat window is lost to the next session.
        """
        return self.scene_path.parent / "artifacts"

    @property
    def label(self):
        """Human-facing id, e.g. `nyc/seq_010/sh_0010/street_a`."""
        return "/".join(self.out_parts)

    def __repr__(self):
        return f"<Target {self.kind} {self.label}>"


def _split(path):
    """Locate `projects/<proj>/...` in a path, if it is in one at all."""
    parts = path.parts
    for i in range(len(parts) - 1, -1, -1):
        if parts[i] == PROJECTS_DIR and i + 1 < len(parts):
            return parts[i + 1], parts[i + 2 :]
    return None, ()


def resolve(path):
    """Turn a path into a Target.

    Accepts a scene file, or a shot directory -- in which case `shot.json` says
    which of its scenes the shot currently is.
    """
    path = Path(path)

    if path.is_dir():
        return _resolve_shot_dir(path)

    if path.suffix.lower() != ".json":
        raise ProjectError(f"{path}: expected a scene .json or a shot directory")
    if path.name in LEVEL_FILES:
        raise ProjectError(
            f"{path.name} describes a level, not a scene. "
            f"Point at a scene file, or at the directory containing it."
        )

    scene = path.stem
    project, rest = _split(path)
    if project is None:
        return Target(path, scene, "standalone")

    # rest is everything under projects/<proj>/, ending in the file name.
    if len(rest) >= 2 and rest[0] == ASSETS_DIR:
        return Target(path, scene, "asset", project=project)
    if len(rest) >= 4 and rest[0] == SEQUENCES_DIR:
        return Target(path, scene, "shot", project=project, sequence=rest[1], shot=rest[2])

    raise ProjectError(
        f"{path}: inside project {project!r} but not under "
        f"{SEQUENCES_DIR}/<sequence>/<shot>/ or {ASSETS_DIR}/"
    )


def _resolve_shot_dir(directory):
    """A shot directory renders the scene `shot.json` selects."""
    shot_file = directory / SHOT_FILE
    scenes = list_scenes(directory)
    if not scenes:
        raise ProjectError(f"{directory}: no scene .json files here")

    selected = None
    if shot_file.exists():
        selected = _read(shot_file).get("scene")

    if selected:
        chosen = directory / f"{selected}.json"
        if not chosen.exists():
            available = [s.stem for s in scenes]
            raise ProjectError(
                f"{shot_file}: selects scene {selected!r}, which does not exist. "
                f"Available: {available}"
            )
    elif len(scenes) == 1:
        chosen = scenes[0]
    else:
        available = [s.stem for s in scenes]
        raise ProjectError(
            f"{directory}: {len(scenes)} scenes and no selection. "
            f"Add \"scene\": \"<name>\" to {SHOT_FILE}, or name one directly. "
            f"Available: {available}"
        )
    return resolve(chosen)


def list_scenes(directory):
    directory = Path(directory)
    return sorted(
        p for p in directory.glob("*.json") if p.name not in LEVEL_FILES
    )


def _read(path):
    # utf-8-sig for the same reason spec.load uses it: a BOM should never be the
    # thing standing between a correct file and a render.
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ProjectError(f"{path}: invalid JSON -- {exc}") from exc


def chain(target):
    """The level files above a scene, outermost first.

    Only files that exist are returned; every level is optional. A project with
    no `project.json` is simply a project with no defaults.
    """
    path = target.scene_path
    files = []
    if target.kind == "shot":
        root = path.parents[3]  # projects/<proj>
        files = [
            root / PROJECT_FILE,
            root / SEQUENCES_DIR / target.sequence / SEQUENCE_FILE,
            path.parent / SHOT_FILE,
        ]
    elif target.kind == "asset":
        files = [path.parents[1] / PROJECT_FILE]
    return [f for f in files if f.exists()]


def merge(base, override):
    """Deep-merge dicts; anything else is replaced outright.

    Replacement is the right default for lists: an `objects` list that merged
    with its parent would be impossible to reason about, and a shot that wants
    fewer objects than the project could never say so.
    """
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def load_spec(path):
    """Read a scene with its inherited defaults applied.

    Resolution order, most specific last: project → sequence → shot → scene.
    A level file holds only what differs at that level, which is what keeps a
    diff readable -- a spec that repeats its parent buries real changes in
    boilerplate.
    """
    target = resolve(path)
    merged = {}
    for level in chain(target):
        data = _read(level)
        data.pop("scene", None)  # a selection, not a spec field
        merged = merge(merged, data)
    merged = merge(merged, _read(target.scene_path))
    merged.setdefault("name", target.scene)
    return merged, target
