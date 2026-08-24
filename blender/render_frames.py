"""Runs INSIDE Blender:  blender -b -P render_frames.py -- <scene.json> <out_dir> [count]

Renders individual stills at exact positions through the shot, full size, one
file each.

Separate from the stills `build_scene.py` drops next to a take, which exist to be
tiled into a contact sheet and are a by-product of the render. These are the
input to something else: a style frame is generated *from* one of these, and the
image model sees whatever it is given -- so they are rendered directly rather
than pulled out of a compressed preview.

Positions are evenly spaced and always include the first and last frame: with
five, that is 0, 25, 50, 75 and 100 percent through the shot.

Same Blender-only constraint as build_scene.py: stdlib plus bpy.
"""

import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_scene  # noqa: E402

DEFAULT_COUNT = 5


def positions(count):
    """Normalised positions through the shot, first and last included."""
    if count <= 1:
        return [0.0]
    return [i / (count - 1) for i in range(count)]


def main(spec_path, out_dir, count=DEFAULT_COUNT):
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    # Absolute, always: Blender resolves a relative render path against the blend
    # file, and with no blend file that lands at the drive root.
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    fps = int(spec.get("fps", 24))
    frames = max(1, round(float(spec.get("duration", 5.0)) * fps))

    objects = [(build_scene.add_object(o), o) for o in spec.get("objects", [])]

    cam_spec = spec.get("camera", {})
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = cam_spec.get("lens", 35.0)
    cam_data.sensor_width = cam_spec.get("sensor_width", 36.0)
    camera = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera

    build_scene.bake(spec, objects, camera, fps, frames)
    # configure_render wants a video path; give it one inside out_dir that is
    # never written, then take the still settings back over.
    build_scene.configure_render(scene, spec, frames, out_dir / "unused.mp4")
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_file_extension = True
    # PNG is lossless either way; Blender just defaults to compressing lightly.
    # These get committed, and the pixels are identical at either setting.
    scene.render.image_settings.compression = 100

    made = []
    for position in positions(count):
        frame = 1 + round(position * (frames - 1))
        scene.frame_set(frame)
        # Named by position, not by index: the moment is what matters when one of
        # these gets picked to become a style frame, and it stays true if the
        # count ever changes.
        path = out_dir / ("t%03d" % round(position * 100))
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        made.append(path)

    print("[ai_render] %d frames -> %s" % (len(made), out_dir))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if len(argv) not in (2, 3):
        raise SystemExit(
            "usage: blender -b -P render_frames.py -- <scene.json> <out_dir> [count]"
        )
    main(argv[0], argv[1], int(argv[2]) if len(argv) == 3 else DEFAULT_COUNT)
