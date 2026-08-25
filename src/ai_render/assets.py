"""Assets and instances: version the recipe, not the bake.

Eight cars built from eight primitives each landed in the scene as sixty-four
objects with the rule that made them thrown away. Every number in them was a
fraction of the car's own footprint -- a roof 0.76 as wide as the body, wheels
at 0.235 of the height -- and none of that survived into the file. Changing the
windscreen rake meant editing sixty-four blocks by hand, which is the exact
thing this project claims to be against.

An **asset** is that rule, written down: parts declared in the unit space of a
bounding box. An **instance** places one at a location, at a size, facing a
direction. Expansion multiplies the two together.

    projects/<proj>/assets/sedan.json     the recipe
    "instances": [{"asset": "sedan", ...}]  in a scene

Unit space, which is the whole of the convention:

- `location` -- x and y are fractions of width and length, measured from the
  instance origin. z is a fraction of height, measured **up from the origin**,
  because a car sits on a road rather than floating around its own centre.
- `scale` -- fractions of [width, length, height].
- `size`, `depth`, `minor_radius` -- scalars, so each is scaled by one named
  axis. `size` follows height and `depth` follows width by default, which is
  what a wheel wants: a radius set by how tall the car is and a tread width set
  by how wide. Override with `size_from` / `depth_from`. The exception is `size`
  on a cube or a plane, where it is the base edge `scale` already multiplies and
  is passed through untouched.
- `rotation` -- degrees, as authored. Not scaled, and that is a real limit: see
  below.

**Non-uniform size skews a rotated part.** A windscreen raked 34.8 degrees on a
4.6 m car wants 33.3 on a 5.2 m one, because the rake is set by rise over run.
An asset stores one angle, so wider or longer instances are a degree or two out.
Nothing here can fix that while a raked pane is a rotated box; a part whose
polygons are placed in unit space would get it for free.

Expansion happens once, in `project.load_spec`, so Blender, `audit` and `check`
all measure the same geometry. Anything that expanded separately would be
measuring a different shot -- the same mistake the interpolation once made.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

# Which axis of the instance size scales each scalar field, unless the part
# says otherwise. Height for radii, width for depth: a wheel on a taller car is
# a bigger wheel, and on a wider car it is a wider tyre.
SCALAR_AXIS = {"size": "z", "depth": "x", "minor_radius": "z"}
AXES = {"x": 0, "y": 1, "z": 2}

# On a cube or a plane, `size` is the base edge that `scale` then multiplies, so
# scaling it here would apply the instance twice. On the round primitives it is
# a radius and there is no other way to set one, so it is a unit fraction like
# everything else. This follows the primitives rather than tidying over them:
# `size` has always meant two different things, and pretending otherwise would
# silently make every boxed part the wrong size.
FLAT_SIZE_TYPES = {"cube", "plane"}


class AssetError(ValueError):
    """Raised when an instance cannot be expanded into objects."""


def _load(assets_dir, name, cache):
    if name in cache:
        return cache[name]
    if assets_dir is None:
        raise AssetError(
            f"instance uses asset {name!r}, but this scene is not inside a project, "
            "so there is no assets/ directory to look in"
        )
    path = Path(assets_dir) / f"{name}.json"
    if not path.exists():
        raise AssetError(f"no asset {name!r} at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    parts = data.get("parts")
    if not isinstance(parts, list) or not parts:
        raise AssetError(f"asset {name!r} has no 'parts' list")
    cache[name] = data
    return data


def _yaw(instance):
    """The instance's turn about Z, in degrees.

    Z only, on purpose. A yaw composes exactly with a part's own XYZ euler --
    `Rz(a) @ Ry(b) @ Rx(c)` is itself an XYZ euler with z = a -- so a car can be
    turned to face the other kerb without any quaternion work. A general
    rotation would not compose that way, and a wrong composition is invisible in
    a grey render and obvious in the result.
    """
    rotation = instance.get("rotation", [0.0, 0.0, 0.0])
    if len(rotation) != 3:
        raise AssetError(f"instance rotation must be three numbers, got {rotation!r}")
    if abs(rotation[0]) > 1e-9 or abs(rotation[1]) > 1e-9:
        raise AssetError(
            "an instance can only be turned about Z, got "
            f"{rotation!r}. Rotate the parts inside the asset instead."
        )
    return float(rotation[2])


def _compose(part_rotation, yaw, part_name):
    """Add the instance's yaw to a part's own rotation, exactly or not at all."""
    rx, ry, rz = (float(a) for a in part_rotation)
    if abs(yaw) < 1e-9:
        return [rx, ry, rz]
    # Rz(yaw) @ Rz(rz) @ Ry(ry) @ Rx(rx) is an XYZ euler with z = yaw + rz only
    # when there is nothing between the two Z turns to spoil it.
    if abs(rz) > 1e-9 and (abs(rx) > 1e-9 or abs(ry) > 1e-9):
        raise AssetError(
            f"part {part_name!r} turns about Z as well as X or Y, so an instance "
            "yaw cannot be folded into it. Bake the yaw into the asset, or drop "
            "the part's own Z rotation."
        )
    return [rx, ry, rz + yaw]


def expand(spec, assets_dir):
    """Return `spec` with its `instances` turned into ordinary objects.

    The instance list is consumed: what comes out is a spec every other part of
    the pipeline already understands, so nothing downstream needs to know assets
    exist.
    """
    instances = spec.get("instances")
    if not instances:
        return spec

    cache = {}
    made = []
    for index, instance in enumerate(instances):
        name = instance.get("name") or f"instance_{index:02d}"
        asset_name = instance.get("asset")
        if not asset_name:
            raise AssetError(f"instance {name!r} names no asset")
        asset = _load(assets_dir, asset_name, cache)

        size = instance.get("size", [1.0, 1.0, 1.0])
        if len(size) != 3:
            raise AssetError(f"instance {name!r} size must be three numbers, got {size!r}")
        size = [float(v) for v in size]
        origin = [float(v) for v in instance.get("location", [0.0, 0.0, 0.0])]
        yaw = _yaw(instance)
        cos, sin = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

        for part in asset["parts"]:
            part_name = part.get("name", "part")
            obj = {k: v for k, v in part.items() if k not in ("name", "size_from", "depth_from")}
            obj["name"] = f"{name}_{part_name}"

            unit = part.get("location", [0.0, 0.0, 0.0])
            local = [unit[0] * size[0], unit[1] * size[1], unit[2] * size[2]]
            # The yaw turns the part's offset around the instance origin; Z is
            # untouched because the turn is about Z.
            obj["location"] = [
                origin[0] + local[0] * cos - local[1] * sin,
                origin[1] + local[0] * sin + local[1] * cos,
                origin[2] + local[2],
            ]

            if "scale" in part:
                # Object space, so the yaw carries it into place -- a car turned
                # 90 degrees is still as wide as it was.
                obj["scale"] = [part["scale"][i] * size[i] for i in range(3)]

            flat = part.get("type", "cube") in FLAT_SIZE_TYPES
            for field, default_axis in SCALAR_AXIS.items():
                if field in part and not (field == "size" and flat):
                    axis = part.get(f"{field}_from", default_axis)
                    if axis not in AXES:
                        raise AssetError(
                            f"part {part_name!r}: {field}_from must be x, y or z, got {axis!r}"
                        )
                    obj[field] = part[field] * size[AXES[axis]]

            obj["rotation"] = _compose(part.get("rotation", [0.0, 0.0, 0.0]), yaw, part_name)
            made.append(obj)

    expanded = dict(spec)
    expanded.pop("instances")
    expanded["objects"] = list(spec.get("objects", [])) + made
    return expanded
