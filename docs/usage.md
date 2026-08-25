# Running it

*Setup, the commands, and where everything lands. What the project is and why it
exists is in the [README](../README.md); how to write a scene is in
[scene-spec.md](scene-spec.md).*

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

### H3Zero on Modal (experimental)

H3Zero is a self-hosted MiniMax H3 route and accepts the blockout plus look
references directly as multipart uploads. It does not use Supabase. Deploy the
endpoint with Modal proxy authentication, set its URL, and use the local Modal
proxy token for an interactive test:

```ini
AI_RENDER_H3ZERO_URL=https://<workspace>--minimax-h3-web.modal.run
AI_RENDER_H3ZERO_AUTH=modal-proxy
AI_RENDER_H3ZERO_MODAL_KEY=<dedicated proxy token id>
AI_RENDER_H3ZERO_MODAL_SECRET=<dedicated proxy token secret>
```

```powershell
$env:PYTHONPATH="src"
python -m ai_render generate projects/nyc/sequences/seq_010/sh_0010/street_a.json `
  --provider h3zero --extract
```

H3Zero produces `16:9` or `9:16` at `480p` (864 x 480) or `768p` (1344 x 768).
The canvas is not yours to choose — the gateway rejects anything that is not one
of its own native presets for the tier, so the provider resolves it from
`resolution` and `aspect_ratio`. This project's shots are authored at 480p; 768p
is the deployment's recommended tier and costs proportionally more GPU time.

The cheapest smoke-test profile is `turbo_4`; `turbo_8`, `spectrum`, and `base`
are also available. `--model turbo_8` is a temporary override. A repeatable
setting belongs in the scene hierarchy:

```jsonc
"generation": {
  "h3zero": {
    "sampling_profile": "turbo_4",
    "checkpoint": "ref2va",
    "accelerator_lora": "ref2v_turbo_4",   // optional; defaults to the match
    "full_prompt": "Keep <Video 1> ... use <Picture 1> for appearance ..."
  }
}
```

### Model and LoRA, per run

Two independent knobs, both switchable on the command line without touching the
scene:

```bash
python -m ai_render generate <scene> --provider h3zero --checkpoint fl2va --lora ref2v_turbo_4
```

`--checkpoint` picks which model conditions on the references — `ref2va` (the
default, the one MiniMax trained for reference conditioning) or `fl2va` (what
upstream H3Zero uses, and what generation 007 ran on).

`--lora` picks the step-distillation LoRA: `ref2v_turbo_4`, `fl2v_turbo_4`,
`fl2v_turbo_8`, or `none`. Omit it and you get the one distilled from the chosen
checkpoint.

**Any LoRA works with any checkpoint.** A distillation carries deltas for the
weights it came from, so crossing them can cost quality — but that is a thing
worth measuring, so nothing refuses the combination. `check` and `generate` both
print a note when a run is crossed, and the finished job says so in
`result.lora_matches_checkpoint`.

`AI_RENDER_H3ZERO_CHECKPOINT` and `AI_RENDER_H3ZERO_LORA` do the same as the
flags for an unattended run. Precedence for both is flag → environment → scene —
the opposite of `sampling_profile`, deliberately: these exist to be flipped for
one comparison without editing and committing the shot.

### The seed is pinned by default

**H3 runs send `seed: 1001` unless told otherwise.** The deployment's own default
is a fresh `secrets.randbelow(2**63)` per job, which it reports only afterwards —
so before this was pinned, two runs meant to differ in one setting also differed
in noise, and generations 008 and 010 were briefly compared as though they did
not. At four steps with no CFG that is not a small difference.

```bash
python -m ai_render generate <scene> --provider h3zero --seed 42
python -m ai_render generate <scene> --provider h3zero --seed random
```

`--seed random` restores the old behaviour when variety is the point rather than
comparability. `AI_RENDER_H3ZERO_SEED` and a `"seed"` key under
`generation.h3zero` work the same way, with the same flag → environment → scene
precedence.

### What was asked for, and what ran

`run.json` records both. The top-level `checkpoint`, `accelerator_lora` and the
merged `generation` block are the *request*; an `executed` block holds what the
worker says it actually ran — model, seed, LoRA id, steps, sampler, scheduler and
canvas, read off the graph it executed rather than off the request.

The two agree on a fully specified run and diverge wherever the deployment filled
a blank in. Having both on disk is what makes a comparison between two takes
checkable months later, once the jobs themselves have aged out of Modal's
retention.

H3 reference tags are case-sensitive and differ from Seedance: `<Video 1>` and
`<Picture 1>`. The H3 prompt is therefore separate; the provider never rewrites
or reuses a tested top-level `full_prompt`.

**At least one look reference is required.** Without one the only picture of the
scene H3 has is the grey blockout, and it treats grey as art direction. `check`
refuses an H3 scene with no `style_references` and prints the tag each one will
land on; `generate` prints the same mapping again from the service's own echo,
and aborts if the two disagree.

**Results are not deleted after download.** The service offers an acknowledge
call that frees the job, its staged references and the MP4 from the Modal
volume; this provider does not make it. A finished run stays inspectable, and a
download that fails can be recovered with `fetch` instead of paid for twice.
Modal expires them on its own 24-hour schedule.

Create and store a dedicated Modal proxy token without exposing it in shell
history:

```powershell
python tools/configure_h3zero_modal.py `
  --url https://<workspace>--minimax-h3-web.modal.run
```

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

### Where references get published

Seedance takes reference videos by URL only, so the blockout and any look
references have to be reachable from the internet for the length of one job.
`AI_RENDER_UPLOADER` picks how:

| | |
| --- | --- |
| `supabase` (default) | Your own bucket, signed URL, object deleted the moment the job ends. Needs `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (service_role — it needs storage write) and `SUPABASE_BUCKET`. Create the bucket first; it can stay **private**, since access is via signed URLs. |
| `piapi` | The provider's own ephemeral store, `storage.theapi.app` — the host their playground publishes to. Authenticates with `PIAPI_KEY`, needs a Creator plan, 10 MB per file. |

The choice is not cosmetic. PiAPI's Seedance docs say *"Use publicly accessible
URLs (e.g. hosted on a CDN or cloud storage). Signed / expiring URLs may fail"* —
which describes the Supabase route exactly. Against that, `piapi` leaves the file
on someone else's server for 24 hours and offers no delete endpoint, so the
cleanup step genuinely does nothing. Pick per what you are uploading.

Whichever runs, `run.json` records it, because where a reference was published
is a difference a result may later have to be explained by.

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
  assets/                       <- reusable parts: a car, a water tower
  sequences/seq_010/
    sequence.json
    sh_0010/
      shot.json                 <- duration, which scene the shot is, and how it generates
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

Which is why the **`generation` block belongs in `shot.json`**, not in the scene.
The prompt, the model and the look references describe the shot being delivered;
the scenes under it are competing ways to stage that same shot. Put them in one
scene and the variant beside it is generated differently, so the comparison
stops being about the staging. A scene may still override a field when the
variant is specifically a test of that field.

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
      run.json                            <- provider, model, params, timings, task id
      final.mp4
      final_frames/
```

Generations nest under the take they came from, because that is the question
you ask later: which blockout is this shot from, and what else did I try against
it? `generate` uses the newest take unless you pass `--take 20260824-153012`.

A failed generation still writes its `run.json`, with the error — it is the
reason the next attempt is different. The provider's `task_id` lands there the
moment the task exists, before any polling: that is what `fetch` needs to
recover a generation you have already paid for, and what lets a failure be
looked up on the provider a week later. Where a provider returns a category
("your content violated community guidelines") and puts the actual cause in the
task log ("rejected due to copyright restrictions"), both are kept — the
category alone cannot be acted on.

### Comparing a result against the blockout

```bash
python -m ai_render generate projects/demo/sequences/seq_010/sh_0020/room.json --resolution 480p --extract
```

`--extract` pulls 8 stills from the result into `final_frames/`, matching the 8
in the take's `frames/`. **Compare identical indices** — `frames/frame_03_.png`
against `final_frames/frame_03_.png`. Comparing different time points reads as
adherence when there is none; that mistake has already been made once here.

A finished generation is then **copied into the shot's `render/`** under its
conventional name — `<shot>_<scene id>_render_v00N.mp4` — and, when `--extract`
built one, the comparison sheet lands in `artifacts/` as
`..._sheet_v0NN_vs_render_v00N.jpg`. The sheet cannot be named before the render
has a number, which is why both happen at the same moment.

`out/` is scratch keyed by timestamp: `20260826-012944_base_768p` records when a
file was made and nothing about which shot or which spec produced it. `render/`
is the committed record. Doing that copy by hand is how two paid runs ended up
sitting in `render/` under raw task ids. Pass `--no-publish` to skip it for a
throwaway probe.

Run `check` before `render` and `render` before `generate` — each stage is free
until the last one, so failures should surface as early as possible.

### Watching several takes together

The contact sheet answers *is the camera where the blockout puts it at 43%* and
answers it well. It cannot answer *which of these is cleaner*: texture,
stylisation and temporal noise do not survive being sampled eight times, and
once several runs all hold the blockout those are the only things left to judge.
Playing them one after another does not work either — the gap between two
playbacks is long enough to forget the first.

```bash
python -m ai_render mosaic out/fourup.mp4 \
  "out/.../preview.mp4=blockout" \
  "projects/.../render/..._render_v007.mp4=base · 30 steps" \
  "projects/.../render/..._render_v011.mp4=spectrum"
```

Clips tile in reading order, two per row by default (`--columns`, `--width`).
`=LABEL` captions a cell; without one the filename stem is used.

Two things are normalised, for the same reason the sheet samples by position
rather than frame number. **Time** is scaled so t = 50% is the same instant in
every cell — a blockout and a generation need not agree on length, and H3
aligns output to its own frame grid, coming back 3 frames longer than the
10-second blockout it was given. **Aspect** is preserved and padded rather than
stretched, because Blender's 16:9 and H3's 7:4 canvas genuinely differ.

Audio is dropped: three generations playing their invented city ambience at once
is noise, not evidence.

This needs **ffmpeg**, which the rest of the pipeline does without — stills come
out of Blender precisely so there is no such dependency. If it is not on PATH,
point `AI_RENDER_FFMPEG` at its directory or at the binary.

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
## Why the provider is PiAPI

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

## The reference contract

Two things in `build_reference_prompt` earned their place:

1. **The kept properties are enumerated.** ByteDance's white-model template names
   eight — camera motion, duration, composition, shot scale, spatial
   relationships, object positions, model structure, motion trajectory. "Use it
   for camera and framing" is too vague to bind.
2. **The blockout's own look is excluded explicitly.** Otherwise flat grey reads
   as art direction rather than as scaffolding.

## Style frames

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
