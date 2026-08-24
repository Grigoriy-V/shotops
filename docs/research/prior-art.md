# Prior art

*Surveyed 2026-08-24.*

## The closest thing, and it got there first

**[`wassermanproductions/blockout`](https://github.com/wassermanproductions/blockout)**
— Apache-2.0, 112 stars, 18 forks, 58 commits at time of writing.

An Electron desktop app for staging grey-box previs: mark-based blocking for cast
and camera, then export a motion-reference package for a video generator. Its
engine is pure TypeScript with no DOM, unit-tested, with scene state as a pure
function shared by playback, video export, stills and glTF baking.

It targets Seedance 2.0, Veo 3.1, Kling, LTX 2.3 and Wan 2.2, and exports a
bundle rather than calling an API: reference video, depth pass, optional normal
pass, stills, a prompt tailored per generator, a pre-wired ComfyUI workflow,
machine-readable metadata, and a `.glb` Blender handoff with animated camera.

**The uncomfortable part.** Its projects are, in its own words, a folder of
pretty-printed, stable-key-order JSON — diff it, branch it, review it. That is
the shotops thesis, already implemented, by someone who thought of it
independently. Worth stating plainly rather than discovering later.

**Where the two actually differ**, and it is not a small gap:

| | blockout | shotops |
| --- | --- | --- |
| Who authors the scene | a human, in a GUI | an agent, writing JSON |
| 3D engine | its own TS engine | Blender headless |
| Generator | you export, then feed it yourself | called from the pipeline |
| Result | a bundle handed off | a take, with provenance, comparable |

Stable-key JSON makes a project *diffable*. It does not make it *agent-authored*
or *auditable end to end*. The distinct claim here is not the file format — it is
that the spec is written by a model, validated before anything renders, and every
output traces back to the exact spec that produced it.

Two adjacent tools by the same author:
[`motion-previs-studio`](https://github.com/wassermanproductions/motion-previs-studio)
(camera path, depth, edges, masks, OpenPose diagnostics from reference footage)
and [`motion-previs-mcp`](https://github.com/wassermanproductions/motion-previs-mcp),
which exposes that extraction to any MCP agent. The direction of travel there is
the opposite of ours: real footage → control pack, rather than authored spec →
blockout.

## Curated workflow collections

**[`Evolink-AI/Awesome-Blender-Seedance-Workflow-Usecases`](https://github.com/Evolink-AI/Awesome-Blender-Seedance-Workflow-Usecases)**
— 39 collected Blender + Seedance cases: camera control, previs, multi-character
blocking, action choreography, Blender MCP, Codex/Claude-assisted blockouts,
FBX/Mixamo, ComfyUI style transfer, and a section on known limitations.

Caveat: the repo appears in search results but returned 404 from the GitHub API
on 2026-08-24 — possibly renamed, moved or made private. The related
[`EvoLinkAI/awesome-seedance-2-guide`](https://github.com/EvoLinkAI/awesome-seedance-2-guide)
resolves. Treat the case count as reported, not verified.

## Traditional pipeline versioning

The problem shotops points at is well known, and the industry's answer has been
**OpenUSD layering** rather than diffing: separate layout, lighting and FX layers
composed non-destructively, so several artists work in parallel without one
blocking another. That solves *concurrency*. It does not give you a readable diff,
blame, or bisect — the composition is still binary-ish and tool-mediated.

Existing open pipeline tools ([`pipeVFX`](https://github.com/hradec/pipeVFX),
[`PIPEDREAMS`](https://github.com/LouisRossouw/PIPEDREAMS)) manage jobs, shots and
software assignment. They orchestrate around the scene file; they do not make it
readable.

Nobody found in this survey is making shot *decisions* — camera, layout, timing —
the versioned source of truth. That gap is where this project sits.

## What this changes for shotops

**Do not claim novelty for diffable JSON scenes.** Claim the agent-authored,
validated, end-to-end-traceable part, and name blockout as prior art in the
README when the project is described to anyone outside this repo.

**Their export bundle is a better idea than our single mp4.** Depth and normal
passes are cheap in Workbench and are exactly the conditioning signals ComfyUI
and open models want. Worth stealing.

**Their `.glb` handoff suggests an escape hatch we lack:** a way out of the spec
into a real DCC when a shot outgrows primitives.
