# shotops

**Shots as source code.** An agent authors a 3D scene and camera as a config
file, Blender renders a grey blockout from it, and a video model turns that
blockout into the finished shot — so the shot has a diff, a history and a
revert, the way software does.

*Running it: [docs/usage.md](docs/usage.md). Writing a scene:
[docs/scene-spec.md](docs/scene-spec.md).*

## The artifact

| in — Blender blockout | out — Seedance 2 |
| --- | --- |
| ![blockout](docs/nyc-blockout.gif) | ![result](docs/nyc-result.gif) |

Ten seconds. A 104-object street built from primitives, and a 20mm camera that
runs 112 m down a dead end at 80 km/h, weaves twice past two cars at 0.95 m,
climbs a wall and crests a roof.

Left is rendered locally and costs nothing. The only authored input is
[`street_a.json`](projects/nyc/sequences/seq_010/sh_0010/street_a.json) — flat
grey boxes, cylinders and planes, and a camera with keyframes. Right came back
from the video model with the move, the timing and the staging intact.

Look at what is above the roof line at the end. There is no bay, no bridge and
no skyline anywhere in the geometry — the sky is empty and the camera is aimed
at nothing. All of it came from the prompt and held for the whole reveal. **A
backdrop that only appears at the end of a move does not have to be built.**

Full quality, not palette-reduced:
[blockout](projects/nyc/sequences/seq_010/sh_0010/preview/seq_010_sh_0010_street_a_64dd03_preview_v003.mp4) (859 KB),
[result](projects/nyc/sequences/seq_010/sh_0010/render/seq_010_sh_0010_street_a_64dd03_render_v003.mp4) (3.8 MB).
Frame-by-frame against the blockout at matched times:
[contact sheet](projects/nyc/sequences/seq_010/sh_0010/artifacts/seq_010_sh_0010_street_a_64dd03_sheet_v008_vs_render_v003.jpg).

### The second reference

The blockout owns motion, framing and where things are. It is told to own
nothing else, which leaves colour, light and material owned by nobody — so a
second reference takes them.

![look references](docs/nyc-lookrefs.jpg)

Three images, and **none of them is this street.** That is the point. The
obvious approach is to restyle the blockout's own first frame, so the two
references agree by construction; it contains a trap, and the trap cost a
generation. The still gets made before the dressing is settled, and then
contradicts it — two cars added to the road afterwards came back as raw white
boxes, because the look reference said the road was empty and the look reference
is what the model takes material from. References carrying only palette and
render style have nothing to disagree with.

Which needs saying in the prompt as well: the video is a guide for movement and
composition only, and appearance comes solely from the images. Without that
line, the model treats flat grey scaffolding as art direction.

*The three above are frames from a released animated feature — a look probe for
an R&D run, not a house style. They live in the shot as
[`styleframes/lookref_a..c.png`](projects/nyc/sequences/seq_010/sh_0010/styleframes).*

### What the cars settled

The two cars the camera threads at 0.95 m are the hardest thing in the shot, and
they are what fixed it. Each had been one cube. For this run each was eight
primitives — lower body, greenhouse set back from centre, raked windscreen,
steeper rear screen, four wheels on their sides — inside exactly the same
footprint. They come back as a yellow taxi and a dark saloon, with tail lights
and number plates.

*The scene has moved on since: the cabin is now a single deformed block, six
parts instead of eight, so the windscreen rake follows the footprint instead of
being a stored angle. The pair above is the run that was actually generated, and
it stays as it was until the next generation replaces both halves.*

**A primitive only has to look like its object at the distance it is seen from.**
Distance buys inference: a box in a row along a kerb reads as a parked car
because the street says so. Proximity spends it. Detail belongs where the camera
goes close, and nowhere else.

And the cars are authored *red*. They came back yellow and near-black, because
the look references decided. **Colour in a blockout is a marker, not a
specification** — it says *there is one object here and this is where it ends*,
so the prompt has something to point at. The run that did not release the model
from the marker kept the red and washed the entire frame in it.

Every run is logged with its provider response, cost and verdict in
[`generations.md`](projects/nyc/sequences/seq_010/sh_0010/generations.md);
what building the blockout taught is in
[`notes.md`](projects/nyc/sequences/seq_010/sh_0010/notes.md).

## Three strands

The project is early, and it is deliberately three things at once, because
separately none of them is worth much.

**1 — AI rendering, from blocking to generation.** Not a prompt-to-video toy: a
shot that starts as deliberate blocking and camera work, and ends as a generated
clip that obeys them.

**2 — Agents that drive Blender.** Scene, camera, lighting, render — built by an
agent, headless, no GUI in the loop. This works because the scene is a set of
configs. A spec is a far better target for a model than a viewport: it can be
written, checked, diffed and rewritten, and a wrong value is visible as text
before anything renders.

**3 — Studio pipeline infrastructure, with principles borrowed from IT.** The
part with the longest reach, and the subject of the next section.

## Why this exists

The generated clip is the visible half. The question underneath is older and
bigger: **can a film production pipeline be versioned the way software is?**

A studio pipeline already has structure — sequences, shots, tasks, publishes.
What it does not have is history you can read. **Commits in CG are effectively
binary.** You open ShotGrid, upload a render or a link to a file, write a
comment, and that is the whole record. You can see that `v012` exists and that it
looks different from `v011`. You cannot see *what changed*. That single missing
capability costs the rest of the model:

- **No diff.** "The camera is wrong now" starts a conversation, not a lookup.
- **No blame.** Nobody can say which change introduced the problem, or why it
  was made.
- **No revert.** Rolling back means restoring a whole file, losing every
  unrelated change that rode along in it.
- **No branch, no merge.** Two looks cannot exist at once, and two artists
  cannot touch one shot without one of them waiting.
- **No bisect.** A shot that regressed over twelve publishes is debugged by
  opening all twelve.

Software solved this by making the source text and treating everything else as
derived. That is the whole trick, and it transfers. **When the scene is a config
file, the shot inherits git.** A scene spec under `projects/` is source: camera
path, blocking, timing, look prompt. "Move the camera 20cm left" is a one-line patch with an
author and a reason attached. Two lighting directions are two branches. The
history of a shot is its commit log, and it is readable by a person who was not
in the room.

Everything downstream is derived and therefore disposable: the blockout render,
the generation, the stills. They are not versioned, they are *reproduced* — which
is why `out/` is gitignored, why each take stores the exact `scene.json` that
produced it, and why nothing is ever overwritten. An output you cannot trace back
to a spec is an output you cannot trust.

**Where this honestly stops.** Not everything in a pipeline reduces to text.
Models, caches, simulations, textures and plates are large and binary; no amount
of enthusiasm makes an Alembic file diffable. Though only *partly* binary, given
the right approach — a procedural asset is a recipe with parameters, and a
recipe is text. The claim is the narrow one: **version the recipe, not the
result.** The parts of a shot that are decisions — layout, camera, timing,
intent — are exactly the parts that are text-shaped, and they are also the parts
people argue about. This repo is the smallest end-to-end test of that idea: a
shot authored as config, rendered, generated, and reviewable as a diff.

## Who this is for

Not the large studio with a pipeline department and a decade of tooling. It is
for the places where the cost of the missing diff is felt directly:

**Small studios that want agents in production now.** No pipeline team, no
budget for one, and the most to gain from a shot being a file an agent can write
and a human can review.

**Previs, and the tender stage of large studios.** Both are judged on how fast an
idea becomes something watchable, and both routinely throw the result away. That
is exactly where a cheap, versioned, regenerable shot beats a careful one.

**And the oldest problem in the room: the art director who cannot say what they
want.** Not a complaint — it is genuinely easier to react than to specify. But
the cost is paid in weeks, by the people iterating blind. If they can talk to an
agent and watch finished-looking AI renders come back at the blocking stage, the
specification happens where it is cheap, against something concrete, before real
production is committed.

## Where this goes

The end state is a full pipeline platform for a small studio: idea → blocking →
generation → edit, with logs, provenance and time analysis in the same substrate
as the work. Not there. What exists today is one honest vertical slice: a shot
authored as JSON, rendered locally, generated with structure held, and every take
traceable to the spec that produced it.

## Prior art

The idea of a diffable, branchable JSON previs project is not new —
[`blockout`](https://github.com/wassermanproductions/blockout) (Apache-2.0) got
there first, from the GUI side. What is distinct here is that the spec is written
by an agent, validated before anything renders, and every output traces back to
the exact spec that produced it.

[`docs/research/`](docs/research/) carries the survey: who else is building this,
which models actually honour a blockout, the blocking craft that decides a shot,
and why agentic Blender work splits into MCP for the viewport and specs for the
pipeline. [`docs/design/`](docs/design/) records decisions that came out of it —
starting with [how the agent checks its own
scene](docs/design/feedback-loop.md).
[`docs/craft/modelling.md`](docs/craft/modelling.md) is the working set of rules
for building geometry a video model can read, each one linked to the experiment
that produced it.

## How it fits together

```
projects/**/<scene>.json ─▶ Blender (headless) ─▶ out/<project>/<seq>/<shot>/<scene>/<take>/preview.mp4
                                                   .../frames/*.png
                                                    │
                                     Supabase Storage (signed URL, then deleted)
                                                    │
                                                    ▼
                                   Seedance via PiAPI (omni_reference)
                                                    │
                                                    ▼
                                            .../<generation>/final.mp4
```

The upload hop is not optional: Seedance takes reference **videos** by URL only.
Images and audio can go inline as base64, video cannot. The blockout goes to your
own bucket under a random key, is passed as a signed URL with a TTL, and is
deleted as soon as the job finishes — including when it fails.

## Why this shape

**The scene spec is the product.** The scene spec is what the agent actually
writes: declarative, diffable, editable field by field. "Move the camera 20cm
left" is a one-line patch, not a regeneration. Blender, the video model, and any
future viewer are all just consumers of that file.

**The blockout is deliberately ugly.** Flat grey, no textures, studio light.
Seedance 2.5's white-model control is documented to work best this way — with no
texture or lighting to distract it, the model reads pure trajectory, framing and
speed off the reference. Rendering pretty would cost time and make results worse.

**Easing is baked in Python, not in f-curves.** `sample()` in
`blender/build_scene.py` evaluates every channel per frame before handing keys to
Blender. Motion is therefore fully determined by the JSON and does not drift
between Blender versions, and camera aim can never gimbal-flip mid-shot.

**The provider is one method wide.** The video model is the fastest-moving piece
of this stack. Swapping Seedance for Runway/Kling/Wan means adding a file in
`src/ai_render/providers/`, not touching the scene layer.

## Honest video-to-video, or nothing

Seedance has native white-model control: hand it a grey blockout clip and it
reads camera trajectory, framing and timing off it. That is the entire point of
this pipeline, and it is the only mode pursued here.

`reference_mode: "video"` — posting the blockout mp4 — is therefore the default,
and **there is no automatic fallback.** Degrading to stills would return a
plausible-looking clip that silently ignores the camera move, which is worse than
a clear failure. If a gateway will not attach a video reference, the fix is a
different gateway, not a quieter version of this one. That is exactly how this
repo ended up on PiAPI — the comparison is in
[usage.md](docs/usage.md#why-the-provider-is-piapi).

`frames` (N stills as `@image1..N`) and `first` stay implemented but
unexercised, for the day a storyboard-shaped reference is genuinely wanted.
`render` writes the stills regardless: they cost 8 frames out of 120 and are the
fastest way to eyeball a blockout without scrubbing video.


## How this gets built

Two days old, one shot built. The rule we work by is that **the example comes
first and the tool is extracted from it** — not the other way round. Every tool
in here arrived because a shot demanded it: `smooth` easing because a flight
stopped dead at every keyframe, `audit` because a retiming drove the camera
through three cars, assets and instances because sixty-four baked objects turned
a one-line change into sixty-four edits.

The cost of that honesty is that **n = 1**, and the repository says so. Some of
what exists is general and some is the shape of one fast camera in one dense
street, and [method.md](docs/design/method.md) keeps the two apart in a table
that is meant to be edited as a second shot proves things.

The core stays small on purpose. Projects and shots will need their own checks
long before those checks are general, so they get somewhere to live outside the
core and a way to be promoted into it once a third shot writes the same one —
[core-and-extensions.md](docs/design/core-and-extensions.md).

## Where everything is

| | |
| --- | --- |
| [docs/usage.md](docs/usage.md) | Setup, the commands, output layout, cost |
| [docs/scene-spec.md](docs/scene-spec.md) | The spec format, field by field |
| [docs/craft/modelling.md](docs/craft/modelling.md) | How to build geometry a video model can read, with the experiment behind each rule |
| [docs/design/](docs/design/) | Decisions and their reasoning — structure, method, extensions, the feedback loop |
| [docs/research/](docs/research/) | The survey: prior art, which models honour a blockout, blocking craft |
| [AGENTS.md](AGENTS.md) | Working agreements for anyone, human or agent, changing this repo |
| `projects/<proj>/.../<shot>/notes.md` | What building that particular shot taught |
| `projects/<proj>/.../<shot>/generations.md` | One entry per paid run: setup, cost, what held, what broke |
