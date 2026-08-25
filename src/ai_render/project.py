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

import hashlib
import json
import re
from pathlib import Path

from . import assets

PROJECTS_DIR = "projects"
SEQUENCES_DIR = "sequences"
ASSETS_DIR = "assets"

PROJECT_FILE = "project.json"
SEQUENCE_FILE = "sequence.json"
SHOT_FILE = "shot.json"

# Files that describe a level rather than a scene, so listing scenes skips them.
LEVEL_FILES = {PROJECT_FILE, SEQUENCE_FILE, SHOT_FILE}

KNOWN_ROLES = {"variant", "asset"}

# What each kind of artifact is, and which directory it lives in. The kind is in
# the file name too, because each kind counts its own versions: "preview v003" is
# the third preview, which is the only thing a version number is good for.
ARTIFACT_DIRS = {
    "preview": "preview",       # the grey blockout
    "still": "frames",          # individual blockout frames, input to a styleframe
    "styleframe": "styleframes",  # the look reference the generation is given
    "render": "render",         # what the video model returned -- the finished shot
    "views": "artifacts",       # working record
    "sheet": "artifacts",
}

SCENE_ID_LENGTH = 6


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
        """Sheets, views and debug renders -- the working record.

        Inside the shot, not in `out/`: these are the record of how a decision
        was reached, and they are meant to be committed. An image that exists
        only in a chat window is lost to the next session.
        """
        return self.scene_path.parent / "artifacts"

    @property
    def preview_dir(self):
        """The blockout itself, kept apart from the record of how it was made.

        One of these is the deliverable and the rest are evidence. Mixed into one
        directory the video is something to hunt for; on its own it is the first
        thing anyone opens.
        """
        return self.scene_path.parent / "preview"

    @property
    def frames_dir(self):
        """Individual stills through the shot, kept for what comes next.

        Not evidence and not the deliverable: these are an input. A style frame
        is generated from one of them, and reference modes that take images
        rather than a clip are fed from here.
        """
        return self.scene_path.parent / "frames"

    @property
    def stem(self):
        """File-name identity, e.g. `seq_010_sh_0010_street_a`.

        The project is not in it: these files sit inside the project already, and
        a name that repeats its own directory is noise. What it does carry is
        everything that would otherwise be ambiguous once a file is downloaded,
        pasted into a message, or sat next to a file from another shot.
        """
        if self.kind == "shot":
            return f"{self.sequence}_{self.shot}_{self.scene}"
        if self.kind == "asset":
            return f"{ASSETS_DIR}_{self.scene}"
        return self.scene

    def dir_for(self, kind):
        return self.scene_path.parent / ARTIFACT_DIRS[kind]

    def name(self, kind, scene_id, version, suffix=None):
        """`seq_010_sh_0010_street_a_a3f9c1_preview_v003`, plus any suffix.

        Two different things sit between the scene and the version, and they
        answer two different questions. The id says *which spec this came from*,
        so everything made from one state of the scene shares it. The version
        says *which one of these* — and it counts only its own kind, because a
        number that counts every file in the shot tells a human nothing.
        """
        base = f"{self.stem}_{scene_id}_{kind}_v{version:03d}"
        return base + (f"_{suffix}" if suffix else "")

    def next_version(self, kind):
        """The next number for this kind of artifact, across every scene id.

        Counted across ids on purpose: "the fourth preview" should mean the
        fourth one made, not the fourth made from some particular spec. Read off
        disk rather than from a stored count, so it is monotonic and deleting an
        old file never renumbers a newer one -- a version in a committed name has
        to keep meaning what it meant.
        """
        pattern = re.compile(
            re.escape(self.stem) + r"_[0-9a-f]+_" + re.escape(kind) + r"_v(\d+)"
        )
        directory = self.dir_for(kind)
        highest = 0
        if directory.is_dir():
            for path in directory.iterdir():
                found = pattern.match(path.name)
                if found:
                    highest = max(highest, int(found.group(1)))
        return highest + 1

    @property
    def label(self):
        """Human-facing id, e.g. `nyc/seq_010/sh_0010/street_a`."""
        return "/".join(self.out_parts)

    def __repr__(self):
        return f"<Target {self.kind} {self.label}>"


def scene_id(spec):
    """Six hex characters standing for the content of a merged spec.

    Not a counter, and deliberately not ordered: it is the answer to "which
    version of the scene is this file from", which a sequence number can only
    answer by keeping a ledger that can fall out of step. This can be recomputed
    from the spec at any time by anyone -- edit one number in the camera track
    and it changes; change nothing and every file made today matches the ones
    made last week.
    """
    canonical = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:SCENE_ID_LENGTH]


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
    # Instances become objects here and nowhere else, so Blender, `audit` and
    # `check` are all looking at the same geometry. It also means `scene_id`
    # hashes the expansion, which is the only honest choice: editing an asset
    # changes the scene, and an id that ignored the asset would say two
    # different shots were the same one.
    merged = assets.expand(merged, assets_dir(target))
    return merged, target


def assets_dir(target):
    """Where `instances` look their assets up: `projects/<proj>/assets/`.

    None for a standalone file, which has no project to hold a library.
    """
    if target.kind == "shot":
        return target.scene_path.parents[3] / ASSETS_DIR
    if target.kind == "asset":
        return target.scene_path.parent
    return None
