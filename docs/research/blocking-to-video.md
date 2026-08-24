# Blocking → video

*Surveyed 2026-08-24.*

## The method has a settled shape

Across collected workflows the recipe is consistent enough to call standard:

1. Build the scene from primitives in Blender. No modelling, no textures.
2. Animate the camera with rough timing — the move matters, the polish does not.
3. Export the blockout clip.
4. Feed it to the generator **as a motion reference**, usually together with a
   start frame that carries the look.

The start frame is where the workflows differ. Common variants: generate it in
Midjourney and match the Blender poses to it; restyle a blockout frame (what
shotops does); or drive the camera from an iPhone pass timed to dialogue. The
multi-character cases are the ones that most need the 3D stage — matching two
performers' blocking by prompt alone does not converge.

This is the same conclusion the pipeline here arrived at independently, and it is
worth noting *why* it keeps being rediscovered: the grey box is not a cheap
substitute for a real render, it is a **cleaner signal**. Texture and lighting in
a reference compete with the prompt for control of the output.

## What "reference" means per model

The single most important distinction, and the one that cost this project the
most: **accepting a reference and honouring it are different things.** A gateway
can take `video_urls`, return `200`, and produce a polished clip that owes
nothing to your camera. See [the PiAPI section of the
README](../../README.md#why-the-provider-is-piapi) — the deciding field was
`mode: "omni_reference"`, not prompt wording or blockout quality.

| Model | Structural reference | Notes |
| --- | --- | --- |
| Seedance 2.x | video reference (white-model control) | what shotops uses; reference video is URL-only, and billing counts input + output duration |
| Wan 2.2–2.7 | reference-to-video; reportedly a "blocking scaffold" input for 3D blockout mesh or camera reference, plus motion-style and colour-palette references *(low confidence — vendor-adjacent blogs only)* | open weights, so the only family where you can run this locally and inspect it |
| Kling 3.0 | reference inputs | characterised as optimised for first-pass quality over iterative control *(low confidence)* |
| Veo 3.1, Runway, LTX 2.3 | targeted by blockout's exporter | not tested here |

The frequently repeated framing that Kling optimises for first-pass quality while
Wan optimises for iterative control is plausible and matches how the tools are
used, but it comes from comparison blogs with an obvious incentive. Treat as a
hypothesis to test, not a finding.

## The other conditioning route: passes, not clips

The ComfyUI-shaped workflows do not send a beauty clip at all. They send
**depth**, **edges/normals**, **masks** and **OpenPose skeletons** — extracted
from footage, or rendered directly from the blockout. `blockout` exports depth
and optional normal passes alongside its reference video for exactly this.

This matters for shotops because those passes are nearly free in Workbench and we
render none of them. A depth pass costs one extra render pass and opens the whole
open-model/ComfyUI branch, where control is explicit rather than negotiated with
a closed gateway.

## Known limits, reported and observed

- **Duration.** These are 5–15s shots. Nothing in this family holds a
  minute-long continuous move.
- **Billing is not per output second.** PiAPI bills input + output, so a 5s
  reference under a 5s shot is charged as 10s. Cheap blockouts are not free
  blockouts.
- **The reference constrains, it does not command.** Structure adherence is
  strong on camera, blocking and shot scale, and much weaker on exact object
  counts and fine geometry — visible in this repo's own comparison sheet, where
  columns track but their number is not guaranteed.
- **Style and structure fight** unless separated deliberately. The two-reference
  split — blockout owns spatial, still owns look — is the mitigation, and it only
  works when the still is derived from the blockout's own frame.

## What this changes for shotops

**Render a depth pass.** Cheapest available upgrade, opens the open-model branch,
costs one flag in `configure_render`.

**Test Wan.** It is the only open-weights family where the blocking-scaffold claim
can be verified rather than believed, and it removes the gateway from the
structure-control question entirely.

**Keep the two-reference split.** It is not a workaround; the collected workflows
converge on the same separation from the other direction.
