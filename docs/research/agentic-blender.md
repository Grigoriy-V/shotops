# Agentic Blender: spec, MCP, or raw `bpy`

*Surveyed 2026-08-24.*

The question this file answers: **when is a spec enough, when do you need MCP,
and why.**

## Three ways to put a model in Blender

**1 — Raw `bpy` script generation.** The model writes Python, you run it. The
standard criticism is fair: the API drifts across versions, context-sensitive
operators fail when the active object, mode or selection is wrong, and a failed
script gives weak feedback. It is genuinely brittle *when the model improvises
scene edits* against an unknown scene state.

**2 — MCP tools.** A server exposes validated operations. The model calls
`create_object`, `assign_material`, `render`, gets structured errors back, and
keeps context across steps. This is the dominant approach in 2026 and the
community consensus for interactive work.

**3 — A declarative spec.** The model writes data, never code. A fixed,
hand-written builder turns that data into a scene. This is what shotops does, and
the survey did not find another project doing it this way for shot work.

## Where MCP stands today

**Official, as of 2026-04-28.** Blender Lab — the Blender Foundation's
experimental program — ships an MCP server that wraps Blender's Python API, and
Anthropic shipped a Claude connector for it alongside eight other creative-tool
connectors, joining the Blender Development Fund as a patron with funding
earmarked for Python API and AI development. Source:
[projects.blender.org/lab/blender_mcp](https://projects.blender.org/lab/blender_mcp),
[announcement discussion](https://blenderartists.org/t/from-blender-mcp-to-3d-agent-anthropic-partners-with-blender-claude-ai-connector-now-official/1639106).

**Community, and much larger.**
[`ahujasid/blender-mcp`](https://github.com/ahujasid/blender-mcp) at ~26,200
stars is the de facto standard, with a long tail of forks specialising in tool
count (51, 69, 93 tools), verification, or headless operation.

## The two facts that decided the architecture here

**MCP requires a GUI Blender session.** The add-on runs inside a live Blender,
listening on `localhost:9876`; the MCP server is a separate process relaying to
it. The community add-on **refuses to start under `blender -b`**, and the
documented workaround on a headless machine is `xvfb-run` — a virtual display, not
background mode. There are also reported timeouts on longer operations such as
glTF export, with "use the headless CLI instead" as the advice.

For a pipeline whose whole point is `blender -b -P build_scene.py` in CI, on a
render node, reproducibly, that is disqualifying — not because MCP is bad, but
because it is built for a human sitting in front of the viewport.

**`execute_blender_code` is `exec()` with no sandbox.** Filed as
[issue #207](https://github.com/ahujasid/blender-mcp/issues/207): arbitrary
LLM-controlled Python, executed with the user's full privileges, in a process
that has your project directory open. There is a `weak_sandbox.py`, and the name
is honest. A separate [arbitrary file read](https://github.com/ahujasid/blender-mcp/issues/202)
was filed against an asset-generation tool. Prompt injection through scene
descriptions and `.blend` contents is a live vector, not a theoretical one.

A spec-driven builder has a smaller blast radius by construction: the model emits
JSON, a validator rejects it before Blender starts, and the only Python that ever
runs is code in this repository.

## What the research literature says

The academic line has been spec-and-code from the start, and its lesson is about
*structure before geometry*:

- **[SceneCraft](https://arxiv.org/abs/2403.01248)** (ICML 2024) — builds a scene
  graph as a blueprint first, converts spatial relationships into numerical
  constraints, writes Blender Python from that, then uses a VLM to look at the
  render and refine. Up to ~100 assets.
- **3D-GPT** — text → Blender scripts coordinated through relational scene graphs.
- **[BlenderLLM](https://github.com/FreedomIntelligence/BlenderLLM)** — a model
  fine-tuned to emit Blender/CAD scripts, with a `CADBench` benchmark.
- **[BlenderGym](https://blendergym.github.io/)** — 245 hand-built scenes across
  procedural geometry editing, lighting, materials, blend shapes and object
  placement. The benchmark exists because this is measurably hard.

Two things to take from it. **The intermediate representation is the product** —
scene graph, constraints, spec; the code is a rendering detail. And **the
vision-in-the-loop refinement is the missing half here**: shotops renders stills
but nothing looks at them. A cheap self-critique pass over `frames/` before
paying for generation is the clearest next step this literature points at.

## When to use which

| Use | Reach for |
| --- | --- |
| Deterministic, headless, versioned shot authoring | **spec** — the shotops case |
| Interactive modelling, "fix this mesh", exploring an existing `.blend` | **MCP** |
| Reading an unfamiliar scene, one-off surgery, retargeting | **MCP**, or a vetted script |
| Anything running unattended, in CI, or on someone else's files | **spec**, and no `exec()` |

The honest summary: MCP won the *assistant* problem — a human in the viewport,
asking for help. The spec wins the *pipeline* problem — no human, reproducible,
reviewable, auditable. shotops is squarely the second, and there is no reason it
cannot gain an MCP surface later for the interactive half.

## What this changes for shotops

**Do not adopt MCP for scene building.** It would trade determinism and headless
operation for interactivity we do not need.

**A vision critique loop is the strongest borrowable idea** — render, look,
adjust the spec, before any paid generation.

**Consider exposing shotops itself as an MCP server** eventually: `check`,
`render`, `takes`, `compare` are exactly the shape of validated tools, with no
`exec()` anywhere near them.
