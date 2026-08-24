"""Keyframe evaluation -- the one piece of scene semantics that is not Blender's.

Easing is baked here rather than handed to Blender f-curves, so the motion is
fully determined by the JSON and does not drift with Blender versions. That
makes it spec semantics rather than render code, which is why it lives in the
package instead of in `blender/`: the renderer is only one of the things that
needs to know where the camera is at t. An audit that measures the path has to
evaluate the *same* curve the render will, or it is measuring a different shot.

Stdlib only, and `blender/build_scene.py` imports it from inside Blender.
"""

from __future__ import annotations


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
    """Evaluate a keyframe track at time t (seconds). Returns a list of floats."""
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
    """One channel of an object or camera at time t: track if present, else static."""
    track = (spec.get("animation") or {}).get(channel)
    if track:
        return sample(track, t)
    return list(spec.get(channel, fallback))


def angle(spec, channel, t):
    """A width-1 channel as a plain number of degrees."""
    track = (spec.get("animation") or {}).get(channel)
    if track:
        return sample(track, t)[0]
    return float(spec.get(channel, 0.0))
