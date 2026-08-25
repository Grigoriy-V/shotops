# How the agent checks its own scene

*Decided 2026-08-24.*

The problem this answers: when the agent writes a config, it cannot see the
result. Something has to render, or the scene has to be inspected some other way,
before anyone knows whether the shot is right. The obvious candidate for fixing
that is an MCP bridge into a live Blender. This note records why we are not doing
that, and what we are doing instead.

## Measured first

Full loop on `demo_room`, cold start, wall clock:

| Step | Time |
| --- | --- |
| Blender launch | fractions of a second |
| build scene + render 120 frames + 8 stills + write files | **7.3 s total** |

Ten primitives, Workbench, 960×540, no GPU. The number matters because it
reframes the question:

**The feedback loop is not slow. It is blind.** MCP would save seconds out of
seven. Seconds out of seven is not the problem.

## What MCP would actually buy

Three distinct things, worth separating because only one of them is interesting:

**State without a rebuild.** Ask where an object is, move one thing, leave the
rest. At ten primitives a rebuild costs 7 s, so the saving is zero. At five
hundred objects with real geometry it stops being zero — this is the argument
that could change later.

**A viewport screenshot instead of a render.** Faster, but it is still pixels
that still need interpreting. The speed changes; the nature of the check does
not.

**Interactive surgery on a scene we did not author.** Open an unfamiliar `.blend`,
work out what is in it, fix it. MCP does this and a spec cannot. It is also not
our loop: here the scene is always ours and always derived from a spec.

Against that: a GUI session (the popular servers
[refuse `blender -b` by design](../research/agentic-blender.md)), accumulated
session state including every mistake made along the way, and the loss of
reproducibility. A spec produces the same scene from the same file. A live
session does not.

## What we do instead

### 1. Inspect — answers with no pixels at all

Half the questions currently costing a render are arithmetic over the spec, and
arithmetic gives exact answers rather than impressions:

- is the subject inside the frustum at **every** keyframe, not just the first and
  last
- what fraction of frame height does it occupy — is the shot scale actually held
- does the camera path pass through a wall
- do any two objects interpenetrate
- which screen side is each object on, and does it jump — screen direction
- does the camera cross the 180° line between shots

"The hero leaves frame for 60% of the shot" is caught more reliably by
computation than by looking at eight stills, most of which simply do not contain
him.

This is also the piece with no equivalent anywhere else: it is only possible
because shots are data.

**Built, 2026-08-25, as `audit`.** It bakes the camera path from the same
`interpolate.sample` the render uses -- a check evaluating a different curve
would be checking a different shot -- and reports speed, acceleration, aim rate,
stalls, and closest approach to every object's bounds. It exits non-zero on a
penetration, so it can gate a render rather than merely inform one.

The prompt for it was a real escape: retiming a move slid the path against
dressing that had not moved with it, and the camera ended up inside three parked
cars. A contact sheet does not show that, because from inside a car there is
nothing to see. The frustum half of the list above -- is the subject in frame,
what fraction of frame height, which screen side -- is not built yet.

**And is being held back deliberately.** Three of this shot's four failures were
framing, which makes the case for building it look overwhelming; that is exactly
the trap. Designed from the memory of a shot that had no subject, it would come
out as a check about empty walls and blank sky. A shot that genuinely needs it --
one with something in frame to keep in frame -- should pull it into existence and
decide its shape. See [method.md](method.md).

### 2. Multi-view — for what arithmetic cannot say

Extra views rendered in the same single Blender run, so the cost stays roughly
the 7 s we already pay: the shot camera, an orthographic top view with the camera
path drawn, front, and a three-quarter. The agent then sees **where things are
and where the camera goes**, which no single frame from inside the shot conveys.

An MCP viewport grab does not give this either — it gives one arbitrary angle of
whatever the session currently looks like.

### 3. Vision in the loop — only if the first two leave gaps

The [SceneCraft pattern](../research/agentic-blender.md#what-the-research-literature-says):
render, have a vision model look, patch the spec, repeat. Powerful and
non-deterministic. It is the right tool for "does this read well", the wrong tool
for "is the subject in frame", and it should not be reached for until the
deterministic checks are exhausted.

## Decision

**No MCP for scene authoring.** It does not improve the quality of the check, and
the rebuild speed it improves is not a bottleneck. Order of work: `inspect`
first (pure arithmetic, testable without Blender at all), multi-view second,
vision-in-the-loop only if something is still slipping through.

**Revisit when** scenes grow heavy enough that rebuild time is felt, or when the
project needs to work with `.blend` files it did not author. Both are real
futures, neither is today.

**Unrelated to this decision:** shotops could reasonably *expose* an MCP server
of its own — `check`, `render`, `takes`, `compare` are already validated
operations with no `exec()` anywhere near them. That is a distribution question,
not a scene-authoring one.
