"""Runs INSIDE Blender:  blender -b -P build_scene.py -- <scene.json> <out.mp4>

Builds a grey white-model blockout from a scene spec and renders it to video.
The output is deliberately ugly: flat grey, no textures, studio light. That is
exactly what a video model wants as a structure reference -- with nothing to
distract it, it reads pure trajectory, framing and speed.

Blender ships its own Python, so this file is stdlib-only (json + math).
"""

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

# ---------------------------------------------------------------- interpolation

def _smoothstep(x):
    return x * x * (3.0 - 2.0 * x)


def _ease(x, mode):
    if mode == "linear":
        return x
    if mode == "in":
        return x * x
    if mode == "out":
        return 1.0 - (1.0 - x) ** 2
    return _smoothstep(x)  # "ease" (default)


def _hermite(track, i, t):
    """Cubic Hermite across the segment, with Catmull-Rom tangents.

    Every other mode here shapes one segment in isolation, which means it knows
    nothing about the segments either side of it. `ease` has zero velocity at
    *both* ends, so a run of eased keys is a stop at every key -- arrive, halt,
    set off again. `linear` has the opposite fault: constant speed within a
    segment and an instant change of direction at the key, which on a position
    track makes the path a polyline with corners in it.

    This mode takes its tangent at a key from the keys either side of it, so the
    tangent leaving a key equals the tangent entering it: velocity is continuous
    through the key, and the path curves through it instead of turning. Speed
    still varies -- it follows key spacing, which is how it should be steered.

    One-sided at the ends, which makes a two-key track exactly linear.
    """
    a, b = track[i], track[i + 1]
    span = b["t"] - a["t"]
    if span <= 0:
        return list(b["value"])
    x = (t - a["t"]) / span

    prev = track[i - 1] if i > 0 else a
    nxt = track[i + 2] if i + 2 < len(track) else b
    before = b["t"] - prev["t"]
    after = nxt["t"] - a["t"]

    h00 = 2 * x**3 - 3 * x**2 + 1
    h10 = x**3 - 2 * x**2 + x
    h01 = -2 * x**3 + 3 * x**2
    h11 = x**3 - x**2

    out = []
    for k, (av, bv) in enumerate(zip(a["value"], b["value"])):
        # Secants across the neighbours, in units per second.
        ma = (bv - prev["value"][k]) / before if before > 0 else 0.0
        mb = (nxt["value"][k] - av) / after if after > 0 else 0.0
        out.append(h00 * av + h10 * span * ma + h01 * bv + h11 * span * mb)
    return out


def sample(track, t):
    """Evaluate a keyframe track at time t (seconds). Returns a list of floats.

    Easing is baked here rather than handed to Blender f-curves, so the motion
    is fully determined by the JSON and does not drift with Blender versions.
    """
    if not track:
        return None
    if t <= track[0]["t"]:
        return list(track[0]["value"])
    if t >= track[-1]["t"]:
        return list(track[-1]["value"])

    for i in range(len(track) - 1):
        a, b = track[i], track[i + 1]
        if a["t"] <= t <= b["t"]:
            mode = a.get("ease", "ease")
            if mode == "smooth":
                return _hermite(track, i, t)
            span = b["t"] - a["t"]
            x = 0.0 if span <= 0 else (t - a["t"]) / span
            x = _ease(x, mode)
            return [av + (bv - av) * x for av, bv in zip(a["value"], b["value"])]
    return list(track[-1]["value"])


def animated(spec, channel, t, fallback):
    track = (spec.get("animation") or {}).get(channel)
    if track:
        return sample(track, t)
    return list(spec.get(channel, fallback))


# ---------------------------------------------------------------- scene build

PRIMITIVES = {
    "cube": lambda o: bpy.ops.mesh.primitive_cube_add(size=o.get("size", 2.0)),
    "plane": lambda o: bpy.ops.mesh.primitive_plane_add(size=o.get("size", 10.0)),
    "sphere": lambda o: bpy.ops.mesh.primitive_uv_sphere_add(radius=o.get("size", 1.0)),
    "cylinder": lambda o: bpy.ops.mesh.primitive_cylinder_add(
        radius=o.get("size", 1.0), depth=o.get("depth", 2.0)
    ),
    "cone": lambda o: bpy.ops.mesh.primitive_cone_add(
        radius1=o.get("size", 1.0), depth=o.get("depth", 2.0)
    ),
    "torus": lambda o: bpy.ops.mesh.primitive_torus_add(
        major_radius=o.get("size", 1.0), minor_radius=o.get("minor_radius", 0.25)
    ),
}


def add_object(spec):
    kind = spec.get("type", "cube")
    if kind not in PRIMITIVES:
        raise ValueError(
            "unknown object type %r (known: %s)" % (kind, ", ".join(sorted(PRIMITIVES)))
        )
    PRIMITIVES[kind](spec)
    obj = bpy.context.active_object
    obj.name = spec.get("name", kind)
    obj.rotation_mode = "XYZ"
    obj.location = Vector(spec.get("location", [0, 0, 0]))
    obj.rotation_euler = [math.radians(a) for a in spec.get("rotation", [0, 0, 0])]
    obj.scale = Vector(spec.get("scale", [1, 1, 1]))
    if "color" in spec:
        # Viewport object colour, which Workbench renders directly. Separating
        # surfaces by value gives the video model a readable silhouette to hold
        # on to; a scene at one flat grey gives it almost nothing.
        rgb = spec["color"]
        obj.color = (rgb[0], rgb[1], rgb[2], 1.0)
    return obj


def aim(location, target):
    """Quaternion that points a Blender camera (-Z forward, +Y up) at target."""
    direction = Vector(target) - Vector(location)
    if direction.length < 1e-6:
        direction = Vector((0.0, 1.0, 0.0))
    return direction.to_track_quat("-Z", "Y")


def angle(cam_spec, channel, t):
    """One camera angle in degrees: animated track if present, else static."""
    track = (cam_spec.get("animation") or {}).get(channel)
    if track:
        return sample(track, t)[0]
    return float(cam_spec.get(channel, 0.0))


def orient(location, target, pan=0.0, tilt=0.0, roll=0.0):
    """Aim at a point, then rotate about the camera's own axes.

    `look_at` alone gives the horizon-level solution with the target dead centre.
    These three angles buy back what that costs: banking into a turn, and framing
    a subject off-centre.

    Right-multiplication is what makes the angles local rather than world. Order
    is aim, pan, tilt, roll -- roll last, so banking does not drag the aim around
    with it.
    """
    quat = aim(location, target)
    if pan:
        quat = quat @ Quaternion((0.0, 1.0, 0.0), math.radians(pan))
    if tilt:
        quat = quat @ Quaternion((1.0, 0.0, 0.0), math.radians(tilt))
    if roll:
        quat = quat @ Quaternion((0.0, 0.0, 1.0), math.radians(roll))
    return quat


def bake(scene_spec, objects, camera, fps, frames):
    """Bake every animated channel to per-frame keys.

    Per-frame baking costs nothing at these lengths and removes a whole class of
    surprises -- gimbal flips on camera aim, f-curve overshoot past a keyframe.
    """
    camera.rotation_mode = "QUATERNION"
    prev_quat = None

    for frame in range(1, frames + 1):
        t = (frame - 1) / fps

        for obj, spec in objects:
            if not spec.get("animation"):
                continue
            anim = spec["animation"]
            if "location" in anim:
                obj.location = Vector(sample(anim["location"], t))
                obj.keyframe_insert("location", frame=frame)
            if "rotation" in anim:
                obj.rotation_euler = [math.radians(a) for a in sample(anim["rotation"], t)]
                obj.keyframe_insert("rotation_euler", frame=frame)
            if "scale" in anim:
                obj.scale = Vector(sample(anim["scale"], t))
                obj.keyframe_insert("scale", frame=frame)

        cam_spec = scene_spec["camera"]
        loc = animated(cam_spec, "location", t, [0, -10, 2])
        target = animated(cam_spec, "look_at", t, [0, 0, 0])
        camera.location = Vector(loc)
        quat = orient(
            loc, target,
            pan=angle(cam_spec, "pan", t),
            tilt=angle(cam_spec, "tilt", t),
            roll=angle(cam_spec, "roll", t),
        )
        # Keep the quaternion on the same hemisphere as the previous frame,
        # otherwise interpolation can take the long way round and spin the shot.
        # This has to run after composition: a bank crossing 180 degrees would
        # otherwise still flip the shot mid-move.
        if prev_quat is not None and quat.dot(prev_quat) < 0:
            quat = Quaternion((-quat.w, -quat.x, -quat.y, -quat.z))
        prev_quat = quat
        camera.rotation_quaternion = quat
        camera.keyframe_insert("location", frame=frame)
        camera.keyframe_insert("rotation_quaternion", frame=frame)

        lens = (cam_spec.get("animation") or {}).get("lens")
        if lens:
            camera.data.lens = sample(lens, t)[0]
            camera.data.keyframe_insert("lens", frame=frame)


def configure_render(scene, spec, frames, out_path):
    render_spec = spec.get("render", {})
    width, height = spec.get("resolution", [960, 540])

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.resolution_percentage = 100
    scene.render.fps = int(spec.get("fps", 24))
    scene.frame_start = 1
    scene.frame_end = frames

    shading = scene.display.shading
    shading.light = "STUDIO"
    # Any per-object colour in the scene switches the whole render to OBJECT
    # mode; otherwise everything stays on one flat grey.
    per_object = any("color" in obj for obj in spec.get("objects", []))
    shading.color_type = "OBJECT" if per_object else "SINGLE"
    shading.single_color = tuple(render_spec.get("object_color", [0.75, 0.75, 0.75]))
    shading.show_shadows = bool(render_spec.get("shadow", True))
    shading.show_cavity = bool(render_spec.get("cavity", True))
    shading.background_type = "VIEWPORT"
    shading.background_color = tuple(render_spec.get("background", [0.05, 0.05, 0.06]))
    scene.display.render_aa = "8"

    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.ffmpeg_preset = "GOOD"
    # Blender otherwise decorates video filenames with the frame range; we want
    # the exact path the orchestrator is going to hand to the upload step.
    scene.render.use_file_extension = False
    scene.render.filepath = str(out_path)


def render_stills(scene, out_path, frames, count):
    """Render `count` evenly spaced stills next to the video.

    Some gateways only accept image references, so the same blockout has to be
    available as a storyboard. Re-rendering a handful of frames is cheap next to
    the full sequence, and it guarantees the stills match the clip exactly.
    """
    if count <= 0:
        return
    frames_dir = Path(out_path).parent / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.png"):
        old.unlink()

    picks = sorted({1 + round(i * (frames - 1) / max(1, count - 1)) for i in range(count)})
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_file_extension = True
    for index, frame in enumerate(picks, start=1):
        scene.frame_set(frame)
        scene.render.filepath = str(frames_dir / f"frame_{index:02d}_")
        bpy.ops.render.render(write_still=True)
    print("[ai_render] %d stills -> %s" % (len(picks), frames_dir))


def main(spec_path, out_path):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    fps = int(spec.get("fps", 24))
    frames = max(1, round(float(spec.get("duration", 5.0)) * fps))

    objects = [(add_object(o), o) for o in spec.get("objects", [])]

    cam_spec = spec.get("camera", {})
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = cam_spec.get("lens", 35.0)
    cam_data.sensor_width = cam_spec.get("sensor_width", 36.0)
    camera = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    bake(spec, objects, camera, fps, frames)
    configure_render(scene, spec, frames, out_path)

    print("[ai_render] %d objects, %d frames @ %dfps -> %s" % (len(objects), frames, fps, out_path))
    bpy.ops.render.render(animation=True)

    still_count = int(spec.get("render", {}).get("stills", 8))
    render_stills(scene, out_path, frames, still_count)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) != 2:
        raise SystemExit("usage: blender -b -P build_scene.py -- <scene.json> <out.mp4>")
    main(argv[0], argv[1])
