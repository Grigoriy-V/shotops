"""Runs INSIDE Blender:  blender -b -P render_views.py -- <scene.json> <out_dir>

Renders the scene from outside the shot: top, front and three-quarter, with the
camera path drawn into the geometry.

A frame from inside the shot answers "does this look right". It cannot answer
"where is everything, and where does the camera actually go" -- and that is the
question an agent authoring a spec needs answered, because it is the one it
cannot see. This is the cheap half of the feedback loop described in
docs/design/feedback-loop.md; the other half is arithmetic that needs no pixels
at all.

Same Blender-only constraint as build_scene.py: stdlib plus bpy.
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_scene  # noqa: E402

MARKERS = 60          # camera path samples
MARKER_SIZE = 0.35    # metres; scaled up for large scenes below
PATH_COLOR = (0.95, 0.95, 0.95, 1.0)
AIM_COLOR = (0.62, 0.62, 0.62, 1.0)


def world_bounds(objects):
    """Axis-aligned bounds of everything built, in world space."""
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in objects:
        # An empty has no geometry to bound, and counting it as a point at its
        # own origin would drag the frame toward a thing that never renders.
        if obj.data is None:
            continue
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner)
            for i in range(3):
                lo[i] = min(lo[i], point[i])
                hi[i] = max(hi[i], point[i])
    return lo, hi


def draw_path(spec, duration, size):
    """Mark the camera path, and every tenth marker its aim direction.

    Drawn as real geometry rather than an overlay: Workbench in background mode
    renders objects, not viewport gizmos, so a gizmo would simply not appear.
    """
    cam_spec = spec.get("camera", {})
    made = []
    for i in range(MARKERS):
        t = duration * i / max(1, MARKERS - 1)
        loc = build_scene.animated(cam_spec, "location", t, [0, -10, 2])
        bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
        marker = bpy.context.active_object
        marker.name = f"path_{i:03d}"
        marker.color = PATH_COLOR
        made.append(marker)

        if i % 10 == 0:
            target = build_scene.animated(cam_spec, "look_at", t, [0, 0, 0])
            direction = Vector(target) - Vector(loc)
            if direction.length > 1e-6:
                tip = Vector(loc) + direction.normalized() * (size * 8)
                bpy.ops.mesh.primitive_cube_add(size=size * 0.6, location=tip)
                aim_marker = bpy.context.active_object
                aim_marker.name = f"aim_{i:03d}"
                aim_marker.color = AIM_COLOR
                made.append(aim_marker)
    return made


def add_camera(name, location, ortho_scale=None, look_at=None):
    data = bpy.data.cameras.new(name)
    if ortho_scale:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    else:
        data.lens = 35.0
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = Vector(location)
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = build_scene.aim(location, look_at or (0, 0, 0))
    return camera


def main(spec_path, out_dir):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    # Absolute, always: Blender resolves a relative render path against the blend
    # file, and with no blend file that lands at the drive root -- silently
    # writing C:\projects\... while reporting success.
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    duration = float(spec.get("duration", 5.0))

    objects = [(build_scene.add_object(o), o) for o in spec.get("objects", [])]
    build_scene.link_parents(objects)
    # Parented parts sit in their point's space, so their own matrices are
    # local; the bounds have to come from the evaluated world transforms.
    bpy.context.view_layer.update()
    built = [obj for obj, _ in objects]
    lo, hi = world_bounds(built) if built else (Vector((0, 0, 0)), Vector((1, 1, 1)))
    size = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z) or 1.0

    # Markers scale with the scene: 0.35 m is right for a room and invisible
    # across a 130 m street.
    draw_path(spec, duration, max(MARKER_SIZE, size * 0.004))

    centre = (lo + hi) / 2.0
    span_x, span_y, span_z = hi.x - lo.x, hi.y - lo.y, hi.z - lo.z
    margin = 1.12

    views = [
        ("top", add_camera(
            "view_top", (centre.x, centre.y, hi.z + size),
            ortho_scale=max(span_x, span_y) * margin,
            look_at=(centre.x, centre.y, lo.z))),
        ("front", add_camera(
            "view_front", (centre.x, lo.y - size, centre.z),
            ortho_scale=max(span_x, span_z) * margin,
            look_at=(centre.x, centre.y, centre.z))),
        ("side", add_camera(
            "view_side", (hi.x + size, centre.y, centre.z),
            ortho_scale=max(span_y, span_z) * margin,
            look_at=(centre.x, centre.y, centre.z))),
        ("three_quarter", add_camera(
            "view_3q",
            (hi.x + size * 0.6, lo.y - size * 0.6, hi.z + size * 0.5),
            look_at=(centre.x, centre.y, centre.z))),
    ]

    render_spec = spec.get("render", {})
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.show_shadows = False   # shadows read as geometry in an ortho plan
    shading.show_cavity = True
    shading.background_type = "VIEWPORT"
    shading.background_color = tuple(render_spec.get("background", [0.05, 0.05, 0.06]))
    scene.display.render_aa = "8"
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_file_extension = True

    for name, camera in views:
        scene.camera = camera
        scene.render.filepath = str(out_dir / f"view_{name}")
        bpy.ops.render.render(write_still=True)

    print("[ai_render] %d views -> %s" % (len(views), out_dir))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) != 2:
        raise SystemExit("usage: blender -b -P render_views.py -- <scene.json> <out_dir>")
    main(argv[0], argv[1])
