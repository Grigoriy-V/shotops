# Craft: blocking, camera, and what to say to the model

*Surveyed 2026-08-24.*

## The split this pipeline forces

In ordinary AI video the prompt carries everything, so guides teach you to write
camera language into it — "dolly zoom", "low angle", "orbit". Here the camera is
**geometry, not vocabulary.** It lives in the scene spec under `projects/` and
arrives as a reference clip.

That relocates the craft rather than removing it:

| Craft | Where it lives here |
| --- | --- |
| Blocking, staging, camera movement, shot scale, timing | the spec — this is directing |
| Light logic, material, atmosphere, lens character, grain | the prompt and the style still |
| Continuity across shots | nowhere yet — see the open problem below |

The practical consequence is a rule, and it is the opposite of what every AI
video guide says: **do not put camera language in the prompt.** The reference
contract already tells the model to take camera motion, composition and shot
scale from `@video1`. Adding "sweeping crane shot" to the prompt gives it a
second, weaker, contradictory instruction. The prompt's job is surfaces and
light.

## The durable sources

Blocking craft predates all of this and did not change. These are the references
worth actually working through, in order of usefulness to this project:

**Steven D. Katz, *Film Directing: Cinematic Motion*** — a staging workshop built
around **24 basic variations** covering common dialogue and dramatic situations.
This is the single most directly applicable text here, because those variations
are effectively *parameterised camera-and-actor patterns*: a subject
configuration, a camera path, a reason. That is the shape of a scene preset. A
library of Katz variations expressed as JSON would be a real contribution and
would give an agent something better to reason with than "put the camera
somewhere nice".

**Steven D. Katz, *Film Directing Shot by Shot*** — the broader catalogue:
continuity style, staging dialogue, spatial connections, depth of frame, angles,
point of view, moving-camera shot types, with 750+ illustrations and boards from
*Empire of the Sun*, *The Birds*, *Citizen Kane*. Its departure point is
Hollywood continuity style — the grammar 99% of what anyone watches is built on,
and therefore the grammar the video models were trained on.

**[Hollywood Camera Work — Master Course in High-End Blocking & Staging](https://www.hollywoodcamerawork.com/the-master-course-in-high-end-blocking-and-staging.html)**
— a systematised language of single-camera blocking. Video, expensive, and the
most rigorous treatment of the specific thing this pipeline authors.

The point of citing books in a research note about AI: the models are trained on
a century of continuity cinema. Feeding them blocking that obeys that grammar is
not nostalgia, it is *hitting the distribution*. Blocking the model has seen ten
thousand times generates cleanly. Blocking that violates it fights the prior.

## Prompt craft, as it applies to the half we still write

From the Seedance-specific guides — camera-language catalogues of ~14 techniques
and prompt collections *(low confidence individually; they agree with each other,
which is worth something, and they are SEO-driven, which is worth less)*:

- **Technical terms beat adjectives.** "Beautiful", "amazing", "cinematic" carry
  almost no signal. Named optical and lighting behaviour does.
- **One lighting logic, stated once.** Where the light comes from, how hard, what
  colour. Contradictions get resolved arbitrarily.
- **No mutually contradictory physical instructions.** The model will satisfy one
  and drop the other, silently.
- **Give subjects something to do.** Static verbs — standing, sitting — produce
  dead frames; specific small motion produces life. Applies to us mostly through
  atmosphere: haze drift, dust, reflections moving.
- **Roughly 50–120 words.** Long prompts dilute; short ones under-specify.

The `demo_room` prompt already follows most of this by accident. Worth making it
a documented convention rather than a habit.

## What our own runs have shown

*High confidence — these come from generations on this repo's own shots, not from
the survey. Full accounts live next to the specs that produced them.*

These are about the **references and the model**. What they imply for the
geometry — how much detail, where, and what colour is for — is stated as rules
in [craft/modelling.md](../craft/modelling.md), which is the file to read before
authoring a scene.

- **Every reference must agree about what is in frame.** A blockout saying
  *objects are standing here* against a style still saying *the road is empty*
  gets resolved by dropping the objects. This is the failure mode of restyling
  the blockout's own frame: the still is made before the dressing is trusted,
  and then contradicts it.
- **Say which reference owns appearance.** "The video is a guide for movement
  and composition only; appearance comes solely from the images" is the line
  that separated the two. Without it the model treats the blockout as art
  direction.
- **Look references need not describe the scene at all.** Unrelated images
  carrying only palette and render style work, and they cannot contradict the
  blockout about staging, because they are not describing that street. This is
  the cheaper and more robust arrangement than a style still per shot.
- **A copyright refusal is not necessarily about the reference.** Three frames
  from a released feature were rejected twice through the API — *"rejected due
  to copyright restrictions"* — on two different model tiers, having been
  accepted twice through the same vendor's playground. The variable turned out
  to be neither the images nor the tier but `service_mode`: pinned to `public`
  it was refused, left empty as the playground leaves it, the same request
  completed. One success is not proof, and the lesson is not that the filter can
  be talked around. It is that **a content verdict is still an API response, and
  worth diffing against a request that worked before it is read as a judgement
  about the content.**
- **Finding out is free, in one direction.** A rejected task freezes its points
  and restores them; only a generation that completes is billed. That makes
  probing what gets refused cost nothing — and confirming what gets accepted
  cost full price.
- **Trim the blockout before probing.** Billing is linear in input + output
  duration, so a four-second cut of a ten-second shot costs 40% of the run. Most
  dressing failures happen in the first seconds, where the camera is closest.

## The open problem: more than one shot

Everything above concerns a single shot. The moment there are two, the craft that
matters is **the grammar of the cut** — meaning made by juxtaposition, not by
either image alone. Continuity rules (screen direction, the 180° line, eyeline
match, cutting on action) are what make two shots read as one space.

Here is why that is interesting for this project specifically: **those rules are
checkable.** Screen direction and the 180° line are geometry, and the geometry is
in the spec. A validator that warns when consecutive shots cross the line, or
when a subject flips screen side, would be enforcing film grammar in code — the
kind of thing that is impossible when the scene is a binary blob, and nearly free
when it is JSON.

No other project found in this survey is doing that.

## Previs, for context

Previs in 2026 spans hand-drawn boards, 2D and AI-generated sequences, 3D previs
and real-time virtual production, with AI making the early cheap end faster. The
recurring framing in the trade material is the correct one: *the craft still
decides the shot; AI just lets you see it sooner.* That is the same argument as
the [README's case for the tender and previs stage](../../README.md#who-this-is-for),
arrived at from the other side.

## What this changes for shotops

**Write down the prompt convention** — surfaces and light only, no camera
vocabulary, one lighting logic, 50–120 words. It is currently tribal knowledge.

**Encode staging patterns as scene presets.** Katz's 24 variations are the
obvious starting library, and they turn "author a shot" from an open-ended
generation problem into choosing and parameterising a known pattern.

**Continuity as validation** is the strongest original idea in this whole survey:
the 180° line is checkable arithmetic once shots are data.

Sources: [Katz, *Film Directing Shot by Shot*](https://www.amazon.com/Film-Directing-Shot-Visualizing-Productions/dp/0941188108),
[Katz, *Cinematic Motion*](https://books.google.com/books/about/Cinematic_Motion.html?id=NvvChOnxZJkC),
[Hollywood Camera Work](https://www.hollywoodcamerawork.com/the-master-course-in-high-end-blocking-and-staging.html),
[Seedance camera language guide](https://www.jxp.com/blog/seedance-2-0-camera-language-guide),
[Seedance camera prompt collection](https://www.xmk.com/seedance/blog/seedance-2-camera-prompt-guide),
[grammar of the cut](https://medium.com/@Micheal-Lanham/learn-ai-filmmaking-with-seedance-2-0-day-6-the-grammar-of-the-cut-08e39527f79c),
[blocking and staging guide](https://peekatthis.com/guide-to-blocking-and-staging-in-film/).
