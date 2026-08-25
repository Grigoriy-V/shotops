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

*Answered by 006, immediately below, and the answer was one field.*

---

## 006 — 2026-08-25, it went through

**The first shot in this project generated end to end by the pipeline.** 002 and
003 were typed into a playground; this one came out of `shot.json`.

### Setup

| | |
| --- | --- |
| Task | `034feab3-468a-4141-b053-a2246cbe351b` |
| Model | `seedance-2-fast-less-restriction`, 480p, 16:9, 10 s |
| `@video1` | the take's own `preview.mp4` — solid-car blockout, `e64594` |
| `@image1..3` | the same three look references that were refused twice |
| Result | `render/..._e64594_render_v004.mp4`, 3.9 MB |
| Compared | `artifacts/..._e64594_sheet_v010_vs_render_v004.jpg` |
| Cost | 10,500,000 points |
| Time | 2 m 34 s |

### The one field

005 → 006 changed exactly one thing:

```diff
- "config": {"service_mode": "public"}
+ "config": {"service_mode": ""}
```

Empty means *use the workspace setting*, which is what the playground's task
record shows and what the docs describe as the default. `"public"` pins PAYG.
Pinning it was this repo's own addition, never asked for by the API, and it is
the difference between two refusals and a finished shot.

**And it is probably not the explanation.** The user's read, taken as the
project's position: *`service_mode` may well be coincidence, and what actually
happened is randomness and imprecision in Seedance's content blocking.* Two
refusals against one success is not evidence that moderation is bound to the
billing mode. It is one clean single-variable difference and one lucky pass, and
those look identical from here.

The field stays empty because empty is the documented default and what the
playground sends — that much needs no theory. The theory is not settled and is
not being chased: **content-filter behaviour gets tested on real future shots,
where a refusal costs a shot rather than an experiment.** Confirming it
deliberately would also cost in the wrong direction: a re-run pinned back to
`public` is free if refused and bills 10,500,000 if not.

### What the result looks like

Structure held for all ten seconds. The two close cars at 13% and 27% come back
as a yellow taxi with a roof sign and a deep red saloon, fully rendered at the
0.95 m pass — the failure 001 was about, answered again on a different tier. The
wall climb reads as a climb, the parapet as a parapet, and the rooftop reveal
brings the bay, the suspension bridge and the far skyline out of the prompt
alone, exactly as 003 did.

### What broke: the water tank became a building

In the last seconds the blockout has a cylinder on the right filling a third of
frame — the rooftop water tank, and the closest thing in shot at that point. The
result puts a brick building with windows there instead.

The shot *does* contain water towers: two of them, centre and left, on legs with
pitched caps, exactly as a comic-book New York rooftop should have. The model put
them where its look references had them. It did not put one where the geometry
said, because nothing told it that the cylinder was one.

Three sources could have said so and none did. **The prompt never mentions a
water tank** — it describes light, haze and the bay, per the convention that the
prompt owns surfaces. **A cylinder is the silhouette of a great many things** —
a tank, a tower, a chimney, a rotunda. **And the look references are of other
places**, deliberately, since that is what stopped them contradicting the
blockout about the road.

The rule that follows is now in
[craft/modelling.md](../../../../docs/craft/modelling.md#how-much-detail-and-where):
a close object survives when the prompt names it, the blocking is specific
enough for the silhouette to say what it is, and a look reference contains one.
Miss any of the three and the result is not so much wrong as unpredictable.

Worth noting what this is *not*: it is not the 001 failure. That was distance —
a box too far from anything that explained it. Here the object was as close as
anything gets. Proximity does not help when nothing says what the shape is.

### What this settles about the pipeline

Everything `shot.json` claims, it now demonstrates. The prompt that produced 003
went out byte for byte; the three references resolved from paths relative to the
shot; `480p`/`16:9` came from `project.json` and the model and duration from
`shot.json`; audio went out `true`, matching the take being reproduced. The
manifest carries the task id, the uploader and the merged generation block, so
this run can be read backwards from a file on disk.

### Cost, updated

| Run | Model | Billed | Points | Per billed second |
| --- | --- | --- | --- | --- |
| 004 | `seedance-2-fast` | rejected | 0 | — |
| 005 | `seedance-2-fast-less-restriction` | rejected | 0 (10,500,000 held) | 525,000 |
| 006 | `seedance-2-fast-less-restriction` | 10 s in + 10 s out | 10,500,000 | 525,000 |

The held figure in 005 was the tier's true price, and 006 charged exactly it.

### What was deliberately not changed

`shot.json` still names `seedance-2-fast`. 006 ran on `-less-restriction` through
a `--model` flag, so **the config as committed does not reproduce this take
exactly** — it would send the cheaper tier. That is on purpose: if the refusals
were noise rather than the tier, `fast` is the honest default and 9% cheaper, and
006 gives no reason to believe otherwise. The flag is how a run departs from the
config; this entry is the record of which one did.

## 007 — H3Zero / MiniMax H3 `turbo_4`, protected Modal deployment

The first H3 test completed on the first submitted job. It used the 10-second
blockout, three ordered look references, the shot's verbatim
`generation.h3zero.full_prompt`, the `turbo_4` four-step LoRA, and an 864 x 480
canvas. H3Zero job `b6b795e4f74c41688589dbf0f37f3026` ran from 16:33:42 to
16:36:36 UTC end to end and produced a 4.3 MB MP4. The protected gateway was
checked before submission: an anonymous request returned 401 and an
authenticated health request returned 200 without invoking the GPU.

The matched-time evidence is
`artifacts/seq_010_sh_0010_street_a_e64594_sheet_v011_vs_render_v005.jpg`;
the kept result is
`render/seq_010_sh_0010_street_a_e64594_render_v005.mp4`.

### What held

The overall camera story holds: the result starts in the street, rises above
the buildings, and finishes on the bay and skyline. The comic-book treatment,
golden-hour colour, haze, suspension bridge, and distant towers are strong and
coherent through the full sampled timeline. The three look references clearly
control appearance rather than copying the grey blockout.

### What did not hold

This is not an exact structural reproduction. By 43% the blockout camera is
close to a facade that fills most of the frame, while H3 has already opened into
an aerial rooftop view. In the final third the skyline composition is stable,
but the blockout's large right-side cylinder is not preserved at the same
position or scale. The result follows the semantic trajectory much better than
the exact composition, object positions, and shot scale requested by the
prompt.

### Cost evidence

The Modal CLI does not expose a final invoice for this individual run. The
observed end-to-end wall time was 174 seconds and the four diffusion steps took
about 66 seconds after model initialization. At the deployment-time RTX PRO
6000 list rate, GPU compute is estimated below roughly $0.15 for this cold run;
CPU gateway/build work and persistent storage are separate. This is an
estimate, not a billed figure.

---

## 008 — H3Zero / Ref2VA on its own distillation

The first run after the checkpoint and the accelerator LoRA became request
parameters. Same shot, same references, same prompt and same four-step profile
as 007; the two things that changed are that reference conditioning ran on
**Ref2VA** instead of FL2VA, and that the step distillation loaded was
`ref2v_turbo_4` — the one distilled from those weights rather than from the
frame model.

| | |
| --- | --- |
| Task | `d95dbe05193f423ca990f17694473c92` |
| Model | `h3zero/ref2va/turbo_4`, 480p 16:9 (864x480), 10 s |
| Accelerator | `ref2v_turbo_4` (v0.1) |
| VRAM | peak 64.89 / 94.97 GiB — **the first measured figure** |
| Result | `render/..._e64594_render_v006.mp4`, 3.2 MB |
| Compared | `artifacts/..._e64594_sheet_v012_vs_render_v006.jpg` |

### What it settles

The plumbing: the checkpoint and the LoRA are selectable per request, the
executed graph reports back which ones actually ran, and the result is no longer
deleted from Modal. The VRAM sampler produced a real number, which corrected a
written assumption — the staged model sizes sum to 62.4 GiB and had been called
an upper bound on the working set, and the measured peak is higher than that,
not lower. Staged weights are a floor, not a ceiling.

### What it does not settle

**Not much, visually.** Read at first against 007 as an improvement in how the
climb was timed; the user's read on the finished clip was that it is
substantially the same result, and that is the one this entry records. The
mechanism supports it: both checkpoints go through the same conditioning node,
and that node appends reference latents as context beside the timeline rather
than binding reference frame `t` to output frame `t`. Changing which weights
read that context cannot fix a structural mechanism that is not there.

The water tank is still not the water tank: it comes back as towers on distant
roof edges rather than as the cylinder filling the right third of frame.

## 009 — the first H3 run that holds the blockout

Three things changed at once against 008, deliberately, because the question
was "can H3 do this at all" rather than "which knob matters":

1. **`base`, 30 steps, no accelerator LoRA at all** — instead of four distilled
   steps. In this graph there is no CFG (`BasicGuider`), so step count is the
   only lever on how hard conditioning is enforced.
2. **768p (1344x768)** — instead of 480p. MiniMax documents the short side as
   768 by default and does not mention 480p anywhere; every earlier H3 run in
   this log was below the resolution the weights were trained at. The
   `fl2v_turbo_4` LoRA is even labelled `768p` in its own filename.
3. **The prompt rewritten into MiniMax's six-section reference format**, with
   timecoded beats taken straight off the camera track in `street_a.json`.

| | |
| --- | --- |
| Task | `664a395b01b44d6da0cb6c95931073c5` |
| Model | `h3zero/ref2va/base`, 768p 16:9 (1344x768), 10 s |
| Accelerator | none — samples the checkpoint directly |
| VRAM | peak 69.3 / 94.97 GiB (73%) |
| Time | 21 m 03 s end to end |
| Result | `render/..._e64594_render_v007.mp4`, 4.1 MB |
| Compared | `artifacts/..._e64594_sheet_v013_vs_render_v007.jpg` |

### What held

**The structure, for all ten seconds.** This is the first time an H3 result does
that.

The decisive column is **t = 43%**, which is exactly where 007 and 008 broke: the
blockout has a facade filling the frame and the camera still climbing it, and
both earlier runs had already opened into an aerial. Here the result is a brick
facade filling the frame, window rows where the ledges are. The climb happens
when the blockout climbs.

At 29% the near car is a yellow taxi, corner-on, right of centre, where the
blockout puts a red box. At 57% the parapet crests with sky above it. And at
71% **the cylinder comes back as a rooftop water tank on a steel frame, at its
position and its scale** — the failure 006 named and 008 did not fix. The
difference is that this prompt names it, at its timecode.

### What did not hold

**The look.** The references are dense Spider-Verse illustration, hot pink and
orange, visible brush. The result is closer to muted photoreal cinema. The
references clearly supplied *content* — the water towers, the bay, the bridge,
the skyline all resemble theirs — but not the manner.

The likely cause is the prompt itself: `detailed_description` came out long and
written in physical terms, which pulls toward realism, and the one comic-book
line ended up buried in `retention_analysis`. `base` without a distillation may
pull the same way. Untested either way.

### What it does not answer

Three variables moved together, so this says H3 *can* hold a blockout and says
nothing about which change bought it. Separating them is the next cheap thing to
do, and 480p/`base` is the single most informative split, because it costs a
fifth of this run.

### What the research behind it found

Two findings outlast this shot and are written up in
[h3zero-modal.md](../../../../docs/h3zero-modal.md):

**H3-Context-IR is not in the open-weight release.** MiniMax's pipeline is
Context-IR, a hosted multi-stage preprocessor, feeding H3-Base. Only H3-Base is
released. Every earlier run in this log fed a free-form prompt straight to
H3-Base — that is, the input meant for the *previous* stage. The six-section
format is the shape of Context-IR's output, and writing it by hand is the
substitute MiniMax themselves point developers at. 009 is the first run that
gave H3-Base an input of the kind it expects.

**The reference video is context, not control.** The conditioning node encodes
it into a `minimax_refs` block re-injected every step and never denoised, while
the output latent starts empty; the text encoder sees the video at 2 fps. There
is no per-frame binding anywhere, and no depth, pose or ControlNet path exists
for H3. Reference video is guidance by construction, which is what the vendor
says as well.

### Recording, from here on

Copying the result out of `out/` into `render/` under its conventional name used
to be manual, and 008 and 009 both sat in `render/` under raw task ids until
they were renamed by hand. `generate` now does it, along with the comparison
sheet, which can only be named once the render has a number. `--no-publish`
opts out.

---

## Reading the point figures

Every Seedance entry above records cost in PiAPI points, because that is what the
task response returns. **Points are tied to cents: 100,000 points to the cent,
10,000,000 to the dollar.** Divide a point figure by ten million to read it in
dollars.

| Run | Tier | Billed | Charged | Effective | Site list price |
| --- | --- | ---: | ---: | ---: | ---: |
| 001 | `mini-less-restriction` | 20 s | $0.69 | $0.0345/s | $0.046/s |
| 002 | `fast` | 8 s | $0.384 | $0.048/s | $0.064/s |
| 003 | `fast` | 20 s | $0.96 | $0.048/s | $0.064/s |
| 006 | `fast-less-restriction` | 20 s | $1.05 | $0.0525/s | $0.070/s |

Two things fall out of it.

**Every run is charged at exactly 0.75 of the published 480p price** — the same
multiplier on all four tiers, so it is an account-level rate rather than a
per-model promotion. Which means the site's price list predicts the *ratios*
between tiers perfectly and the absolute figure not at all.

**The reference video is billed as well as the output.** No row reconciles
without twice the output duration: 10 s in plus 10 s out is 20 billed seconds,
and 002's four-second take is 8. 001 recorded this from a line in the provider
log; the arithmetic now confirms it independently. A blockout is not free to hand
over, which makes reference duration a cost lever and not only a quality one.

*This table was first written with the rate derived from the published prices,
which produced 7,500,000 points to the dollar and a $1.40 figure for 006. The
account says $1.05. The four runs really were mutually consistent — but internal
consistency fixes only the ratios, and the scale has to come from a bill.*
