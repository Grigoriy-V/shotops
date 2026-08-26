# Ideas, not started

*Recorded 2026-08-24; idea 4 added 2026-08-26.* Directions worth trying, with
what each one would actually test. None of these is scheduled; this file exists
so the reasoning is not re-derived later.

## 1 — Self-hosted generation on Modal, compared against Seedance

Deploy open video models serverlessly on [Modal](https://modal.com) — LTX-2.5 and
H3 — run generation there against the same blockouts, and compare with the
Seedance results we already have.

*(Pin down what "H3" means before starting: HunyuanVideo and Hunyuan3D are
different projects, and idea 3 below wants the 3D one.)*

**What it tests.** Whether structure control survives outside a closed gateway.
Right now the decisive knob is a vendor's `mode: "omni_reference"` flag — a field
in someone else's API that could change without notice. With open weights the
conditioning is ours: we choose what the model is conditioned on, at what
strength, with what seed.

**Why it might be better than a gateway, beyond independence.** PiAPI bills
input + output duration, so every iteration pays for the blockout twice over.
Self-hosted, the reference is free and only GPU seconds cost. Iteration economics
change enough to change how the tool is used.

**What makes it a fair comparison, not a vibe.** The same take, the same
blockout, the same style still, frames sampled at identical normalised times —
the `compare` machinery already exists and exists precisely so this kind of claim
can be checked. Anything less repeats [the frame-matching mistake made
here once](../../README.md#comparing-a-result-against-the-blockout).

**Known unknowns.** Cold-start time on serverless GPU for a model of this size;
whether these models take a *video* structural reference at all or only stills
and passes; VRAM tier and therefore cost per run.

## 2 — Scenes built from ready-made assets

*Partly overtaken, 2026-08-25.* The spec now has `assets` and `instances`, but
they are the **recipe** half: a part list in the unit space of a bounding box,
written by hand, expanded at load. That answers "geometry should be reusable and
diffable". It does not touch what this idea is actually about — pulling in
geometry that somebody else made, from a library or a `.blend` or a download,
and pinning it reproducibly. See [scene-spec.md](../scene-spec.md) for what
exists.

Let the spec reference real assets — a library object, a `.blend` link, a
downloaded model — instead of only primitives.

**What it tests.** Whether silhouette fidelity improves structure adherence. The
blockout is deliberately untextured, but shape is not appearance: a chair-shaped
grey mass tells the model far more than a grey box does, at no cost to the
"flat grey reads as scaffolding, not art direction" principle.

**What it changes in the spec.** A new object kind alongside `cube`/`sphere` —
something like `{"type": "asset", "source": "...", "transform": ...}` — plus a
resolution rule for where assets live and how they are pinned. That last part is
the interesting one: **an asset reference must be as reproducible as a
primitive**, or the spec stops being a complete description of the shot. A hash
or a version-pinned id, not a local path.

**Risks.** Scene weight (the 7.3 s loop is a load-bearing number — see
[feedback-loop.md](feedback-loop.md)); licensing, if anything is ever published;
and the possibility that it simply does not help, which is worth knowing.

## 3 — Scenes with generated 3D models

Have the agent generate the geometry too: text-to-3D for hero props, dropped
into the same spec.

**What it tests.** Whether the pipeline can be closed end to end with no human
asset work at all — the fullest version of "the agent authors the scene".

**Where it plausibly wins.** Blockouts do not need clean topology, UVs, or
watertight meshes. They need correct silhouette and scale. That is the easiest
thing for current text-to-3D to deliver and the hardest thing to fake with
primitives. This is a case where the low quality bar is a genuine advantage
rather than a compromise.

**Where it plausibly fails.** Generated meshes arrive at arbitrary scale and
orientation, and a shot cares about both; automatic normalisation into the
scene's metric, Z-up world is likely the real work here, not the generation.

**Same reproducibility question as idea 2**, sharper: a generated mesh must be
cached and content-addressed, or the spec no longer reproduces the shot. Generate
once, store by hash, reference by hash.

## 4 — Feeding the previous shot back as a second reference video

*Recorded 2026-08-26.* For a sequence, attach the **previous shot's generated
output** as a second video reference alongside the blockout and the character
pictures, so the next shot inherits grade, grain and identity from what actually
came out rather than only from what was asked for.

**Provenance, because it matters here.** This is not official guidance. MiniMax's
platform docs do not address chaining generations at all; their advice for
consistency is a repeated character block and the same reference image every
time. The chaining idea comes from [one vendor
blog](https://www.atlascloud.ai/blog/tips/minimax-h3-reference-to-video)
*(low confidence)*. See [h3-prompting.md](../research/h3-prompting.md).

**What it tests.** Whether appearance continuity across a cut is better served by
conditioning on a real previous frame sequence than by re-deriving the look from
stills each time. H3 accepts up to 3 reference videos, so the capacity is there.

**What it changes.** A provider change: we attach exactly one video, the
blockout, and `validate_h3_prompt` raises on any `<Video 2>`. That constraint was
deliberate and would need widening rather than removing — the blockout must stay
`<Video 1>`, and a second video needs its own role stated in the prompt or it
will compete with the blockout for structural authority.

**Where it plausibly fails.** Conditioning each shot on the last one's *output*
is the classic way drift compounds along a sequence: shot 4 inherits shot 3's
mistakes as ground truth. It may also fight the blockout, since a previous shot
is a video reference with its own camera move.

**Run it as its own test, not inside a spot.** The
[rooftop spot](../../projects/spot/script.md) deliberately does the cheap thing
first — same character pictures everywhere, no chaining — so that if identity
holds, this idea is unnecessary, and if it does not, there is a specific failure
for chaining to be measured against.

## What ties them together

Ideas 2 and 3 both push on the same seam: **the spec currently describes
everything about a shot, and both would let something in from outside it.** That
is fine — but only if whatever comes in is pinned as precisely as the numbers
already are. The moment a shot depends on a file that might change, the version
control claim this whole project rests on quietly stops being true.
