"""Load and validate a scene spec.

The scene spec is the real output of the agent: a declarative JSON document that
diffs cleanly and can be edited field by field. "Move the camera 20cm left" is a
one-line patch, not a regeneration. Everything downstream -- Blender, the video
model, any future viewer -- is a consumer of this file.
"""

from __future__ import annotations

import json
from pathlib import Path

KNOWN_TYPES = {"cube", "plane", "sphere", "cylinder", "cone", "torus"}
# "smooth" is the only one that looks past its own segment: it carries velocity
# through the key instead of stopping on it. A continuous move wants it.
KNOWN_EASE = {"linear", "ease", "in", "out", "smooth"}
KNOWN_REFERENCE_MODES = {"video", "frames", "first"}
KNOWN_ROLES = {"variant", "asset"}

# Camera angles sit on top of the aim rather than replacing it: `look_at` still
# points the camera, and roll/pan/tilt rotate it about its own axes afterwards.
# Width 1 each, on purpose -- most shots animate roll alone, and a one-number
# channel is a one-line diff.
CAMERA_ANGLES = ("roll", "pan", "tilt")
CHANNEL_WIDTH = {
    "location": 3, "rotation": 3, "scale": 3, "look_at": 3,
    "lens": 1, "roll": 1, "pan": 1, "tilt": 1,
}


class SpecError(ValueError):
    """Raised with a path into the document, so the fix is obvious."""


def _fail(where, message):
    raise SpecError(f"{where}: {message}")


def _check_vec(where, value, width):
    if not isinstance(value, list) or len(value) != width:
        _fail(where, f"expected a list of {width} numbers, got {value!r}")
    for item in value:
        if not isinstance(item, (int, float)) or isinstance(item, bool):
            _fail(where, f"expected numbers, got {value!r}")


def _check_animation(where, animation, duration):
    if not isinstance(animation, dict):
        _fail(where, "must be an object mapping channel -> keyframe list")
    for channel, track in animation.items():
        path = f"{where}.{channel}"
        if channel not in CHANNEL_WIDTH:
            _fail(path, f"unknown channel (known: {', '.join(sorted(CHANNEL_WIDTH))})")
        if not isinstance(track, list) or not track:
            _fail(path, "must be a non-empty list of keyframes")
        last_t = None
        for i, key in enumerate(track):
            kp = f"{path}[{i}]"
            if not isinstance(key, dict) or "t" not in key or "value" not in key:
                _fail(kp, "keyframe needs 't' (seconds) and 'value'")
            t = key["t"]
            if not isinstance(t, (int, float)) or isinstance(t, bool):
                _fail(kp, f"'t' must be a number, got {t!r}")
            if last_t is not None and t < last_t:
                _fail(kp, f"keyframes must be sorted by 't' ({t} follows {last_t})")
            if t > duration + 1e-6:
                _fail(kp, f"'t'={t} is past the scene duration of {duration}s")
            last_t = t
            ease = key.get("ease", "ease")
            if ease not in KNOWN_EASE:
                _fail(kp, f"unknown ease {ease!r} (known: {', '.join(sorted(KNOWN_EASE))})")
            _check_vec(f"{kp}.value", key["value"], CHANNEL_WIDTH[channel])


def validate(spec):
    if not isinstance(spec, dict):
        _fail("<root>", "scene spec must be a JSON object")

    duration = spec.get("duration", 5.0)
    if not isinstance(duration, (int, float)) or duration <= 0:
        _fail("duration", f"must be a positive number, got {duration!r}")
    fps = spec.get("fps", 24)
    if not isinstance(fps, int) or fps <= 0:
        _fail("fps", f"must be a positive integer, got {fps!r}")

    resolution = spec.get("resolution", [960, 540])
    _check_vec("resolution", resolution, 2)

    objects = spec.get("objects", [])
    if not isinstance(objects, list):
        _fail("objects", "must be a list")
    names = set()
    for i, obj in enumerate(objects):
        where = f"objects[{i}]"
        if not isinstance(obj, dict):
            _fail(where, "must be an object")
        kind = obj.get("type", "cube")
        if kind not in KNOWN_TYPES:
            _fail(f"{where}.type", f"unknown type {kind!r} (known: {', '.join(sorted(KNOWN_TYPES))})")
        name = obj.get("name", kind)
        if name in names:
            _fail(f"{where}.name", f"duplicate object name {name!r}")
        names.add(name)
        for channel in ("location", "rotation", "scale"):
            if channel in obj:
                _check_vec(f"{where}.{channel}", obj[channel], 3)
        if "color" in obj:
            _check_vec(f"{where}.color", obj["color"], 3)
            if not all(0.0 <= c <= 1.0 for c in obj["color"]):
                _fail(f"{where}.color", f"components must be in 0..1, got {obj['color']!r}")
        if "animation" in obj:
            _check_animation(f"{where}.animation", obj["animation"], duration)

    role = spec.get("role", "variant")
    if role not in KNOWN_ROLES:
        _fail("role", f"unknown role {role!r} (known: {', '.join(sorted(KNOWN_ROLES))})")

    camera = spec.get("camera")
    if not isinstance(camera, dict):
        _fail("camera", "a scene needs a camera object")
    for channel in ("location", "look_at"):
        if channel in camera:
            _check_vec(f"camera.{channel}", camera[channel], 3)
    for channel in CAMERA_ANGLES:
        if channel in camera:
            value = camera[channel]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                _fail(f"camera.{channel}", f"must be a number of degrees, got {value!r}")
    if "animation" in camera:
        _check_animation("camera.animation", camera["animation"], duration)
    has_loc = "location" in camera or "location" in (camera.get("animation") or {})
    if not has_loc:
        _fail("camera", "needs 'location' or an animated location track")

    generation = spec.get("generation")
    if generation is not None:
        if not isinstance(generation, dict):
            _fail("generation", "must be an object")
        if not generation.get("prompt"):
            _fail("generation.prompt", "required to run the video generation step")
        mode = generation.get("reference_mode", "video")
        if mode not in KNOWN_REFERENCE_MODES:
            _fail(
                "generation.reference_mode",
                f"unknown mode {mode!r} (known: {', '.join(sorted(KNOWN_REFERENCE_MODES))})",
            )
        seconds = generation.get("duration", 5)
        if not isinstance(seconds, int) or not 4 <= seconds <= 30:
            _fail("generation.duration", f"must be an integer from 4 to 30, got {seconds!r}")
        if "model" in generation:
            # Left open on purpose: providers add model variants faster than a
            # whitelist here could track, and rejecting a working one is worse
            # than passing a typo through to a clear API error.
            if not isinstance(generation["model"], str) or not generation["model"].strip():
                _fail("generation.model", f"must be a non-empty string, got {generation['model']!r}")

    stills = spec.get("render", {}).get("stills", 8)
    if not isinstance(stills, int) or not 0 <= stills <= 30:
        _fail("render.stills", f"must be an integer from 0 to 30, got {stills!r}")
    if generation and generation.get("reference_mode") == "frames" and stills < 2:
        _fail("render.stills", "reference_mode 'frames' needs at least 2 stills")

    return spec


def load(path):
    path = Path(path)
    try:
        # utf-8-sig: plenty of Windows tools write a BOM, and a spec that is
        # otherwise perfect should not fail on an invisible byte.
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SpecError(f"{path}: invalid JSON -- {exc}") from exc
    try:
        return validate(raw)
    except SpecError as exc:
        raise SpecError(f"{path} -> {exc}") from None


def load_target(path):
    """Load a scene with its project/sequence/shot defaults applied.

    Returns `(spec, target)`. This is what the CLI uses; `load` stays for a bare
    file with no hierarchy above it.
    """
    from . import project

    merged, target = project.load_spec(path)
    try:
        return validate(merged), target
    except SpecError as exc:
        raise SpecError(f"{target.scene_path} -> {exc}") from None


def scene_name(spec, path):
    return spec.get("name") or Path(path).stem
