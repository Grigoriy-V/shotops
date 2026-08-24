# Skills and MCP servers, per strand

*Surveyed 2026-08-24.* What already exists that we could adopt instead of
writing, organised by the project's three strands.

The Agent Skills format is portable — adopted by Claude Code, Codex, Cursor and
Gemini CLI — so a skill written here is not locked to one client.

## Strand 2 — agents driving Blender

This is where the ecosystem is thickest and the quality spread is widest.

**MCP servers.** [`ahujasid/blender-mcp`](https://github.com/ahujasid/blender-mcp)
(~26.2k stars) is the default; Blender Lab's official server is the
institutionally safer choice. Both need a GUI session — see
[agentic-blender.md](agentic-blender.md) for why that rules them out of this
pipeline. Notable variants: `sandraschi/blender-mcp` explicitly targets headless
via FastMCP, `PatrykIti/blender-ai-mcp` adds deterministic verification and
vision-assisted workflows, `glonorce/Blender_mcp` claims 69 tool groups and a
499-test suite.

**Skills.** Thin and unvetted. Surveyed named skills and their repo weight:

| Skill | Scope | Repo weight |
| --- | --- | --- |
| Game Developer | Unity, Unreal, ECS, shaders, optimisation | `Jeffallan/claude-skills`, ~403★ |
| 3D Modeling Specialist | topology, UV, retopology, DCC workflows | `majiayu000/claude-skill-registry`, ~78★ |
| Shader Techniques | HLSL/GLSL, Unity shaders | same registry |
| Three.js Agent Skills | R3F practice and performance | ~11★ |
| Blender 3D Modeling | `bpy`, `bmesh`, procedural generation | ~0★ |
| Code Buddy Blender Automation | CLI rendering, batch, MCP | ~3★ |
| CAD Agent | parametric CAD via build123d | ~2★ |

Single-digit-star repos executing in your environment deserve the same scrutiny
as any dependency. **Nothing here covers the actual need** — authoring a
validated scene spec and reasoning about camera and blocking. The nearest
neighbours are modelling and shader skills, which is a different craft.

## Strand 1 — AI rendering, blocking to generation

Effectively empty as *skills*. What exists is tooling:
[`motion-previs-mcp`](https://github.com/wassermanproductions/motion-previs-mcp)
turns reference footage into control packs (depth, OpenPose) over MCP, and
[`backblaze-labs/awesome-video-generation`](https://github.com/backblaze-labs/awesome-video-generation)
is a serviceable index of video-generation APIs and SDKs.

No skill encodes what this repo learned the expensive way: that a reference must
be *attached* by an explicit mode flag, that the two-reference split is what makes
style controllable, or that frames must be compared at matched normalised times.
That knowledge currently lives in `AGENTS.md` and the README.

## Strand 3 — pipeline as code

Nothing found. No skills, no MCP servers. Pipeline tools
([`pipeVFX`](https://github.com/hradec/pipeVFX)) are orchestration, not
agent-facing surfaces.

## Reading of it

**The gap is real and it is exactly where this project sits.** The ecosystem has
converged on "help a human model faster in a GUI". Nobody is packaging shot
authoring, provenance, or version-controlled production decisions.

**Adopt nothing wholesale right now.** The Blender skills are either
GUI/MCP-shaped or too thin to trust, and none of them target headless spec
authoring.

**Two are worth reading, not installing:** `PatrykIti/blender-ai-mcp` for how it
does deterministic verification, and `motion-previs-mcp` for how it packages
control signals for a generator.

**If skills get written here later**, the three that would carry real weight —
scene-spec authoring with the camera and blocking conventions baked in, the
reference contract for video generation, and take/generation hygiene — do not
exist anywhere else and would have to be written from this repo's own experience.
