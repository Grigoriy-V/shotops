# Documentation

Four kinds of document, kept apart on purpose. When something new is worth
writing down, the first question is which of these it is — a rule with no home
ends up in three files at three lengths, which is how this directory nearly went
wrong.

## Reference — how to use the thing

| | |
| --- | --- |
| [usage.md](usage.md) | Setup, the commands, output layout, what each one costs |
| [scene-spec.md](scene-spec.md) | The spec format, field by field |

## Craft — how to do the work well

| | |
| --- | --- |
| [craft/modelling.md](craft/modelling.md) | Building geometry a video model can read. Every rule carries the experiment that produced it. **Read before authoring a scene.** |

## Design — decisions and why

| | |
| --- | --- |
| [design/method.md](design/method.md) | How we decide what to build: examples first, and which tools are still n = 1 |
| [design/pipeline-structure.md](design/pipeline-structure.md) | Project → sequence → shot → scene, inheritance, naming |
| [design/core-and-extensions.md](design/core-and-extensions.md) | What a project may add without touching the core. Decided, not built |
| [design/feedback-loop.md](design/feedback-loop.md) | How an agent checks its own scene before spending anything |
| [design/camera-orientation.md](design/camera-orientation.md) | Why the camera has `roll`, `pan` and `tilt` on top of `look_at` |
| [design/ideas.md](design/ideas.md) | Directions considered and not started, with what each would test |

## Writing — the project explained outward

| | |
| --- | --- |
| [writing/shotops-ru.md](writing/shotops-ru.md) | The long-form article. Russian for now; an English version will sit beside it |

Not a doc in the sense the other three are. It argues rather than specifies, and
it is written for someone who has never seen the repository — so every number in
it is checked against the repository, and nothing is claimed there that is not
demonstrated here.

## Research — the ground it stands on

[research/](research/) — prior art, which models honour a blockout, agentic
Blender approaches, and blocking craft. Dated, with confidence marked, because
this field moves fast enough that an old note is a liability.

---

**Not here.** What a particular shot taught lives in that shot's `notes.md`, and
what a paid run did lives in its `generations.md`, next to the spec that produced
them. Working agreements — what you are allowed to do — are in
[AGENTS.md](../AGENTS.md) at the root. The product argument is the
[README](../README.md).
