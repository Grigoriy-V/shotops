# ShotOps: Scene as Code for AI-native production

ShotOps started with a simple idea: **what if a CG scene existed as code, instead of only as a file inside a DCC?**

Camera, blocking, objects, transforms, timing, references, and generation settings are described as readable structured state. An agent can create and modify that state. Blender can build the scene from it and render a blockout. A generative model can turn that blockout into a finished shot. Git can keep the history of every change.

> **Agents author it. DCCs execute it. AI models render it. Git remembers it.**

---

## 1. First production case — NYC

**[IMAGE 1 — INSERT HERE]**  
`NYC blocking / H3 base`

The first production case is a ten-second fly-through of a NYC street.

The scene contains 104 objects, built almost entirely from simple primitives. A 20 mm camera travels roughly 112 meters, passes two cars at about 0.95 m, climbs a wall, and crests a rooftop.

On the left is the structured Blender blockout.  
On the right is the result from self-hosted MiniMax H3.

H3 preserves the main camera motion, timing, and staging even though the source scene is intentionally rough.

The same shot had already been generated through Seedance 2.

The renderer changed. The source scene did not.

That is the core ShotOps idea: **the shot should not belong to a specific DCC, agent, or video model.**

---

## 2. A new production loop: from handoffs to natural language

The classic production loop was not designed because it is the perfect way to create images.

It exists because the tools require specialized operators.

A typical loop looks something like this:

**Director / Art Director**  
→ Supervisor  
→ Artist  
→ DCC  
→ Preview  
→ Supervisor  
→ Director  
→ Notes  
→ Artist

Every iteration passes through several handoffs.

If the scene becomes structured state and an agent can build and modify it, a different loop becomes possible:

**Creator / Director / Art Director**  
→ natural language  
→ Agent  
→ Scene  
→ Render  
→ iteration

A person can say:

- “move the camera closer”;
- “make the car appear earlier”;
- “keep the staging, but restore the previous lens”;
- “give me three camera move variants”;
- “the character should take up one third of the frame”.

The agent is not only changing a prompt.

It is changing **the scene state itself**.

Blender rebuilds the blocking, and the AI renderer returns a visually finished version.

The important part is that every iteration remains **an editable, versioned scene**, not just another image.

For previs, tenders, pitches, and early development, this can radically shorten the path from an idea to a visual result — especially when one person is still deciding what they actually want.

---

## 3. Scene as Code: bringing IT principles into CG production

In traditional CG production, the scene usually lives inside a `.blend`, `.ma`, `.hip`, or another binary DCC file. History exists around it — versions, renders, playblasts, ShotGrid / Shotgun, comments, and links — but the changes themselves remain opaque.

`v018` is different from `v017`, but understanding exactly how often means opening both versions and reconstructing the context manually.

In ShotOps, the scene is stored as structured text:

- `camera`
- `blocking`
- `objects / assets`
- `transforms`
- `timing`
- `look references`
- `generation settings`

The Blender scene, blockouts, previews, and generations become **derived artifacts**, while the source of truth moves into versioned scene state.

That makes it possible to bring familiar IT principles into CG:

- Git diff instead of a comment saying “updated camera”;
- reverting one change instead of rolling back the whole scene;
- branches for parallel staging ideas;
- merging independent changes;
- reproducing a specific scene state;
- a readable history of how the shot evolved.

A diff can be as literal as:

`camera.focal_length: 24 → 20`

`car_02.position.x: 4.8 → 5.4`

`shot.duration: 8.0 → 10.0`

`look_reference: ref_a → ref_b`

That is **Scene as Code**: production state becomes inspectable, diffable, and reversible, while binary DCC files stop being the only place where the scene exists.

---

## 4. The agent as a production operator

The agent is one layer of ShotOps.

It can:

- build the scene;
- create the camera;
- place objects;
- change timing;
- launch Blender;
- generate previews;
- send generations;
- compare iterations.

It works through config rather than uncontrolled GUI state.

And it can check its own work before an expensive generation.

The sequence is:

**1. Deterministic checks**  
camera path, speed, acceleration, stalls, collisions, closest approach.

**2. Multi-view render**  
shot camera, top, front, and 3/4 views to inspect layout and camera path.

**3. Vision review**  
only where a mathematical check cannot answer the question.

This is how `audit` appeared: it uses the same baked camera path as the renderer and can stop an iteration before generation if the camera passes through geometry.

The principle is simple:

> **Deterministic checks first. Vision where it actually adds information.**

---

## 5. The renderer should not define the pipeline either

The next important layer is model abstraction.

The NYC shot has already gone through proprietary Seedance 2 and self-hosted MiniMax H3 on Modal.

**[IMAGE 2 — INSERT HERE]**  
`2×2 grid: blockout / Seedance 2 / H3 base / H3 spectrum or H3 8-step`

One scene state. Multiple render backends.

In the current tests:

- **Seedance 2** — around **2:34**, **$1.05**, low operational overhead;
- **H3 base** — around **21:03**, roughly **$1.06 GPU cost**, strongest H3 structural fidelity;
- **H3 spectrum** — around **13:57**, roughly **$0.70**;
- **H3 8-step distilled** — around **6:51**, roughly **$0.35**, faster and cheaper, but weaker on structure.

These numbers show different production trade-offs.

More importantly, the production pipeline no longer has to be built around a proprietary service.

Self-hosted open weights give control over:

- weights;
- sampler;
- steps;
- model lifecycle;
- deployment;
- cost;
- whether the same endpoint still exists tomorrow.

For ShotOps, that means:

**Scene State**  
→ **Model Adapter**  
→ Seedance / self-hosted H3 / future model

H3 makes another advantage of this approach very clear. The open weights include H3-Base, but not the hosted **H3-Context-IR** stage that turns free-form multimodal input into a structured representation for the model. In ShotOps, much of that work is already done by the system itself: the shot already exists as code, subjects, camera, timing, and scene structure are explicitly defined, and the agent already knows the full state instead of having to infer it again from a prompt. It can build the model-specific representation directly from the scene config and pass it to the adapter. With another model, only that translation layer changes — not the scene and not the production pipeline.

The renderer changes.

The way the shot is authored does not.

---

## 6. From a single shot to a sequence

NYC tested one long continuous shot.

The next experiment, `spot`, was deliberately different.

Four blockout shots with three cuts were assembled into a single reference video and sent to H3 in one generation.

A single character reference defined the same character across multiple shots.

**[IMAGE 3 — INSERT HERE]**  
`SPOT blockout sequence / H3 generated sequence`

The cuts were largely preserved, and the same character carried across shots.

Camera adherence and performance direction are still inconsistent, but the important result for ShotOps is:

> **The generation unit does not have to be a single shot. It can be a sequence.**

That opens a different production path: instead of generating every shot independently and assembling the edit afterward, an already edited blockout can become the structural reference for an entire sequence.

---

## 7. Who this is for, and where ShotOps is going

Today the market is split between two extremes.

On one side are prompt-first AI tools: fast, but production state quickly gets fragmented across prompts, chats, provider history, and folders.

On the other side is the traditional studio pipeline: high control, but with ShotGrid, DCC integrations, asset management, render infrastructure, and a dedicated pipeline team.

ShotOps sits between those two models.

**Prompt-to-video tools**  
low infrastructure overhead / low production control

**ShotOps**  
low-to-medium overhead / high control and traceability

**Traditional studio pipeline**  
high overhead / very high control

The main audience is:

- solo creators;
- small AI-native studios;
- small / medium production teams.

For larger studios, the natural entry point is previs, tenders, pitches, early creative development, and AI departments.

In short:

> **Studio-level production discipline without studio-level infrastructure.**

From there, ShotOps can grow from a system for scenes and shots into a broader production layer:

**Idea → Previs / Tender → Shots / Sequences → CG + AI Generation → Edit → Delivery**

Under that flow: version history, agents, assets, model adapters, approvals, generation logs, shot status, cost analysis, and time analysis.

The goal is not another AI renderer, and not simply a faster version of the existing CG pipeline.

The goal is an **alternative to DCC-centric production**, where one versioned production system connects people, agents, DCCs, open and proprietary models, and the full path from idea to delivery.
