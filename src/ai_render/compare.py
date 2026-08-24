"""Build a side-by-side contact sheet: blockout on top, result below.

Sparse stills invite bad readings. Eight frames cannot settle how far an object
rotated, and eyeballing two folders in an image viewer makes it far too easy to
line up frame 5 against frame 8 and call it a match -- which is exactly the
mistake this module exists to stop.

Both clips are sampled at the same normalised positions across their full
length, so column N is the same moment in both. The sheet labels each column
with that position, and puts the pair in one image so there is nothing to
misalign.
"""

from __future__ import annotations

from pathlib import Path

LABEL_H = 22
GAP = 6
BG = (18, 18, 20)
FG = (235, 235, 235)


def _load_font(size=14):
    from PIL import ImageFont

    for name in ("DejaVuSans.ttf", "arial.ttf", "segoeui.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _frames(folder):
    frames = sorted(Path(folder).glob("frame_*.png"))
    if not frames:
        raise RuntimeError(f"no frame_*.png in {folder}")
    return frames


def grid(paths, out_path, columns=2, cell_width=560, labelled=False):
    """Tile images into one sheet.

    Separate from `build` on purpose: that one exists to make a specific
    comparison impossible to get wrong, and adding modes to it would blunt it.
    This one just tiles -- views of a scene, stills of a take -- and saves as
    JPEG, because these live in the repository and get committed.
    """
    from PIL import Image, ImageDraw

    paths = [Path(p) for p in paths]
    if not paths:
        raise RuntimeError("nothing to tile")

    cells = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        height = round(image.height * cell_width / image.width)
        cells.append((image.resize((cell_width, height), Image.LANCZOS), path.stem))

    cell_h = max(c.height for c, _ in cells)
    rows = (len(cells) + columns - 1) // columns
    label_h = LABEL_H if labelled else 0
    width = columns * cell_width + (columns + 1) * GAP
    height = rows * (cell_h + label_h + GAP) + GAP

    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    font = _load_font()

    for index, (image, name) in enumerate(cells):
        col, row = index % columns, index // columns
        x = GAP + col * (cell_width + GAP)
        y = GAP + row * (cell_h + label_h + GAP)
        if labelled:
            draw.text((x, y + 3), name, fill=FG, font=font)
        sheet.paste(image, (x, y + label_h))

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=88, optimize=True)
    return out_path


def build(blockout_dir, result_dir, out_path, column_width=340):
    from PIL import Image, ImageDraw

    top = _frames(blockout_dir)
    bottom = _frames(result_dir)
    if len(top) != len(bottom):
        raise RuntimeError(
            f"frame counts differ: {len(top)} in {blockout_dir}, {len(bottom)} in {result_dir}. "
            "Re-extract both with the same --count, or the columns will not line up."
        )

    def scaled(path):
        image = Image.open(path).convert("RGB")
        height = round(image.height * column_width / image.width)
        return image.resize((column_width, height), Image.LANCZOS)

    tops = [scaled(p) for p in top]
    bottoms = [scaled(p) for p in bottom]
    row_h_top = max(i.height for i in tops)
    row_h_bottom = max(i.height for i in bottoms)

    columns = len(tops)
    width = columns * column_width + (columns + 1) * GAP
    height = LABEL_H + row_h_top + GAP + row_h_bottom + LABEL_H + 2 * GAP

    sheet = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    font = _load_font()

    for index, (a, b) in enumerate(zip(tops, bottoms)):
        x = GAP + index * (column_width + GAP)
        # Position through the shot, not a frame number: the two clips can have
        # different frame counts and still be compared honestly.
        position = index / max(1, columns - 1)
        draw.text((x, 4), f"t = {position * 100:.0f}%", fill=FG, font=font)
        sheet.paste(a, (x, LABEL_H))
        sheet.paste(b, (x, LABEL_H + row_h_top + GAP))

    label_y = LABEL_H + row_h_top + GAP + row_h_bottom + GAP
    draw.text((GAP, label_y), "top: blockout    bottom: result", fill=FG, font=font)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    return out_path
