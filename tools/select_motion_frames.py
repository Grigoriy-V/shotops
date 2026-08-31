"""Keep a motion-weighted subset of an extracted frame sequence.

The selection is deliberately sparse where a camera is slow and dense around
its fastest section.  It is a manual velocity model, not optical-flow analysis:
use ``--power`` to increase the middle bias and ``--center`` to move the dense
region along the clip.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def biased_positions(
    total: int,
    keep: int,
    power: float = 3.0,
    center: float = 0.5,
    linear_mix: float = 0.0,
) -> list[int]:
    """Return ``keep`` distinct zero-based indices, including both endpoints.

    A power of 1 is uniform.  Values above 1 make the mapping flat at
    ``center``: successive kept frames are closer there and farther apart at
    the beginning and end. ``linear_mix`` (0..1) retains a minimum central
    step: 0 is the full curve, while 1 is uniform selection.
    """
    if total < 1:
        raise ValueError("the sequence contains no frames")
    if not 1 <= keep <= total:
        raise ValueError(f"--keep must be from 1 to {total}, got {keep}")
    if power < 1:
        raise ValueError("--power must be at least 1 (1 means uniform selection)")
    if not 0 < center < 1:
        raise ValueError("--center must be strictly between 0 and 1")
    if not 0 <= linear_mix <= 1:
        raise ValueError("--linear-mix must be from 0 to 1")
    if keep == 1:
        return [0]

    proposed: list[int] = []
    for sample in range(keep):
        u = sample / (keep - 1)
        if u <= 0.5:
            fraction = center * (1 - (1 - 2 * u) ** power)
        else:
            fraction = center + (1 - center) * (2 * u - 1) ** power
        fraction = linear_mix * u + (1 - linear_mix) * fraction
        proposed.append(round(fraction * (total - 1)))

    # A simple left-to-right repair of duplicate rounded positions would push
    # the dense region later in the clip.  Resolve once from each direction,
    # then meet in the middle so ``--center`` stays where it says it is.
    forward: list[int] = []
    for sample, value in enumerate(proposed):
        minimum = forward[-1] + 1 if forward else 0
        maximum = total - (keep - sample)
        forward.append(max(minimum, min(value, maximum)))
    backward = [0] * keep
    for sample in range(keep - 1, -1, -1):
        minimum = sample
        maximum = backward[sample + 1] - 1 if sample + 1 < keep else total - 1
        backward[sample] = min(maximum, max(proposed[sample], minimum))

    positions: list[int] = []
    for sample, (left, right) in enumerate(zip(forward, backward)):
        value = round((left + right) / 2)
        minimum = positions[-1] + 1 if positions else 0
        maximum = total - (keep - sample)
        positions.append(max(minimum, min(value, maximum)))
    return positions


def image_frames(folder: Path) -> list[Path]:
    return sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def select(
    source: Path,
    output: Path,
    keep: int,
    power: float,
    center: float,
    linear_mix: float,
    overwrite: bool,
) -> list[Path]:
    frames = image_frames(source)
    indices = biased_positions(len(frames), keep, power, center, linear_mix)
    output.mkdir(parents=True, exist_ok=True)
    chosen = [frames[index] for index in indices]
    collisions = [output / frame.name for frame in chosen if (output / frame.name).exists()]
    if collisions and not overwrite:
        names = ", ".join(path.name for path in collisions[:3])
        raise FileExistsError(f"output already contains selected frame(s): {names}; use --overwrite")
    for frame in chosen:
        shutil.copy2(frame, output / frame.name)
    manifest = {
        "source": str(source.resolve()),
        "source_frame_count": len(frames),
        "kept_frame_count": len(chosen),
        "power": power,
        "center": center,
        "linear_mix": linear_mix,
        "selected": [
            {"source_index": index + 1, "file": frames[index].name}
            for index in indices
        ],
    }
    (output / "selection.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="directory containing extracted image frames")
    parser.add_argument("--keep", type=int, required=True, help="number of frames to retain")
    parser.add_argument("--output", type=Path, help="destination directory (default: <source>_selected_<keep>)")
    parser.add_argument("--power", type=float, default=3.0, help="middle-density curve; 1 is uniform, higher removes more at the ends")
    parser.add_argument("--center", type=float, default=0.5, help="0..1 location of the fastest part of the move")
    parser.add_argument("--linear-mix", type=float, default=0.0, help="0..1 blend with uniform selection; raises the minimum central spacing")
    parser.add_argument("--overwrite", action="store_true", help="replace same-named selected frames in the output")
    args = parser.parse_args()

    source = args.source.resolve()
    if not source.is_dir():
        parser.error(f"source is not a directory: {source}")
    output = (args.output or source.with_name(f"{source.name}_selected_{args.keep}")).resolve()
    chosen = select(source, output, args.keep, args.power, args.center, args.linear_mix, args.overwrite)
    print(f"[select] {len(chosen)} of {len(image_frames(source))} frames -> {output}")
    print(f"[select] power={args.power:g}, center={args.center:g}, linear_mix={args.linear_mix:g}; first={chosen[0].name}, last={chosen[-1].name}")


if __name__ == "__main__":
    main()
