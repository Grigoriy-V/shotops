"""Runs INSIDE Blender:  blender -b -P extract_frames.py -- <video> <out_dir> [count]

Pulls evenly spaced stills out of a finished clip so the result can be compared
against the blockout frame for frame. That comparison is the core QA question of
this pipeline -- did the model actually honour the camera move, or did it invent
its own? -- and it needs no ffmpeg on PATH, since Blender decodes video itself.
"""

import sys
from pathlib import Path

import bpy


def main(video_path, out_dir, count):
    video_path = str(Path(video_path).resolve())
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # A movie clip is the reliable way to read a video's true dimensions and
    # length; the sequencer then does the actual decoding.
    clip = bpy.data.movieclips.load(video_path)
    width, height, frames = clip.size[0], clip.size[1], clip.frame_duration

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.sequence_editor_create()
    scene.sequence_editor.sequences.new_movie("clip", video_path, channel=1, frame_start=1)

    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.resolution_percentage = 100
    scene.render.use_sequencer = True
    scene.render.image_settings.file_format = "PNG"
    scene.frame_start = 1
    scene.frame_end = frames

    picks = sorted({1 + round(i * (frames - 1) / max(1, count - 1)) for i in range(count)})
    for index, frame in enumerate(picks, start=1):
        scene.frame_set(frame)
        scene.render.filepath = str(out_dir / f"frame_{index:02d}_")
        bpy.ops.render.render(write_still=True)

    print("[extract] %dx%d, %d frames -> %d stills in %s" % (width, height, frames, len(picks), out_dir))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if not 2 <= len(argv) <= 3:
        raise SystemExit("usage: blender -b -P extract_frames.py -- <video> <out_dir> [count]")
    main(argv[0], argv[1], int(argv[2]) if len(argv) > 2 else 8)
