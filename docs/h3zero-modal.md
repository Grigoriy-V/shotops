# H3Zero on Modal

This is the reproducible source and deployment note for the experimental
`--provider h3zero` route. The provider integration itself is documented in
[usage.md](usage.md).

## Pinned source

- Upstream: `https://github.com/hui-tony-zk/h3zero`
- Tested commit: `8655e33d2b5a6f670458aa783a6d44b1c659d7e8`
- Local checkout: `.tools/h3zero/` (gitignored)
- Local Python: 3.11 virtual environment at `.tools/h3zero/.venv/`

The upstream no-GPU suite passed at that commit: 57 Python tests, 35 frontend
tests, and 4 Node/orchestration tests. The production npm dependency graph had
no reported vulnerabilities; the full development graph reported one high
severity advisory.

Clone and verify the exact revision before doing anything that can allocate
cloud resources:

```powershell
git clone https://github.com/hui-tony-zk/h3zero .tools/h3zero
git -C .tools/h3zero checkout --detach 8655e33d2b5a6f670458aa783a6d44b1c659d7e8
git -C .tools/h3zero apply ..\..\tools\h3zero-proxy-auth.patch
git -C .tools/h3zero apply ..\..\tools\h3zero-checkpoint-vram.patch
```

`h3zero-proxy-auth.patch` changes only the ASGI decorator and requires Modal
proxy authentication. Do not deploy the upstream public default: its job
endpoint can allocate an RTX PRO 6000 for anyone who discovers the URL. The
`.modal.run` endpoint then uses a dedicated workspace proxy token; create and
store it in the gitignored `.env` without exposing it in shell history:

```powershell
python tools/configure_h3zero_modal.py `
  --url https://<workspace>--minimax-h3-web.modal.run
```

`h3zero-checkpoint-vram.patch` does two things, described below: it makes the
reference checkpoint a request parameter defaulting to Ref2VA, and it measures
VRAM.

Both patches are held here rather than in a fork because the checkout is
disposable and the pinned upstream commit is the thing worth trusting. After
applying them, `npm test` in the checkout should report **70** no-GPU Python
tests against the pinned baseline of 57, and the 35 frontend tests still pass.

## The reference checkpoint is a request parameter

MiniMax ships two H3 checkpoints. `fl2va` is conditioned on first and last
frames; `ref2va` is the one trained for reference conditioning. Upstream H3Zero
downloads both but hard-codes its reference graph to FL2VA — a deliberate
upstream choice, made for general prompt quality, and one that could only be
revisited by redeploying.

That is the wrong shape for the decision. Both files are already on the volume,
each 31.7 GiB, and neither is more expensive to load than the other. Which one
runs is a property of a *job*, not of a deployment — so the patch makes it a
config field and an A/B becomes two runs instead of two deploys:

```jsonc
{ "mode": "references", "reference_checkpoint": "ref2va" }   // or "fl2va"
```

The field is validated against a fixed map of ids and never carries a filename,
because the resolved value reaches ComfyUI's `UNETLoader`, which reads a file
off the model volume by name. It is rejected outright in `frames` mode.

**Ref2VA is the default**, because it is the checkpoint MiniMax trained for
reference conditioning.

Expect less from that than the name suggests. Generation 007 ran on FL2VA and
reproduced the blockout's *semantic* trajectory — street, climb, bay — while
losing its composition, shot scale and object positions. 008 changed only the
checkpoint and the matching distillation, and came back **substantially the
same**. The reason is in the next section but one: both checkpoints reach the
references through the same conditioning node, and that node has no mechanism
for holding structure. Changing whose weights read the context cannot supply a
binding that does not exist.

What did move the result was [009](../projects/nyc/sequences/seq_010/sh_0010/generations.md)
— 30 steps, 768p, and a prompt in MiniMax's own reference format.

Which one actually ran is read back out of the executed graph, not echoed from
the request, and lands in `result.model`, `result.checkpoint` and
`result.reference_checkpoint`. With the checkpoint selectable, "which model made
this" stops being something a caller may assume.

Sampling profile and LoRA strengths were already request parameters; this closes
the last one that was not. Registering a *new* style LoRA still needs an edit to
the checkout's `local_loras.py` and `npm run models` to fetch the weight — a new
file has to reach the volume somehow — but choosing among configured ones and
setting their strengths is `config.loras`.

## The accelerator LoRA is a second, independent parameter

A turbo profile is a **step distillation**, and a distillation carries deltas
for the weights it was distilled from. Upstream H3Zero could ignore that,
because it ran every graph on FL2VA and only ever downloaded the `fl2v` line.

Which distillation to load is therefore its own request field, `accelerator_lora`,
resolved separately from the checkpoint:

| id | file | distilled from |
| --- | --- | --- |
| `ref2v_turbo_4` | `minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16` | `ref2va` |
| `fl2v_turbo_4` | `minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16` | `fl2va` |
| `fl2v_turbo_8` | `minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16` | `fl2va` |
| `none` | — | loads no accelerator at all |

**Any accelerator pairs with any checkpoint.** Crossing one onto weights it was
not distilled from is a genuine risk to output quality — but it is a *question*,
not a mistake, and answering it requires the combination to be reachable.
Nothing refuses a crossed pairing; the run reports it instead, through
`result.lora_id` and `result.lora_matches_checkpoint`, and `check` and
`generate` both say so on the console.

Omit the field and it defaults to the distillation matching the checkpoint:

| Checkpoint | Profile | Default accelerator |
| --- | --- | --- |
| `ref2va` | `turbo_4` | `ref2v_turbo_4` |
| `ref2va` | `turbo_8` | `fl2v_turbo_8` — no 8-step ref2v exists, so this default is itself a crossing |
| `fl2va` | `turbo_4` | `fl2v_turbo_4` |
| `fl2va` | `turbo_8` | `fl2v_turbo_8` |
| either | `base`, `spectrum` | none — samples the checkpoint directly at 30 steps |

That last row is the whole story for `base` and `spectrum` in normal use: their
`lora` is `None`, `resolve_accelerator_lora` returns early, and no
`LoraLoaderModelOnly` node is built at all. Their `lora_strength: None` in
`SAMPLING_PROFILES` is the matching record of "there is no LoRA here", and it is
never read.

**The one hole is the explicit path.** Naming an accelerator by hand — `--lora`,
`AI_RENDER_H3ZERO_LORA`, or `generation.h3zero.accelerator_lora` — skips that
early return, because the check is on whether the *caller* left the field blank,
not on whether the profile has a LoRA at all. The node is then built with
`strength_model: None`. The combination it comes from is not a question worth
answering the way a crossed checkpoint is: a step distillation and a 30-step
profile contradict each other outright, so the fix is to refuse the pairing at
resolve time, not to invent a strength for it. Unfixed, and reachable only by
asking for it.

Two asymmetries worth knowing when reading results: the Ref2V distillation is
**v0.1** against the fl2v line's v1.0/v1.1, and the fl2v 4-step file is labelled
`768p` while this project renders at 480p. Neither is a defect, but neither is a
like-for-like comparison either.

LightX2V published the Ref2V counterpart on 2026-08-13, *after* the pinned
`TURBO_REVISION`, so the patch moves the pin to
`ec01fa4c86263832faa0bd1d6d8f36a281eaabb2` and adds the file to
`MODEL_DOWNLOADS`. It is **already on the volume** — 1.82 GiB, fetched by
`npm run models`, which reported the other seven files as `Already present` and
downloaded only this one.

## What is missing from the open weights

MiniMax's product is two stages. **H3-Context-IR** takes free-form multimodal
input — text, images, video, audio — parses the instructions, associates the
modalities, works out the temporal structure, and emits a structured *Context
Intermediate Representation*. **H3-Base** then generates 768p video and audio
from that IR. Its generative core, `H3-Omni-Transformer`, is a 33B dense
single-stream transformer with 3-D MM-RoPE over `(t, h, w)`.

Only H3-Base is released. In MiniMax's words, Context-IR "relies on a
multi-stage workflow and multiple hosted models and services", so it is not in
the open-weight release and exists only as a hosted API.

**This means a free-form prompt sent to H3-Base is being fed to the wrong
stage.** Generations 007 and 008 did exactly that. The six-section format —
`subject_definitions`, `summary`, `retention_analysis`, `detailed_description`,
`overall_soundscape`, `non_diegetic_music` — is the shape of Context-IR's
output, and hand-writing it is the substitute MiniMax point developers at:
"developers can follow the Prompting Guidance to build their own preprocessing
systems."

Which makes a preprocessor a real component of this project rather than a
prompt-tweaking habit — and one where a blockout pipeline has an advantage over
the hosted service. Context-IR exists to *infer* subjects, roles and timing from
free text. Here they are already explicit: `objects` and `instances` name the
subjects, and the camera track's keyframes are the timecodes. The IR can be
derived from the scene, not guessed from prose.

Two more places where this deployment sits below the reference implementation,
neither cheaply fixed:

- **The weights are int8, not bf16.** They come from `Comfy-Org/MiniMax-H3`, a
  repack, not from `MiniMaxAI/MiniMax-H3`. At bf16 the transformer and the
  Qwen3-VL text encoder would need roughly 66 and 52 GB, which does not fit the
  97 GB card together.
- **Everything runs through third-party interpretations of the architecture:**
  Comfy-Org's quantisation, ComfyUI's H3 nodes, H3Zero's wrapper, and LightX2V's
  distillations. Four parties, none of them MiniMax.

## The reference video is context, not control

Worth knowing before designing a shot around it, because it caps what any amount
of prompting can buy.

`MiniMaxH3OrderedReferenceToVideo` starts the output from `_empty_av_latent` —
an empty latent. The reference video is VAE-encoded into a separate
`minimax_refs` block hung off the conditioning, which the DiT re-injects every
step and never denoises. It is context sitting *beside* the timeline, with its
own `latent_t/h/w`. **Nothing binds reference frame `t` to output frame `t`**,
and H3 has no depth, pose or ControlNet path at all.

The language half sees even less: the encoder is handed frames at 2 fps
(`range(0, frames, FPS // 2)`), so a ten-second blockout reaches Qwen3-VL as
about nineteen stills.

The vendor says the same in plainer words — a reference video is guidance, not
guaranteed reproduction. Structure adherence is therefore something to be
*coaxed*, through step count, native resolution and an IR-shaped prompt, and 009
shows that coaxing works. It is not something to be *enforced*.

One avoidable mismatch sits on top of that. A 10 s output is 243 frames (the
`17k+5` grid), while the reference is truncated by the same rule to 226 frames —
9.42 s. The model gets 93% of the move and has to fill 10.125 s with it, and the
final settle is cut off. Rendering blockouts to 243 frames would remove it.

## VRAM

The GPU worker now samples ComfyUI's own `/system_stats` on a thread for the
duration of a workflow and keeps the high-water mark. It has to be sampled
during the run: the memory is released before the workflow returns, so a reading
taken afterwards finds almost nothing. The peak lands in the job's
`result.vram`, in the GPU logs, and on the console during `generate`.

**Measured, generation 008:** peak **64.89 GiB of 94.97 GiB — 68% of the card**,
on a 10-second 480p `turbo_4` reference generation with one video and three
image references.

That number corrects an assumption made before it existed. The staged model
sizes below sum to 62.4 GiB, and this note previously called that an *upper
bound* on the working set, reasoning that DynamicVRAM streams weights rather
than holding all four resident. The measured peak is **higher** than the staged
sum, not lower: streaming does reduce resident weights, but activations,
latents and the attention working set are added on top of whatever is resident,
and together they more than close the gap. Staged weights are a floor to reason
from, not a ceiling.

The device is an RTX PRO 6000 Blackwell Server Edition with **97,250 MB** of
VRAM, in `NORMAL_VRAM` state with DynamicVRAM streaming and async weight
offloading over two streams. The models staged for a reference run are:

| Model | Staged |
| --- | ---: |
| `MiniMaxH3` (diffusion, int8) | 32,427 MB |
| `MiniMaxH3TEModel_` (Qwen3-VL-32B text encoder, int8) | 25,882 MB |
| `MiniMaxH3VideoVAE` | 4,965 MB |
| `MiniMaxH3AudioVAE` | 576 MB |
| **Total staged** | **63,850 MB** |

Ref2VA does not change the picture: the two checkpoints are the same size.

At 68% on a 10-second 480p clip there is real headroom, but not a lot of it —
768p is roughly 2.7x the pixels per frame, and that scales the activation half
of the number rather than the weights. Worth measuring before assuming the tier
fits, which is now a thing the sampler makes cheap to do.

Timing from 007, for scale: four `turbo_4` steps in 66.5 s, of which 21.4 s was
the first step including model initialization and the rest ran at 16.6 s/step.
The whole ComfyUI prompt took 126.5 s.

## Checking a payload without allocating anything

The checkout is also a test fixture. `tools/check_h3zero_contract.py` imports
the gateway's own validators out of it and runs a scene's real payload through
them — no network, no GPU:

```powershell
.tools\h3zero\.venv\Scripts\python.exe tools\check_h3zero_contract.py `
  projects\nyc\sequences\seq_010\sh_0010\street_a.json
```

It confirms the canvas is a native preset for the tier, that the reference
declarations validate, and — the part worth having — that the tags the gateway
would assign are the tags the prompt names. Run it before any paid generation.

## Where this goes next

Not scheduled, and recorded here so the decision does not have to be rediscovered.

H3Zero was taken as a fast way to reach H3 at all, and it did that. What it
costs is a product's worth of assumptions this project does not share: two
resolution tiers with 480p as the default when the model is native at 768p, a
whitelist of two aspect ratios when MiniMax supports at least six, step counts
pinned per profile, canvas presets, a web frontend and a spec version to keep in
step with it. Every one of those got in the way this session.

ComfyUI itself is not the problem and is worth keeping — the graph submitted to
`/prompt` **is already ComfyUI API JSON**. H3Zero builds it in Python; a workflow
exported from the ComfyUI editor is the same document. So the shape to move to
is: build the graph in the ComfyUI UI, export API JSON, treat it as a template
with holes for prompt, canvas, seed, checkpoint and reference filenames, and
keep Modal as a thin worker that stages files, posts the graph and returns the
MP4.

Worth keeping from the checkout: the Modal image definition, the model volume
and `download_models`, the VRAM sampler, and **`ordered_refs_node.py`** — it
solves a real problem the stock nodes do not, namely a cross-media reference
order, so that `<Picture 2>` means the picture the prompt thinks it means.

Worth dropping: `parse_config` and the gateway, the frontend and `SPEC_VERSION`,
the resolution tiers and canvas whitelist in `specs.py`, the sampling-profile
catalogue, and `build_frames_workflow` / `build_reference_workflow`.

One thing this buys beyond tidiness: with the checkpoint filename no longer
hard-coded, MiniMax's own bf16 weights become reachable, and the cost of the
int8 repack becomes measurable instead of assumed.

### Aim it at custom workflows and LoRAs

The user's steer, and it follows from the sampling runs 010 through 012 rather
than from taste. Since the heavy path is already being paid for — a full
ComfyUI, its node ecosystem, a 98 GiB model volume — **the replacement should be
built to exploit that, not merely to tolerate it.** Two capabilities are the
point of the rebuild:

**Arbitrary graphs, authored in the ComfyUI editor.** Not a fixed reference
pipeline with holes in it, but whatever graph the shot needs, exported as API
JSON and templated. That is the difference between a product with a config file
and a tool that can answer a question nobody anticipated.

**LoRAs as first-class inputs.** The four LoRA runs settled that the pairing
matters more than the vendor's default suggests: the distillation MiniMax pairs
with its own reference checkpoint came last, and one distilled from the *other*
checkpoint came second overall. `CONFIGURED_LORAS` in the checkout is a
local-only style-LoRA mechanism that this project has never used and that reads
files from a module the repo does not ship. Loading a LoRA — style or
step-distillation, from the volume or from a URL — should be an ordinary
request parameter with a strength, not a deployment-time list.

Both of these are things `parse_config` and the profile catalogue currently
prevent rather than provide.

## Cost and licence gates

Do not run H3Zero's `setup`, model download, GPU deploy, smoke test, or an API
job without an explicit approval for that run. The initial model volume is
about 98 GiB. A first `turbo_4` job is 480p; cold start and model loading can
cost more than the generation itself.

**The checkpoint parameter, the accelerator parameter and the VRAM sampler are
all in the checkout and none is live.** The gateway change needs `npm run
deploy`, the worker change needs `npm run deploy:gpu`.

Neither rebuilds the image and neither re-downloads weights. Every file they
touch arrives through `add_local_python_source`, whose own docstring says the
files "are added to containers on startup and are not built into the actual
Image" — so the cached CUDA, ComfyUI and torch layers are untouched. Weights are
the separate `download_models` function, which only `npm run models` calls, and
which skips anything already on the volume. Deploy starts no GPU either.

The one real cost is that a redeploy invalidates the CPU memory snapshot, so the
first job afterwards pays a cold start again — 174 s end to end in 007, of which
66 s was sampling.

**`npm run deploy` exits non-zero even when it succeeds.** Its last step,
`verifyFrontendBundle`, fetches the deployed URL anonymously to confirm the
expected bundle is being served — and the proxy-auth patch makes that a 401 by
design. The deployment itself is already complete when this fires; the line to
look for is `App deployed in …! 🎉` above the traceback. Verify with an
authenticated request instead:

```powershell
$env:PYTHONPATH="src"
.tools\h3zero\.venv\Scripts\python.exe tools\check_h3zero_contract.py `
  projects\nyc\sequences\seq_010\sh_0010\street_a.json
```

That checks the payload offline. For the live endpoint, `GET /api/specs` with
the `Modal-Key` / `Modal-Secret` headers from `.env` returns the deployed
contract, and its `version` should read `1.8`.

The spec version moves 1.7 → 1.8 because the references mode now advertises a
choice of checkpoint. The frontend pins that version, so gateway and frontend
have to deploy together — which `npm run deploy` does anyway.

MiniMax H3's licence defines an Applicable Territory that excludes the United
States, European Union, United Kingdom, and Republic of Korea. Modal normally
uses US infrastructure for some storage traffic even when compute is routed to
another region. Region selection alone therefore does not establish licence
compliance. Resolve that deployment question before weights are downloaded to
Modal.

## First evidence

The first paid result is not acceptance evidence by itself. Run generation with
`--extract`, then compare it against the same take at matched normalised times:

```powershell
$env:PYTHONPATH="src"
python -m ai_render generate projects/nyc/sequences/seq_010/sh_0010/street_a.json `
  --provider h3zero --extract
```

Record whether H3 holds camera motion, framing, object positions, and duration.
Reference ingestion proves only that the API accepted the files; it does not
prove structural adherence.

The first run after the redeploy has a better question available to it than
"is this good", because 007 exists: **same shot, same references, same prompt,
same profile, one checkpoint changed.** Compare against 007 at matched times and
the answer is about Ref2VA rather than about H3. Confirm from `result.model`
that Ref2VA is what actually ran before reading anything into the frames.
