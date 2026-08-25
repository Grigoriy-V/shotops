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
closest geometry in the shot at 0.89 m, placed there deliberately to sell the
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

Directions set by the user, in their order of priority. *Where each one now
stands is tracked at the end of 003, not here — this is what was decided on the
day.*

1. **A better style still.** The most critical. The look reference is doing more
   work than anything else in the pipeline, and this one was known to be loose.
2. **Colour the objects that matter and name the colour in the prompt** — cars in
   red, prompt says the red forms are cars. Costs one field per object and no
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
halves of the same failure.

**Which is the cost of doing (2) and (3) together, and it is a real one.** If the
next run comes back with cars in the road, the result will not say whether the
colour, the silhouette or both were responsible. That was a deliberate choice —
both are scene work and the shot wants both regardless — but it means the next
generation is a test of the *shot*, not of a hypothesis. Separating them later
costs one file: a second scene in this shot with the colour and the old cubes,
which is what parallel variants are for.

Both were answered by 002 and 003, below. The attribution cost was paid as
predicted, and then some.

---

## 002 — 2026-08-25, four seconds, no style still

Run by hand in the provider's playground, not through the CLI. A deliberately
cheap probe: the first four seconds of the shot only, to see whether the new
cars survive close range before paying for a full ten.

### Setup

| | |
| --- | --- |
| Task | `711402f5-3ee9-43af-811d-9bd3fa5aa5ac` |
| Model | `seedance-2-fast`, 480p, 16:9, **4 s** |
| `@video1` | the 4 s trim of `preview/..._64dd03_preview_v003.mp4` |
| `@image1..3` | `styleframes/lookref_a.png`, `_b`, `_c` — three frames from a released animated feature, as look references. Which local file was which `@image` is not recoverable from the log. |
| Result | `render/..._64dd03_render_v002_4s.mp4`, 864×496, 97 frames |
| Compared | `artifacts/..._64dd03_sheet_v007_vs_render_v002.jpg` |
| Cost | 3,840,000 points |

**Three things changed at once from 001** — the scene (new cars, new colour), the
model (`seedance-2-fast` in place of `seedance-2-mini-less-restriction`), and the
whole approach to the look reference. Nothing here is a controlled experiment.

**This is direction (4), and it is the interesting part.** There is no style
still. The one generated from the blockout is gone, and in its place are three
unrelated images that carry only the look. That inverts the reference contract:
`@video1` owns the motion and the staging, the images own the palette and the
render style, and neither is asked to agree with the other about what is in the
road. The contradiction that broke 001 cannot arise, because no look reference
is describing this street.

### What held

**The cars came back as cars.** This is the 001 failure, and it does not recur.
At the close pass they have bodies, windscreens, wheels, tail lights and number
plates. Either the silhouette, the colour, the reference change or the model did
it — see the attribution note above; the shot works, the hypothesis does not.

### What broke

**Everything landed in one warm band.** Buildings, road, haze and cars all sit
in the same orange-red register, so the cars separate from the blocks by
brightness alone and barely by hue. The car colour the spec asks for is red;
the sun down the street is amber; the model resolved the two by painting the
whole frame in that key.

Which makes the red suspect rather than proven. It was chosen so the prompt
could *name* the objects; what it appears to have done here is also set the
palette.

---

## 003 — 2026-08-25, the full ten

Same three look references, same model, full length, prompt reworked. The user's
verdict: **this closes the stage.** Good enough as a proof of concept and as a
fast previz. There is flickering, read as a limit of the model at 480p rather
than of the pipeline — the contact sheet cannot confirm or deny that, sixteen
stills being the wrong instrument for temporal noise.

### Setup

| | |
| --- | --- |
| Task | `7253e8b0-671b-4641-9ee0-3c13c734d774` |
| Model | `seedance-2-fast`, 480p, 16:9, 10 s |
| `@video1` | `preview/..._64dd03_preview_v003.mp4` |
| `@image1..3` | the same three look references as 002 |
| Result | `render/..._64dd03_render_v003.mp4`, 864×496, 241 frames |
| Compared | `artifacts/..._64dd03_sheet_v008_vs_render_v003.jpg` |
| Cost | 9,600,000 points |
| Time | 3 m 06 s |

### What changed in the prompt

Two additions, and they are the whole difference:

> Don't rely on the appearance of the objects or the reference video. The
> appearance is determined solely by the reference images.

and the backdrop written out explicitly — the bay, the suspension bridge, the
distant towers — where 001 and 002 left it to "golden hour" and hope.

### What held

**The near cars are a yellow taxi and a dark saloon.** At 13% and 27%, at the
0.95 m pass, both are fully rendered with tail lights, plates and a roof sign.
This is the thing 001 got wrong, answered as completely as it can be.

**They are not red.** The spec paints them `[0.75, 0.08, 0.06]` and the model
overrode it from the look references. Which is the finding worth keeping:

> **Colour in the blockout is a marker, not a specification.** It says *there is
> one object here and this is where it ends*. What the object is finally painted
> comes from the look reference. Naming the colour in the prompt is how the two
> stay attached — and releasing the model from it, as 003 does explicitly, is
> what stops the marker from leaking into the palette.

002 → 003 is a one-variable change on that point, near enough: same model, same
references, same scene, and the warm-on-warm flattening is gone. The frame now
separates cool blue-grey masonry from the warm sun down the street.

**The backdrop, again, and better.** Bay, suspension bridge, skyline, water — all
of it from the prompt, none of it in the geometry, held steady for the whole
reveal. The water tower primitive comes back as a water tower on legs, the
parapet as a parapet, the AC units as AC units.

**The wall reads.** The eight ledges become window rows; the climb from 40% to
60% is legible as a climb rather than as a grey pan.

### What is still open in the result

- **Flicker**, per the user's read above. Unmeasured.
- **The empty stretch at 60%** is a pale wash — the blockout is a flat facade
  filling frame with the sky above it, and the result is not much more. The
  moment before a reveal is the one with least to hold onto.
- **The three look references are frames from a commercial film.** Fine as a
  look probe, which is what this was. Not a house style, and not something to
  build a pipeline default on.
- **`styleframes/v002.png`** — a comic-book street with red cars and a dead-end
  building, generated but used by neither run. Worth a run of its own, since it
  is the one look reference that actually contains *this* street.

### Cost, which is now a straight line

| Run | Model | Billed | Points | Per billed second |
| --- | --- | --- | --- | --- |
| 001 | `seedance-2-mini-less-restriction` | 10 s in + 10 s out | 6,900,000 | 345,000 |
| 002 | `seedance-2-fast` | 4 s in + 4 s out | 3,840,000 | 480,000 |
| 003 | `seedance-2-fast` | 10 s in + 10 s out | 9,600,000 | 480,000 |

Exactly linear in billed duration, and `fast` is 39% dearer per second than the
mini. The practical consequence is 002's whole reason for existing: **a four-
second probe costs 40% of the ten-second run.** Trimming the blockout is the
cheapest instrument in the pipeline for anything that fails in the first
seconds — which is where close-range dressing fails.

### The config, captured

*Added after the fact.* 002 and 003 were run in the playground, so for a while
the best result in the project could not be reproduced by the project: the spec
still said `seedance-2-mini`, a photorealistic prompt and no look references.
That is now closed. `shot.json` carries the model, the prompt and the three
references — the shot's `generation` block, not the scene's, because
`street_a.json` and any variant beside it have to be generated identically or
the comparison between them says nothing about the staging.

**The prompt goes out exactly as it was tested.** The first attempt at this
regenerated the contract from the pipeline's own template — more specific about
what `@video1` owns, plus a line telling the model to take no framing from the
images — which is a better-sounding prompt and an untested one. 003's text is
the text that produced the result being claimed, so `generation.full_prompt`
holds it verbatim and nothing is prepended. `check` says so out loud, and the
only thing it guards is the one error a verbatim prompt can make alone: naming
`Image 3` when the scene attaches two references.

`prompt` still exists and still gets the generated contract. It is the right
field while a look is being searched for; `full_prompt` is the right field once
a wording is the reason a take works.

The prompt keeps `20mm anamorphic`, which had been struck out of the earlier
prompt as camera vocabulary in a shot where the camera is geometry. It came back
by hand in 002 and stayed for 003. It is at least no longer *wrong* — the scene
renders on a 20 mm lens — and it is in the config that produced the good take,
so it stays until something argues otherwise.

Changing the prompt changes the scene id: `64dd03` → `a341b4`, on a scene whose
geometry did not move a millimetre. Everything already on disk still carries
`64dd03` and still records what made it. Whether a blockout's id should depend
on the prompt at all is an open question about `scene_id`, not about this shot.

### Where the seven directions stand now

1. **A better style still.** **Overtaken.** Replaced by (4) rather than done.
   The unused `v002.png` is the one still worth testing.
2. **Colour and name it.** **Built and tested** — but see the marker finding:
   it works as an attachment point, not as a paint order.
3. **More detailed cars.** **Built and tested.** The close pass survives.
4. **No style still, a set of look references instead.** **Built and tested,
   twice.** This is the change that carried both runs.
5. **Two to four style frames through the shot.** **Not started**, and less
   urgent now: (4) removed the reason the middle of the shot needed its own
   reference.
6. **Rework the prompt.** **Done for now** — the lens is out, the objects are
   named, the backdrop is written, and the model is told which reference owns
   appearance.
7. **A stronger model.** **Not started.** 003 ran on `fast`; the ceiling above
   it is untested, and the flicker is the first thing that would test it.

---

## 004 — 2026-08-25, the first run through the CLI, rejected

The point of this one was not the shot. 002 and 003 were run by hand in the
playground; `shot.json` had since been made to describe them, and nothing had
ever sent it. **A config that has never been sent is a claim, not a
reproduction.**

### Setup

| | |
| --- | --- |
| Task | `a0d1ee95-acfe-40ac-ada9-c37439ff880e` |
| Model | `seedance-2-fast`, 480p, 16:9, 10 s — merged from `project.json` and `shot.json`, not typed anywhere |
| `@video1` | the take's own `preview.mp4` — the solid-car blockout, `e64594` |
| `@image1..3` | `styleframes/lookref_a/b/c.png`, resolved from the shot directory |
| Result | **none.** `status: failed`, `code 10003` |
| Cost | **nothing.** `consume: 0`, `frozen: 0`, `restored frozen points` |

### Rejected on copyright, not on anything we built

```
error:  Your content violated community guidelines.
logs:   The request was rejected due to copyright restrictions.
        Attempt 1 failed (content restriction), retrying.
        The request was rejected due to copyright restrictions.
```

The three look references are frames from a released animated feature. The same
three files went through the playground twice, in 002 and 003, and were accepted
both times; through the API they were refused three times in a row. Why the two
routes disagree is not known, and guessing would be worse than saying so.

What it settles is not in doubt: **the best result in this project rests on
references it has no right to.** `generations.md` already carried that as a
caveat under 003 — *fine as a look probe, not a house style*. It is now a hard
constraint. The `-less-restriction` task variants exist and are the wrong
instrument here: the block is a correct copyright decision, not a false
positive.

### What the run did prove

Everything up to the model, which was the whole reason to run it:

- **The blockout is deterministic.** A fresh `render` of the current spec
  produced `scene_id e64594` — the id the committed `preview_v004` already
  carried — and `ffmpeg -f framemd5` matched the two videos frame for frame.
  Only the container hash differs, on metadata.
- **Inheritance resolves the way the docs say.** `resolution: 480p` and
  `aspect_ratio: 16:9` came from `project.json`, `model` and `duration` from
  `shot.json`, and the three references from paths relative to the shot
  directory. `run.json` recorded the merge, so this is checkable, not asserted.
- **The prompt went out verbatim**, and `check` said so before anything was
  uploaded.
- **The upload cleaned up after itself.** All four files — blockout and three
  references — were removed from storage on the failure path, not just on
  success.

### Two bugs it found, both fixed

The failure was the useful part, because it exercised the paths a successful run
never touches.

**`run.json` did not record the task id.** It had to be read out of stdout. That
breaks the one guarantee that matters when money is involved: `fetch` recovers a
generation the download lost, and it needs the id. The id is now written by an
`on_task` callback **before polling starts** — the moment after which the run
belongs to the provider.

**The manifest kept the category and dropped the cause.** `error` read *"Your
content violated community guidelines"*, which names nothing to change; the
sentence that does — *"rejected due to copyright restrictions"* — was in the
task's `logs`, which the poller printed only on success. Both are now printed
and both go into the exception, so both reach the manifest. Repeated lines from
the provider's internal retry collapse to one.

Both are covered by tests built from this task's own response.

### What is open

The look references. 004 cannot be repeated as written, and neither can 003.
`styleframes/v002.png` — our own generation, and the only reference that depicts
*this* street — is still unused, but the prompt names three images and there is
one. That is a look decision, not a code one.

---

## 005 — 2026-08-25, the same refusal on a different tier

One variable moved from 004: `seedance-2-fast-less-restriction` in place of
`seedance-2-fast`. Same blockout, same three references, same prompt, same
Supabase upload. Free again — `restored frozen points`, `consume: 0`.

| | |
| --- | --- |
| Task | `5be024f3-e0a8-4787-881e-78de242fc864` |
| Verdict | `failed` — *"The request was rejected due to copyright restrictions."* |
| Held while running | `frozen: 10,500,000` |

### What it settles

**The model tier is not the variable.** Two runs, two tiers, one verdict. What
is left is the references themselves.

**Nor was the transport.** The docs warn that "signed / expiring URLs may fail",
and the Supabase route publishes exactly those. It was worth removing as a
suspect and it is now removed as a cause: the service fetched all four files and
converted them to assets before rejecting the content. Whatever refused this,
it had the pixels.

**Rejection is final on `-less-restriction`.** 004's log shows *"Attempt 1
failed (content restriction), retrying"*; this one has a single rejection. The
docs say so, and the logs agree.

### What it revealed, unasked

```
auto_upload_assets enabled, retention_hours=168, asset_quota_hold_hours=3
auto_upload_assets: converted 4 url(s) to ephemeral asset://
```

**The `-less-restriction` tier puts every reference through the Private Asset
Library by itself.** The task's `input` came back with `image_urls` and
`video_urls` rewritten to `asset://asset-20260825223231-…` — ours were never
sent as URLs at all past that point.

Which answers a question that was about to be asked separately: pre-uploading
assets by hand would not have changed this verdict, because moderation runs
after the conversion, not before it. What manual upload *would* buy is an id we
chose and can reuse — and reuse across shots is the interesting half, since
"stable consistency across shots" is the open problem in
[craft.md](../../../../docs/research/craft.md#the-open-problem-more-than-one-shot).
Worth remembering that the library is a cache, not an archive: assets are purged
after 3 to 15 days idle depending on plan.

### Cost, updated

| Run | Model | Billed | Points | Per billed second |
| --- | --- | --- | --- | --- |
| 001 | `seedance-2-mini-less-restriction` | 10 s in + 10 s out | 6,900,000 | 345,000 |
| 002 | `seedance-2-fast` | 4 s in + 4 s out | 3,840,000 | 480,000 |
| 003 | `seedance-2-fast` | 10 s in + 10 s out | 9,600,000 | 480,000 |
| 004 | `seedance-2-fast` | rejected | 0 | — |
| 005 | `seedance-2-fast-less-restriction` | rejected | 0 (10,500,000 held) | 525,000 |

The held figure is the price of the tier, visible because a rejected task freezes
before it refunds: **`-less-restriction` is about 9% dearer than `fast`.**

And the thing worth saying plainly, because it changes how cheap this whole line
of enquiry is: **a rejected task costs nothing.** Points are frozen at the start
and restored on refusal. Probing what a model will accept is free; only success
bills.

### What changed in the pipeline because of these two runs

- `run.json` now carries `task_id`, written before polling.
- A failed task's real reason travels in the error, not just the vendor's
  category. 005's manifest reads the whole log, which is how the
  `auto_upload_assets` lines were noticed at all.
- `audio` follows the API's default of true, which is what 003 ran with. 005's
  `input` confirms it: `"audio": true`.
- There are two uploaders now, `AI_RENDER_UPLOADER` choosing. Kept, though 005
  showed the signed URL was never the problem.

### Still open

Unchanged and now the only thing in the way: **the same three files were
accepted through the playground on 24 August and refused twice through the API on
the 25th.** No explanation is available from either log, and the difference is
not the tier, not the transport, and not the prompt. Whatever the reason, these
references cannot be sent from here — which makes the look reference a decision
to be made, not a bug to be found.
