# shotops

**Shots as source code.** An agent authors a 3D scene and camera as a config
file, Blender renders a grey blockout from it, and a video model turns that
blockout into the finished shot — so the shot has a diff, a history and a
revert, the way software does.

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
they are what fixed it. Each was one cube; each is now eight primitives — lower
body, greenhouse set back from centre, raked windscreen, steeper rear screen,
four wheels on their sides — inside exactly the same footprint. They come back
as a yellow taxi and a dark saloon, with tail lights and number plates.

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
repo ended up on PiAPI; see below.

`frames` (N stills as `@image1..N`) and `first` stay implemented but
unexercised, for the day a storyboard-shaped reference is genuinely wanted.
`render` writes the stills regardless: they cost 8 frames out of 120 and are the
fastest way to eyeball a blockout without scrubbing video.

## Setup

**Blender 4.5 LTS.** Either install it normally, or unpack the portable build
into `.tools/` (gitignored) — the pipeline finds it there first, which pins it to
a known version without touching the system. `AI_RENDER_BLENDER` overrides both.

```bash
curl -L -o blender.zip https://download.blender.org/release/Blender4.5/blender-4.5.12-windows-x64.zip
```

LTS on purpose: the `bpy` API is stable across its lifetime, and Workbench is the
render engine here, so a GPU is optional.

```bash
pip install -r requirements.txt
```

Put your [PiAPI key](https://piapi.ai) in `.env` (`PIAPI_KEY`):

```bash
copy .env.example .env
```

The file is gitignored, so keys stay out of git and out of shell history. Real
environment variables override it, so a one-off `$env:PIAPI_KEY=...` still works
without editing the file.

To use the CometAPI provider instead, set `COMETAPI_KEY` and pass
`--provider comet` — but read the section above first, because it will not
honour your camera.

### Choosing the model

Defaults to **`seedance-2-mini`**, the iteration tier. Three ways to change it,
highest precedence first:

```bash
python -m ai_render generate projects/demo/sequences/seq_010/sh_0020/room.json --model seedance-2
```

```jsonc
"generation": { "model": "seedance-2", ... }   // pins a scene to a tier
```

```bash
# .env — the baseline for everything
AI_RENDER_PIAPI_TASK_TYPE=seedance-2-fast
```

Tiers: `seedance-2-mini` (cheapest) → `seedance-2-fast` → `seedance-2`, plus
`-less-restriction` variants of each. Only `seedance-2` does 1080p; asking for it
on another tier fails before the request goes out, not after you have paid.

The value is not validated against a whitelist — PiAPI adds task types faster
than this repo can track, and rejecting a working one is worse than letting a
typo reach a clear API error.

The same `.env` needs Supabase Storage credentials for the upload hop —
`SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (service_role, it needs storage write),
and `SUPABASE_BUCKET`. Create the bucket first; it can stay **private**, since
access is via signed URLs.

```bash
python tools/check_env.py
```

Reports which credentials are set without ever printing their values.

## Use

```bash
$env:PYTHONPATH="src"; python -m ai_render all projects/demo/sequences/seq_010/sh_0010/cube.json
```

| Command | Does |
| --- | --- |
| `check <scene>` | validate the spec, no rendering, no cost |
| `audit <scene>` | measure the camera move: speed, stalls, clearance to everything |
| `render <scene>` | Blender → a new take with `preview.mp4` |
| `generate <scene>` | blockout → `final.mp4` via the video model |
| `all <scene>` | both |
| `takes <scene>` | list takes and their generations |
| `styleframe <scene>` | restyle a blockout frame into a look reference |
| `compare <scene>` | contact sheet, blockout vs result at matched times |
| `views <scene>` | top/front/side/3-quarter of the scene, camera path drawn |
| `frames <scene>` | individual stills through the shot → `<shot>/frames/` |
| `sheet <scene>` | keep a take with the shot: blockout to `preview/`, stills to `artifacts/` |
| `extract <video>` | pull stills from any clip for comparison |
| `fetch <task-id>` | re-download a finished task without paying again |

### Project, sequence, shot, scene

A scene does not carry its identity; its path does.

```
projects/nyc/
  project.json                  <- fps, resolution, aspect: defaults for everything below
  assets/                       <- work that belongs to no sequence
  sequences/seq_010/
    sequence.json
    sh_0010/
      shot.json                 <- duration, and which scene the shot currently is
      brief.md                  <- the authored intent
      notes.md                  <- what building it taught
      street_a.json             <- a scene: one way of staging the shot
      street_b.json             <- another, in parallel
      preview/                  <- the blockout, one file per version
      frames/                   <- individual stills, the input to a style frame
      artifacts/                <- sheets and views, the working record
```

Each level holds only what differs at that level; a scene inherits the rest.
Resolution order, most specific wins: scene → shot → sequence → project.

Several scenes in one shot are **parallel variants**, never segments: a shot is
one of its scenes, never an assembly of them. Point a command at a shot directory
and it renders the scene `shot.json` selects.

Numbering goes up in tens — `sh_0010`, `sh_0020` — so inserting a shot later is a
naming problem that is already solved rather than a renumbering that invalidates
every path in `out/`.

### The preview, and the record of how it got there

`views` and `sheet` write into the shot, not into `out/`. That is a deliberate
exception to "outputs are derived, so they are disposable": these are not
outputs, they are the record of how a decision was reached — the view that showed
the wall was empty, the sheet that proved the camera held. They are small and
committed. An image that exists only in a chat window is lost to the next
session.

Three directories, because these are three different kinds of thing — one is the
deliverable, one is an input to what comes next, and the rest is evidence:

```
<shot>/preview/    seq_010_sh_0010_street_a_6de41e_preview_v002.mp4
<shot>/frames/     seq_010_sh_0010_street_a_6de41e_still_v001_t000.png
                   seq_010_sh_0010_street_a_6de41e_still_v001_t025.png   ...
<shot>/artifacts/  seq_010_sh_0010_street_a_6de41e_sheet_v004.jpg
                   seq_010_sh_0010_street_a_70bf8c_views_v001.jpg
```

`frames` renders stills straight from the spec at full size — evenly spaced, first
and last always included, so five gives 0, 25, 50, 75 and 100 percent. They are
named by position rather than by index, because the moment is what matters when
one of them is picked to become a style frame, and it stays true if the count
changes. They are not pulled out of the preview: an image model sees whatever it
is handed, and there is no reason to hand it something that has been through a
video codec.

### Reading a file name

`<sequence>_<shot>_<scene>_<id>_<kind>_v###`. The project is left out — these live
inside it already. Everything else is there because it is what goes missing the
moment a file is downloaded, pasted into a message, or sat next to a file from
another shot.

The two middle parts answer different questions, which is why both exist.

**The id** is six hex characters of the spec's content, so everything made from
one state of the scene carries the same one. `6de41e_preview_v002` and
`6de41e_sheet_v004` are the same render seen two ways; `70bf8c_preview_v001` is
from a scene that has since been edited. It is a hash rather than a counter on
purpose: it can be recomputed from the spec by anyone at any time, so "is this
still current?" is a question you can answer from the files themselves instead of
from a ledger that can fall out of step.

**The version** counts its own kind and nothing else, so "the fourth sheet" means
the fourth sheet. It is a high-water mark read off disk, so deleting an old file
never renumbers a newer one — a version in a committed name has to keep meaning
what it meant.

### Output layout

One task, one directory. Nothing is ever overwritten.

```
out/nyc/seq_010/sh_0010/street_a/         <- mirrors the scene's place in the project
  20260824-153012/                        <- a take: one blockout render
    scene.json                            <- the exact spec that produced it
    preview.mp4
    frames/
    20260824-153500_seedance-2-mini_480p/ <- one generation from that take
      run.json                            <- provider, model, params, timings
      final.mp4
      final_frames/
```

Generations nest under the take they came from, because that is the question
you ask later: which blockout is this shot from, and what else did I try against
it? `generate` uses the newest take unless you pass `--take 20260824-153012`.

A failed generation still writes its `run.json`, with the error — it is the
reason the next attempt is different.

### Comparing a result against the blockout

```bash
python -m ai_render generate projects/demo/sequences/seq_010/sh_0020/room.json --resolution 480p --extract
```

`--extract` pulls 8 stills from the result into `final_frames/`, matching the 8
in the take's `frames/`. **Compare identical indices** — `frames/frame_03_.png`
against `final_frames/frame_03_.png`. Comparing different time points reads as
adherence when there is none; that mistake has already been made once here.

Run `check` before `render` and `render` before `generate` — each stage is free
until the last one, so failures should surface as early as possible.

### Measuring a move before rendering it

```bash
python -m ai_render audit projects/nyc/sequences/seq_010/sh_0010/street_a.json
```

```
speed     max 30.2 m/s at t=3.58  (109 km/h), mean 15.0 m/s
stalls    none -- the move never stops and restarts
clearance closest 4 of 104 objects:
            0.95 m  car_03_body          t=1.62
            0.95 m  car_06_body          t=2.88
```

No Blender, no pixels, no cost. It bakes the path from the same interpolation
the render uses — a check that evaluated a different curve would be checking a
different shot — and exits non-zero if the camera ends up inside anything, so it
can gate a render rather than merely inform one.

It exists because of an escape. Retiming a move slides the path against dressing
that did not move with it, and a clearance that held before the change did not
hold after: the camera flew through three parked cars, and eight frames of grey
contact sheet showed nothing, because from inside a car there is nothing to see.
Speed and stalls come along for free once the path is baked — a chain of eased
keyframes stops dead at every one of them, which is obvious in a number and easy
to miss in a video.

```bash
python tests/test_core.py
```

Tests cover spec validation and the baking math; they stub out `bpy`, so they run
without Blender installed.

## Scene spec

```jsonc
{
  "fps": 24,
  "duration": 5.0,              // seconds
  "resolution": [960, 540],     // blockout only; final resolution is in `generation`

  "objects": [
    {
      "name": "hero",
      "type": "cube",           // cube | plane | sphere | cylinder | cone | torus
      "size": 2.0,
      "location": [0, 0, 1.0],  // metres, Z-up
      "rotation": [0, 0, 0],    // degrees, XYZ
      "animation": {
        "rotation": [
          { "t": 0.0, "value": [0, 0, 0], "ease": "ease" },
          { "t": 5.0, "value": [0, 0, 120] }
        ]
      }
    }
  ],

  "camera": {
    "lens": 35.0,               // mm, on a 36mm sensor
    "location": [9, -9, 5],
    "look_at": [0, 0, 1.0],     // aim point, not a rotation — far easier to author
    "animation": { "location": [ ... ], "look_at": [ ... ] }
  },

  "generation": {
    "prompt": "A polished dark-granite monolith rotating in a brutalist hall...",
    "reference_mode": "video",  // video | frames | first
    "duration": 5,              // 4-30
    "resolution": "720p",       // 480p | 720p; 1080p on seedance-2 only
    "aspect_ratio": "16:9",
    "model": "seedance-2-fast",
    "style_references": [       // look references, in tag order: @image1, @image2 ...
      "styleframes/lookref_a.png",
      "styleframes/lookref_b.png"
    ]
  }
}
```

Animatable channels: `location`, `rotation`, `scale`, plus `look_at`, `lens`,
`roll`, `pan` and `tilt` on the camera.

`look_at` aims the camera; the three angles rotate it about its own axes
afterwards, in degrees. `roll` banks it — without that a flight reads as a drone
holding the horizon level. `pan` and `tilt` swing the aim off the target, which
is how a subject gets to sit anywhere but dead centre. All three default to 0,
so a scene that omits them renders exactly as before.

Easing is set per keyframe and governs the segment *starting* at that key:
`ease` (smoothstep, the default), `linear`, `in`, `out`, `smooth`.

`smooth` is the one to reach for on a move that should not stop. The other four
shape one segment in isolation and know nothing about their neighbours — `ease`
in particular has zero velocity at *both* ends, so a run of eased keys arrives
and halts at every one of them, and `linear` turns a corner at each key instead
of curving through it. `smooth` takes its tangent at a key from the keys either
side, so velocity carries through: continuous speed, a curved path, and speed
still steered by how far apart the keys are. With only two keys it is exactly
linear.

**Write the prompt about materials and light, not about layout.** The provider
prepends the reference contract itself. Everything spatial — blocking, framing,
camera path — comes from the blockout; the prompt's job is only to say what the
surfaces are made of and how they are lit.

`style_references` are paths relative to the scene file, and **order is
meaning**: the first becomes `@image1`. When any are present the contract adds
the sentence that decides the shot — *appearance is determined solely by the
images* — and tells the model to take no framing from them. Repeated `--style`
flags override the list for one run without editing the scene, and a
`styleframe.png` sitting in the take is the last resort.

### Why the provider is PiAPI

**`mode: "omni_reference"`.** That single field is the difference between a clip
that follows your camera and a clip that merely looks good. PiAPI exposes
`text_to_video | first_last_frames | omni_reference`, and only the last one
attaches mixed-media references to the generation.

CometAPI's Seedance route has no such switch. It accepts `video_urls`, returns
`200`, produces a polished result — and the result owes nothing to the blockout.
Two live runs confirmed it by frame-for-frame comparison against the same
blockout; the same blockout through PiAPI's `omni_reference` held camera
trajectory, blocking and shot scale exactly.

Things that looked like the cause and were not:

- **The tag syntax.** `@video1`, `[Video 1]` and plain `Video 1` all bind fine
  once the reference is genuinely attached. The tag is positional — it points at
  an entry in `video_urls`, not at a name in the scene spec — so with no
  attachment there is nothing for any spelling of it to point at.
- **Blockout quality.** Worth improving on its own merits (see `demo_room.json`,
  which encloses the space and separates surfaces by value), but it was never
  what stood between us and structure control.

### The reference contract

Two things in `build_reference_prompt` earned their place:

1. **The kept properties are enumerated.** ByteDance's white-model template names
   eight — camera motion, duration, composition, shot scale, spatial
   relationships, object positions, model structure, motion trajectory. "Use it
   for camera and framing" is too vague to bind.
2. **The blockout's own look is excluded explicitly.** Otherwise flat grey reads
   as art direction rather than as scaffolding.

### Style frames

The reference contract tells the model to ignore the blockout's lighting and
colour — which leaves those properties owned by nobody, so the model picks them
itself. A **style still** (`@image1`) takes them back: it owns material,
lighting, colour and mood, while the blockout keeps everything spatial.

The still must agree with the blockout, or the two references pull against each
other. So it is made by **restyling the blockout's own frame**, not by generating
a picture from text:

```bash
python -m ai_render styleframe projects/demo/sequences/seq_010/sh_0020/room.json
```

That sends `frames/frame_01_.png` to GPT Image 2's edit endpoint with an
instruction to change surfaces and light only — same camera, same framing, same
object positions — and writes `<take>/styleframe.png`. `generate` picks it up
automatically from then on; `--style <path>` overrides, and several generations
can share one still rather than paying for it each time.

`--frame N` restyles a different still, `--source <path>` restyles any image.
`--text` switches to pure text-to-image — useful for exploring a look before a
blockout exists, but it invents its own composition, so it should not be fed to
a shot.

Two API details worth knowing: `input_fidelity` must **not** be sent to
`gpt-image-2` (it always runs at high fidelity and rejects the parameter), and
`size` defaults to `auto` here so the edit keeps the frame's proportions.

**A style still is one way to do this, and not the one that has worked best.**
The two runs that fixed the NYC shot used no style still at all: three unrelated
look references, which is what `generation.style_references` is for. A still made
by restyling the blockout is made *before* the dressing is settled, and then
disagrees with it — which is how two cars got dropped. References that carry only
palette and render style have nothing to disagree with.

The command is still worth having when a shot genuinely needs its own frame.
Both routes end up in the same list: `styleframe.png` in the take is simply the
last place `generate` looks.

## Cost

PiAPI bills **input + output** duration, so a 5s blockout under a 5s shot is
charged as 10s. Iterate on `seedance-2-mini` at `480p`, and only move up once the
camera move is right.

Billing is linear in that total, which makes a **trimmed blockout the cheapest
probe there is**: four seconds of a ten-second shot costs 40% of the full run,
and dressing usually fails in the first seconds, where the camera is closest to
things. `ffmpeg -t 4 -c copy` cuts one without re-encoding.

Every stage before `generate` is free, which is why `check`, `render`, `extract`
and `compare` are separate commands — get the blockout right locally, then pay
once. Blender rendering is local and costs nothing.

The render engine is Workbench, not Cycles or EEVEE. That is not a compromise:
the blockout is meant to be flat, untextured grey, because that is what the video
model reads structure from best. A pretty preview would cost time *and* make
results worse — and it means a GPU is optional.
