# Generations — NYC flight

*A running log, one section per paid run. [brief.md](brief.md) is what was asked
for, [notes.md](notes.md) is what building the blockout taught; this is what the
video model did with it.*

---

## 001 — 2026-08-25, first test

Run by hand. Verdict at the time: **not bad for a rough test, with problems, and
the problems are understood.**

### Setup

| | |
| --- | --- |
| Task | `f5f64c19-28d1-40e5-b7f0-0c555080e32a` |
| Model | `seedance-2-mini-less-restriction`, 480p, 16:9, 10 s |
| `@video1` | `preview/..._6de41e_preview_v002.mp4` — the blockout |
| `@image1` | `styleframes/..._6de41e_styleframe_v001.png` |
| Result | `render/..._6de41e_render_v001.mp4`, 864×496, 241 frames |
| Compared | `artifacts/..._sheet_v005_vs_render_v001.jpg`, 16 columns at matched times |

Prompt: the standard reference contract, plus a look line changed by hand from
the spec's — `Colorful comic book style` in place of photorealistic, and `20mm`
corrected to match the camera. The rest of the look text unchanged.

The style still **was** generated from the first blockout frame. Its own
generation was loose, and that was a known risk taken deliberately.

### What the log says

- **Billing confirmed as documented.** `video reference total duration: 10.0s
  (10s), billing includes input + output duration`. Consumption: 6,900,000
  points for a 10 s shot against a 10 s blockout.
- **2 m 34 s** to generate: queued 18:55:37Z, started 18:55:46Z, ended 18:58:21Z.
- **The `@` tags are rewritten server-side.** We send `@video1` / `@image1`; the
  task recorded `Video 1` / `Image 1`. They are accepted and translated, not
  rejected — worth knowing before anyone "fixes" the tag format in
  `providers/base.py`.
- **Audio was switched on for us:** `audio: enabled=true (server hint applied)`.
  Not requested, not wanted, and not currently something the provider layer says
  anything about.
- **References become ephemeral assets** with `retention_hours=168`. The upload
  survives a week, so a re-run inside that window need not re-upload.

### What held

**The prompt furnished the world past the edge of the geometry.** This was *the*
open question in the brief, and the answer is yes. There is no bay, no bridge, no
sunset and no distant skyline in the blockout — above the roof line there is
literally nothing — and the result has all four, steady for the whole 3.4 s of
the reveal. **The rooftop backdrop does not have to be built.**

**Structure and timing.** All ten seconds, the crest where the blockout puts it,
the weave and the bank intact.

**The facade rhythm earned its keep.** The eight ledges came back as window rows;
the climb reads as a climb. The water tower primitive came back as an actual
water tower on legs.

### What broke

From roughly t = 20% to t = 40%, two raw white boxes sit in the road, untextured,
while the buildings, road, kerb and lamp posts around them are fully rendered.
They are `car_03` and `car_06` — the two mid-road cars at the weave peaks, the
closest geometry in the shot at 0.85 m, placed there deliberately to sell the
speed.

**The style still had no cars in the road; the blockout did.** That is the
sharpest part of the cause. The two references were handed contradictory accounts
of the same surface: `@video1` said *there are objects standing here*, `@image1`
said *the road is empty*, and the look reference is what the model was told to
take material from. There was no material for a thing the look reference does not
contain.

Proximity is the other half. The same cubes read as cars perfectly well in the
opening seconds at twenty metres, in a row along the kerb — distance lets the
model infer "car" from context and supply one. At under a metre, filling a third
of frame, corner-on, there is no context left and nothing in the silhouette to
infer from: a 1.9 × 4.6 × 1.5 box has no wheels, no cabin, no glass. Everything
that did survive close range — wall, kerb, parapet, poles — is a thing whose
primitive shape *is* its real shape.

Stated as a rule, because it cuts against the instinct that a blockout can stay
crude: **a primitive only has to look like its object at the distance it is seen
from — and the style reference has to contain that object at all.**

### Where to go next

Directions set by the user, in their order of priority. **Nothing here is
started.**

1. **A better style still.** The most critical. The look reference is doing more
   work than anything else in the pipeline, and this one was known to be loose.
2. **Colour the objects that matter and name the colour in the prompt** — cars in
   red, prompt says the red blocks are cars. Costs one field per object and no
   geometry at all, which makes it the cheapest thing on this list to test.
3. **Slightly more detailed car models,** so the silhouette itself carries the
   answer rather than relying on the prompt to.
4. **No style still at all** — a set of style reference images instead, with the
   prompt changed to match.
5. **Two to four style frames through the shot,** so the middle has a reference
   of its own rather than inheriting one made for frame 1.
6. **Rework the prompt.** What ran is a rough v1.
7. **A stronger model.**

Worth noting how (2) and (5) interact with what broke: (2) attacks the "no
material for this object" half directly and (5) attacks it too, by giving the
middle of the shot a reference that was made from the middle of the shot. (3)
attacks the proximity half. They are not alternatives — they address different
halves of the same failure, and testing them together would make attribution
impossible.
