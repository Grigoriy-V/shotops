# Research

Notes on the ground shotops stands on. Written 2026-08-24; every claim here is
dated because this field moves fast enough that a six-month-old note is a
liability.

| File | Question it answers |
| --- | --- |
| [prior-art.md](prior-art.md) | Who else is building this, and what did they get right first |
| [blocking-to-video.md](blocking-to-video.md) | Which models take a blockout as structural reference, and how people actually feed it |
| [agentic-blender.md](agentic-blender.md) | Spec vs MCP vs raw `bpy` — what each is genuinely for |
| [skills-and-mcp.md](skills-and-mcp.md) | What already exists as skills and MCP servers across our three strands |
| [craft.md](craft.md) | Blocking and camera craft, and which half of it belongs in the prompt |

**Confidence marking.** Sources are uneven: GitHub repos and arXiv papers are
checkable, vendor blogs and SEO comparison sites are not. Anything resting on the
latter is marked *(low confidence)* rather than quietly promoted to fact.

Two things worth knowing before reading:

**The core idea is not novel, and that is useful.** [`blockout`](prior-art.md)
shipped JSON-project-folders-you-can-diff before this repo existed — which means
the premise has been tested by someone else and the format questions have a
worked answer to borrow. Existing products here are a shortcut, not a threat.

**The most useful finding was a negative one.** The popular way to put an agent
in Blender — a live-bridge MCP server — [structurally cannot do what this
pipeline needs](agentic-blender.md): it needs a GUI session and refuses to start
under `blender -b`, by design. That is not a knock on MCP. It means the two
approaches answer different questions, and picking the wrong one is expensive.
