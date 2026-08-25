"""Tile several clips into one video, so takes can be compared moving.

The contact sheet in `compare.py` answers "is the camera where the blockout puts
it at 43%", and it answers it well: a wrong camera is obvious in one column.
It cannot answer "which of these three is cleaner". Texture, stylisation and
temporal noise do not survive being sampled sixteen times, and by the time
several runs all hold the blockout, those are the only things left to judge.
Watching them one after another does not work either -- the gap between two
playbacks is long enough to forget what the first one looked like.

So: one file, clips side by side, playing together.

Two things are normalised, both for the same reason the sheet samples by
position rather than by frame number. **Time** is scaled so t = 50% is the same
moment in every cell, because a blockout and a generation need not agree on
duration -- H3 aligns output to its own frame grid and comes back 3 frames
longer than the 10-second blockout it was given. **Aspect** is preserved and
padded rather than stretched, because these clips genuinely differ: 16:9 out of
Blender against H3's 7:4 canvas.

Audio is dropped. Three generations playing their invented city ambience at
once is noise, not evidence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

LABEL_H = 26
BG_HEX = "0x121214"
BG_RGB = (18, 18, 20)
FG = (235, 235, 235)


def find_ffmpeg(name="ffmpeg"):
    """Locate ffmpeg, which is not on PATH on the machine this was written for."""
    override = os.environ.get("AI_RENDER_FFMPEG")
    if override:
        candidate = Path(override)
        # Accept either the binary itself or the directory holding it.
        if candidate.is_dir():
            candidate = candidate / name
        for path in (candidate, candidate.with_suffix(".exe")):
            if path.is_file():
                return str(path)
        raise RuntimeError(f"AI_RENDER_FFMPEG is set but {name} is not at {override}")

    found = shutil.which(name)
    if found:
        return found

    for base in (r"C:\ffmpeg\bin", r"C:\Program Files\ffmpeg\bin", "/usr/bin", "/usr/local/bin"):
        for path in (Path(base) / name, Path(base) / f"{name}.exe"):
            if path.is_file():
                return str(path)
    raise RuntimeError(
        f"{name} not found. Put it on PATH, or set AI_RENDER_FFMPEG to its "
        "directory (or to the binary itself)."
    )


def probe(clip):
    """Duration and pixel size of a clip's first video stream."""
    out = subprocess.run(
        [
            find_ffmpeg("ffprobe"), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", str(clip),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    data = json.loads(out)
    streams = data.get("streams") or []
    if not streams:
        raise RuntimeError(f"no video stream in {clip}")
    duration = float((data.get("format") or {}).get("duration") or 0.0)
    if duration <= 0:
        raise RuntimeError(f"could not read a duration from {clip}")
    return duration, int(streams[0]["width"]), int(streams[0]["height"])


def _labels_png(labels, columns, cell_w, cell_h, out_path):
    """One transparent overlay carrying every cell's caption.

    Drawn with PIL rather than ffmpeg's `drawtext`, which needs a font path
    escaped through two levels of filter syntax and is miserable on Windows.
    """
    from PIL import Image, ImageDraw

    from .compare import _load_font

    rows = (len(labels) + columns - 1) // columns
    image = Image.new("RGBA", (columns * cell_w, rows * (cell_h + LABEL_H)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = _load_font(15)
    for index, text in enumerate(labels):
        col, row = index % columns, index // columns
        x = col * cell_w
        y = row * (cell_h + LABEL_H)
        draw.rectangle([x, y, x + cell_w, y + LABEL_H], fill=(*BG_RGB, 255))
        draw.text((x + 8, y + 5), text, fill=FG, font=font)
    image.save(out_path)
    return out_path


def build(clips, out_path, columns=2, cell_width=672, fps=24, crf=18):
    """Tile `clips` -- (path, label) pairs -- into one video at `out_path`."""
    clips = [(Path(p), str(label)) for p, label in clips]
    if not clips:
        raise RuntimeError("nothing to tile")
    missing = [p for p, _ in clips if not p.is_file()]
    if missing:
        raise RuntimeError("missing clip(s): " + ", ".join(str(p) for p in missing))

    probed = [probe(p) for p, _ in clips]
    target = max(duration for duration, _, _ in probed)
    # Cell shape follows the widest source aspect, so the clip that defines it
    # is not the one that gets padded.
    aspect = max(width / height for _, width, height in probed)
    cell_h = round(cell_width / aspect / 2) * 2
    cell_full_h = cell_h + LABEL_H

    parts = []
    for index, (duration, _, _) in enumerate(probed):
        # Scale time so the same fraction of each clip plays at the same
        # instant; without it a 3-frame difference in length silently becomes a
        # 3-frame difference in what is being compared.
        stretch = target / duration
        parts.append(
            f"[{index}:v]setpts=PTS*{stretch:.9f},fps={fps},"
            f"scale={cell_width}:{cell_h}:force_original_aspect_ratio=decrease,"
            f"pad={cell_width}:{cell_h}:(ow-iw)/2:(oh-ih)/2:color={BG_HEX},"
            f"pad={cell_width}:{cell_full_h}:0:{LABEL_H}:color={BG_HEX}[c{index}]"
        )

    inputs = "".join(f"[c{i}]" for i in range(len(clips)))
    layout = "|".join(
        f"{(i % columns) * cell_width}_{(i // columns) * cell_full_h}"
        for i in range(len(clips))
    )
    parts.append(f"{inputs}xstack=inputs={len(clips)}:layout={layout}:fill={BG_HEX}[grid]")
    parts.append(f"[grid][{len(clips)}:v]overlay=0:0,format=yuv420p[out]")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    overlay = out_path.with_suffix(".labels.png")
    _labels_png([label for _, label in clips], columns, cell_width, cell_h, overlay)

    command = [find_ffmpeg(), "-y", "-v", "error"]
    for path, _ in clips:
        command += ["-i", str(path)]
    command += [
        "-i", str(overlay),
        "-filter_complex", ";".join(parts),
        "-map", "[out]",
        "-an",
        "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
        str(out_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpeg failed:\n{exc.stderr.strip()[:2000]}") from None
    finally:
        overlay.unlink(missing_ok=True)
    return out_path
