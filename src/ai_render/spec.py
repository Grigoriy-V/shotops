"""Load and validate a scene spec.

The scene spec is the real output of the agent: a declarative JSON document that
diffs cleanly and can be edited field by field. "Move the camera 20cm left" is a
one-line patch, not a regeneration. Everything downstream -- Blender, the video
model, any future viewer -- is a consumer of this file.
"""

from __future__ import annotations

import json
from pathlib import Path

KNOWN_TYPES = {"cube", "plane", "sphere", "cylinder", "cone", "torus", "mesh"}
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
        if kind == "mesh":
            verts = obj.get("vertices")
            if not isinstance(verts, list) or not verts:
                _fail(f"{where}.vertices", "a mesh needs a non-empty list of vertices")
            for v_index, vertex in enumerate(verts):
                _check_vec(f"{where}.vertices[{v_index}]", vertex, 3)
            faces = obj.get("faces")
            if not isinstance(faces, list) or not faces:
                _fail(f"{where}.faces", "a mesh needs a non-empty list of faces")
            for f_index, face in enumerate(faces):
                if not isinstance(face, list) or len(face) < 3:
                    _fail(f"{where}.faces[{f_index}]", f"needs at least three indices, got {face!r}")
                # An index past the end is a crash inside Blender, a long way
                # from the file that caused it.
                bad = [j for j in face if not isinstance(j, int) or not 0 <= j < len(verts)]
                if bad:
                    _fail(
                        f"{where}.faces[{f_index}]",
                        f"vertex index out of range: {bad!r} (have {len(verts)} vertices)",
                    )
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
        # Either half of the deal, but one of them. `prompt` is the look only and
        # gets the reference contract prepended; `full_prompt` is sent byte for
        # byte and takes precedence, which is how a prompt that was tested by
        # hand stays exactly the prompt that was tested.
        # An asset is scratch work -- a car on a grey plane, checked and rendered
        # locally, never generated -- so it inherits the project's generation
        # defaults without ever needing a prompt to go with them.
        h3zero = generation.get("h3zero")
        if h3zero is not None and not isinstance(h3zero, dict):
            _fail("generation.h3zero", "must be an object")
        h3_prompt = h3zero.get("full_prompt") if isinstance(h3zero, dict) else None
        if role != "asset" and not generation.get("prompt") and not generation.get("full_prompt") and not h3_prompt:
            _fail(
                "generation.prompt",
                "required to run the video generation step -- or 'full_prompt' "
                "to send a complete prompt of your own, contract included; H3Zero may use "
                "generation.h3zero.full_prompt",
            )
        if "full_prompt" in generation and not str(generation["full_prompt"]).strip():
            _fail("generation.full_prompt", "must be a non-empty string when present")
        if isinstance(h3zero, dict):
            if not isinstance(h3_prompt, str) or not h3_prompt.strip():
                _fail("generation.h3zero.full_prompt", "must be a non-empty string")
            profile = h3zero.get("sampling_profile", "turbo_4")
            if profile not in {"turbo_4", "turbo_8", "spectrum", "base"}:
                _fail(
                    "generation.h3zero.sampling_profile",
                    "must be turbo_4, turbo_8, spectrum, or base",
                )
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
        references = generation.get("style_references")
        if references is not None:
            # Order is meaning here -- the first entry becomes @image1 and the
            # prompt refers to the tags by number, so a set or a mapping would
            # lose the only thing that binds a file to a tag.
            if not isinstance(references, list) or not references:
                _fail("generation.style_references", "must be a non-empty list of paths")
            for index, ref in enumerate(references):
                if not isinstance(ref, str) or not ref.strip():
                    _fail(
                        f"generation.style_references[{index}]",
                        f"must be a non-empty path relative to the shot directory, got {ref!r}",
                    )

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
    from . import assets, project

    try:
        merged, target = project.load_spec(path)
    except assets.AssetError as exc:
        # Expansion happens inside load_spec, so its errors arrive without the
        # context every other spec error carries. Give them the same shape.
        raise SpecError(f"{Path(path)} -> {exc}") from None
    try:
        return validate(merged), target
    except SpecError as exc:
        raise SpecError(f"{target.scene_path} -> {exc}") from None


def scene_name(spec, path):
    return spec.get("name") or Path(path).stem
