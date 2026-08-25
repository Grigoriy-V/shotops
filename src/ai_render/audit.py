"""Measure a camera move without rendering it.

The other half of the feedback loop in docs/design/feedback-loop.md. `views`
answers "where is everything" in pixels; this answers the questions pixels are
bad at -- how fast, how hard, how close -- in metres, from the same baked curve
the render uses.

It exists because of a specific failure. Retiming a move slides the path against
dressing that did not move with it, and a clearance that held before the change
did not hold after: the camera went through three parked cars, and nothing in a
grey blockout said so. Eight frames of contact sheet will not show a 5 m car the
camera is inside of, because from inside it there is nothing to see.

Nothing here needs Blender, so it is free and instant, and it can run before
every render rather than after a bad one.
"""

from __future__ import annotations

import math

from .interpolate import angle, animated, sample

# A stall is a dip in the middle of a move, not either end of one. The camera
# has to be travelling before it and travelling after it -- a shot that starts
# from rest or settles into its final frame is doing what it was asked to.
STALL_FRACTION = 0.10   # of the shot's median speed
MOVING_FRACTION = 0.50  # what counts as "travelling", either side of the dip


def _widest_scale(obj):
    """The largest scale the object ever reaches, per axis.

    An animated scale would otherwise be measured at whatever value it happens
    to hold in the static field. Taking the widest it gets keeps the clearance
    check conservative for the whole shot rather than correct for one frame.
    """
    scale = list(obj.get("scale", [1.0, 1.0, 1.0]))
    track = (obj.get("animation") or {}).get("scale")
    for key in track or []:
        scale = [max(s, abs(v)) for s, v in zip(scale, key["value"])]
    return scale


def _half_extents(obj):
    """Half the object's local bounding box, before rotation, after scale.

    Mirrors PRIMITIVES in blender/build_scene.py. If a primitive is added there
    it has to be added here too, or the audit quietly stops seeing it -- so an
    unknown type raises rather than defaulting to something plausible.
    """
    kind = obj.get("type", "cube")
    sx, sy, sz = _widest_scale(obj)

    if kind == "mesh":
        # Symmetric about the object origin, which is conservative when the
        # vertices are not: it can only make the box bigger, never smaller, and
        # a clearance that errs must err toward "too close".
        verts = obj.get("vertices") or [(0.0, 0.0, 0.0)]
        local = tuple(max(abs(v[axis]) for v in verts) for axis in range(3))
    elif kind == "cube":
        h = obj.get("size", 2.0) / 2.0
        local = (h, h, h)
    elif kind == "plane":
        h = obj.get("size", 10.0) / 2.0
        local = (h, h, 0.0)
    elif kind == "sphere":
        r = obj.get("size", 1.0)
        local = (r, r, r)
    elif kind in ("cylinder", "cone"):
        r = obj.get("size", 1.0)
        local = (r, r, obj.get("depth", 2.0) / 2.0)
    elif kind == "torus":
        outer = obj.get("size", 1.0) + obj.get("minor_radius", 0.25)
        local = (outer, outer, obj.get("minor_radius", 0.25))
    else:
        raise ValueError(f"audit does not know the bounds of type {kind!r}")

    return (local[0] * abs(sx), local[1] * abs(sy), local[2] * abs(sz))


def _rotated_extents(obj):
    """Half-extents of the axis-aligned box that contains the rotated object.

    Conservative for anything turned off-axis, exact for the multiples of 90
    degrees that primitives are actually placed at -- a wheel is a cylinder laid
    on its side. Erring outward is the right direction for a clearance check:
    it can report a gap that is really slightly larger, never one that is not
    there.
    """
    hx, hy, hz = _half_extents(obj)
    rx, ry, rz = (math.radians(a) for a in obj.get("rotation", [0.0, 0.0, 0.0]))
    if not (rx or ry or rz):
        return hx, hy, hz

    cx, sx_ = math.cos(rx), math.sin(rx)
    cy, sy_ = math.cos(ry), math.sin(ry)
    cz, sz_ = math.cos(rz), math.sin(rz)
    # Blender's XYZ euler: R = Rz @ Ry @ Rx.
    rot = (
        (cz * cy, cz * sy_ * sx_ - sz_ * cx, cz * sy_ * cx + sz_ * sx_),
        (sz_ * cy, sz_ * sy_ * sx_ + cz * cx, sz_ * sy_ * cx - cz * sx_),
        (-sy_, cy * sx_, cy * cx),
    )
    half = (hx, hy, hz)
    return tuple(sum(abs(rot[r][c]) * half[c] for c in range(3)) for r in range(3))


def _box_distance(point, centre, half):
    """Distance from a point to an axis-aligned box. Zero means inside."""
    total = 0.0
    for p, c, h in zip(point, centre, half):
        gap = abs(p - c) - h
        if gap > 0:
            total += gap * gap
    return math.sqrt(total)


def _direction(loc, target):
    dx, dy, dz = (t - l for t, l in zip(target, loc))
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-9:
        return (0.0, 1.0, 0.0)
    return (dx / length, dy / length, dz / length)


def path(spec):
    """The baked camera path, one entry per rendered frame.

    Sampled at exactly the frame times `bake()` uses, so this is the shot that
    will be rendered rather than a smooth approximation of it.
    """
    fps = int(spec.get("fps", 24))
    frames = max(1, round(float(spec.get("duration", 5.0)) * fps))
    cam = spec.get("camera", {})
    out = []
    for frame in range(1, frames + 1):
        t = (frame - 1) / fps
        loc = animated(cam, "location", t, [0, -10, 2])
        target = animated(cam, "look_at", t, [0, 0, 0])
        out.append({
            "t": t,
            "location": loc,
            "look_at": target,
            "direction": _direction(loc, target),
            "roll": angle(cam, "roll", t),
        })
    return out


def motion(points, fps):
    """Speed, acceleration and aim rate per frame, in metres and degrees."""
    for point in points:
        point["speed"] = 0.0
        point["accel"] = 0.0
        point["aim_rate"] = 0.0

    for i in range(1, len(points)):
        a, b = points[i - 1], points[i]
        step = math.dist(a["location"], b["location"])
        b["speed"] = step * fps
        dot = sum(x * y for x, y in zip(a["direction"], b["direction"]))
        b["aim_rate"] = math.degrees(math.acos(max(-1.0, min(1.0, dot)))) * fps
    if len(points) > 1:
        points[0]["speed"] = points[1]["speed"]

    for i in range(1, len(points)):
        points[i]["accel"] = (points[i]["speed"] - points[i - 1]["speed"]) * fps
    return points


def stalls(points):
    """Frames where the move stops dead in the middle and then carries on.

    The fault `smooth` easing was added to fix: a chain of eased keys arrives,
    halts and sets off again at every one of them. Both halves of that are the
    test. A camera pulling away from a standing start has not arrived anywhere,
    and one settling into its last frame does not carry on -- neither is the
    fault, and counting them would train the reader to ignore the report.
    """
    speeds = sorted(p["speed"] for p in points)
    if not speeds:
        return []
    median = speeds[len(speeds) // 2]
    if median <= 0:
        return []

    found = []
    run = None
    for i, point in enumerate(points):
        if point["speed"] < median * STALL_FRACTION:
            run = run or {"start": i, "end": i, "slowest": point["speed"]}
            run["end"] = i
            run["slowest"] = min(run["slowest"], point["speed"])
        elif run:
            found.append(run)
            run = None
    if run:
        found.append(run)

    moving = median * MOVING_FRACTION
    kept = []
    for run in found:
        arrives = any(p["speed"] > moving for p in points[:run["start"]])
        carries_on = any(p["speed"] > moving for p in points[run["end"] + 1:])
        if arrives and carries_on:
            run["t"] = points[run["start"]]["t"]
            run["seconds"] = points[run["end"]]["t"] - points[run["start"]]["t"]
            kept.append(run)
    return kept


def clearances(spec, points):
    """Closest approach from the camera to every object, and when it happened.

    Measured against the whole object rather than at the moment that looks
    tightest: the closest point of a 5 m car is often at its far end, where the
    camera has already begun to come back. Guessing that moment once left
    0.51 m where 0.90 was intended.
    """
    results = []
    for index, obj in enumerate(spec.get("objects", [])):
        half = _rotated_extents(obj)
        track = (obj.get("animation") or {}).get("location")
        resting = obj.get("location", [0.0, 0.0, 0.0])
        best = None
        for point in points:
            centre = sample(track, point["t"]) if track else resting
            distance = _box_distance(point["location"], centre, half)
            if best is None or distance < best["distance"]:
                best = {"distance": distance, "t": point["t"]}
        if best is not None:
            results.append({
                "name": obj.get("name", f"{obj.get('type', 'cube')}_{index}"),
                "distance": best["distance"],
                "t": best["t"],
            })
    results.sort(key=lambda r: r["distance"])
    return results


def report(spec, closest=8, per_second=True):
    """Everything above, as lines of text. Returns `(lines, penetrations)`."""
    fps = int(spec.get("fps", 24))
    points = motion(path(spec), fps)
    duration = points[-1]["t"] if points else 0.0
    lines = []

    travelled = sum(
        math.dist(points[i - 1]["location"], points[i]["location"])
        for i in range(1, len(points))
    )
    speeds = [p["speed"] for p in points]
    fastest = max(range(len(points)), key=lambda i: points[i]["speed"])
    hardest = max(range(len(points)), key=lambda i: abs(points[i]["accel"]))
    swiftest = max(range(len(points)), key=lambda i: points[i]["aim_rate"])

    lines.append(
        f"path      {len(points)} frames, {duration:.2f}s, {travelled:.1f} m travelled"
    )
    lines.append(
        f"speed     max {max(speeds):.1f} m/s at t={points[fastest]['t']:.2f}"
        f"  ({max(speeds) * 3.6:.0f} km/h), mean {sum(speeds) / len(speeds):.1f} m/s"
    )
    lines.append(
        f"accel     max |{points[hardest]['accel']:.0f}| m/s2 at t={points[hardest]['t']:.2f}"
    )
    lines.append(
        f"aim       max {points[swiftest]['aim_rate']:.0f} deg/s at t={points[swiftest]['t']:.2f}"
    )

    dips = stalls(points)
    if dips:
        for dip in dips:
            lines.append(
                f"STALL     t={dip['t']:.2f} for {dip['seconds']:.2f}s, "
                f"down to {dip['slowest']:.2f} m/s -- and then moves off again"
            )
    else:
        lines.append("stalls    none -- the move never stops and restarts")

    if per_second and duration >= 2.0:
        marks = []
        for second in range(int(duration) + 1):
            near = min(points, key=lambda p: abs(p["t"] - second))
            marks.append(f"{near['speed']:.0f}")
        lines.append("per sec   " + " ".join(marks) + "  m/s")

    gaps = clearances(spec, points)
    hits = [g for g in gaps if g["distance"] <= 0.0]
    for hit in hits:
        lines.append(f"INSIDE    {hit['name']} at t={hit['t']:.2f} -- the camera is in it")
    if gaps:
        lines.append(f"clearance closest {min(closest, len(gaps))} of {len(gaps)} objects:")
        for gap in gaps[:closest]:
            flag = "  <-- inside" if gap["distance"] <= 0.0 else ""
            lines.append(
                f"            {gap['distance']:6.2f} m  {gap['name']:<20} t={gap['t']:.2f}{flag}"
            )
    return lines, hits
