# Camera orientation: aim, and the angle on top of it

*Proposed 2026-08-24. Not implemented — this is a design note awaiting a
decision.*

## The gap

Camera orientation is currently derived entirely from `look_at`:

```python
quat = direction.to_track_quat("-Z", "Y")
```

That is a good authoring model — an aim point is far easier to write and to
reason about than a rotation — but it fixes two things the director does not get
to choose:

**Roll is always zero.** `to_track_quat` produces the horizon-level solution.
A camera cannot bank into a turn, which is a large part of the language of a
flight shot: banking is what separates a body thrown through a street from a
drone on autopilot.

**The subject is always dead centre.** The aim point *is* the frame centre, so
there is no way to place a subject in the lower third, or to lead a move by
looking slightly ahead of where the camera is going.

## Proposal: three scalar offsets on top of the aim

Keep `look_at` as the primary control. Add three optional angles, in degrees,
applied to the camera's own axes *after* the aim:

| Channel | Axis | Meaning |
| --- | --- | --- |
| `roll` | local Z (the view axis) | bank; positive rolls one way, sign fixed at implementation |
| `pan` | local Y | swing the aim left/right off the target |
| `tilt` | local X | swing the aim up/down off the target |

Each is a single number, static or animated, defaulting to 0. Absent means
absent — every existing scene renders identically.

```jsonc
"camera": {
  "lens": 20.0,
  "location": [0, -120, 1.4],
  "look_at": [0, 0, 1.4],
  "roll": -6.0,                       // static bank
  "animation": {
    "roll": [                         // or animated
      { "t": 0.0, "value": [0] },
      { "t": 1.6, "value": [-14] },
      { "t": 3.2, "value": [12] }
    ]
  }
}
```

**Three scalars rather than one `[pitch, yaw, roll]` triple** — deliberately.
Most shots animate roll alone, and a one-number channel is a one-line diff.
Bundling all three would make every bank edit touch a vector, which is exactly
the kind of noise this project exists to avoid. `lens` already sets the
precedent for a width-1 channel.

## Mechanics

Composition is a right-multiply, so the offsets act in the camera's local frame
rather than the world's:

```
q = q_aim · q_pan(Y) · q_tilt(X) · q_roll(Z)
```

Order matters and this one is conventional: swing the aim first, bank last, so
roll does not drag the aim around with it.

The existing hemisphere-keeping check must run **after** composition, not before,
or a bank crossing 180° can still flip the shot mid-move.

## What it touches

- `spec.py` — three entries in `CHANNEL_WIDTH` at width 1, and static-value
  validation alongside `location` / `look_at`
- `build_scene.py` — read static or animated values in `bake()`, compose, then
  hemisphere-check
- `README.md` — the scene-spec section, and a note that the angles are degrees
- tests — composition maths is checkable without Blender: aim at a target with
  `roll: 90` and assert the up-vector has rotated, assert `0` is identical to
  absent

## Why now

The NYC flight shot needs `roll` to read as flight rather than as a camera rig.
The other two are not needed by that shot, but they close the same hole, cost
almost nothing once the composition exists, and are the difference between "aim
at a point" and "frame a shot".
