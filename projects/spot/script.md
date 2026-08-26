# Rooftop — a 13-second car spot

*The script, before any geometry exists. Written first so the blocking argues
for itself and the specs are a transcription rather than an invention.*

## The idea

A car alone on a rooftop parking deck at first light. Someone crosses the deck,
reaches it, and drives away. Three shots, thirteen seconds, no dialogue, no
titles, no product name.

**The subject of this test is the person, not the car.** The same face has to
come back across a cut, from a different distance and a different angle, and
the only thing making that happen is a character reference image pinned into
both generations. Everything else in the spot is arranged to make that question
answerable.

The location earns its place by getting out of the way. A rooftop deck is a flat
plane, a low parapet, a few light masts and open sky: almost no geometry,
nothing above the car competing for attention, an unobstructed low sun. It is
also somewhere car commercials actually go, so the grammar will not read as an
exercise.

**Total 13.0 s** — 4.0 + 5.0 + 4.0.

## The character

A slim blonde woman with model features and an *office siren* look: hair pulled
back tight, dark-framed glasses, a tailored business suit. She is the only
person in the spot.

The reference images are supplied rather than generated, and **the written block
gets finalised against them, not before** — a description that disagrees with
its own pictures is worse than no description, because the model has to pick one
and will not tell us which.

Provisional wording, to be reconciled with the files:

```
<Subject 1> is a fictional adult woman: slim, blonde, model features,
hair pulled back into a tight low bun, rectangular dark-framed glasses,
a tailored charcoal suit over a white shirt.
```

Note what that does *not* say: **"office siren"**. It is a trend name, and a
trend name is a bet that the model learned the same reference set we mean by it.
The attributes are spelled out instead — which is also what the retention
vocabulary [asks for anyway](../../docs/research/h3-retention.md): the term
selects the mode, the enumeration is what actually gets held.

**Identity anchors.** The glasses are already one — a specific frame shape is
checkable in any frame in a way that "blonde" is not. One more of that kind,
decided once the references exist, would give us two things to look for across
the cut instead of a general impression of the same face.

## The character reference

This is the mechanism the whole spot exists to test, so it is worth being exact
about it.

**There is no `<Character N>` reference type.** H3 attaches exactly three kinds
of file — `<Picture N>`, `<Video N>`, `<Audio N>` — and a character reference is
an ordinary picture. The identity machinery is one level up, in the prompt:
`subject_definitions` declares reusable **`<Subject N>`** entries, each a persona
named once and referred to by tag everywhere after. Full note in
[h3-prompting.md](../../docs/research/h3-prompting.md).

**The subject and its pictures are bound in the same sentence, per attribute.**
This is the part that decides whether it works:

```
<Subject 1> is the fictional adult woman whose facial identity and
shoulder-length copper curls come from <Picture 1>, and whose
forest-green jacket, cream shirt, and dark trousers come from
<Picture 2>.
```

Each picture is cited for the attributes it owns — one for face and hair,
another for wardrobe — so the model is never left to work out which reference
governs what. A subject declared without its pictures is prose; a subject
declared with them is a binding. So the driver gets written once, in this form,
and pasted identically into both shots.

[`retention_analysis`](../../docs/research/h3-retention.md) then classifies how
hard each one is held, with a vocabulary we have not been using:
**`fully_preserved`**, `partially_preserved`, `attribute_transfer`,
`weak_reference`. The driver is `fully_preserved`. The blockout and the look
pictures are both `attribute_transfer` — a more accurate description of what
they have always done than the prose we wrote by hand, and, for the look
pictures, possibly a loosening we have already paid for the lack of.

So the contract has to **split by role**, and the split is what is new — not any
particular picture count:

- the look pictures — colour, light, material, rendering style;
- the character pictures — **`<Subject 1>` only**: face, hair, build, clothing.
  Not a style reference, and not evidence about the location.

**Neither group has a fixed size.** However many character references arrive,
they land as `<Picture N>` in upload order and get cited by number inside the
subject declaration. The prompt is written last, once the folder is populated,
so the numbering follows the files rather than the files following a guess.

Good news on the plumbing: our validator only inspects picture, video and audio
tags, so `<Subject 1>` passes through
[untouched](../../src/ai_render/providers/h3zero.py). No code change is needed
for any of this.

Worth watching in the result: look references dominate appearance — that was the
nyc lesson — and character portraits are now competing for the same authority.
If the deck comes back looking like wherever the portrait was shot, the split
failed, and the fix is in the wording rather than in the pictures.

## The world

Metric, Z-up. Deck surface is z = 0. The car sits at the origin facing **+Y**,
which is the direction of the open edge, the city, and the low sun.

The sun stays at the same azimuth in all three shots — the strongest continuity
lever available after the portrait. Three clips that agree about where the sun
is will cut together even when they disagree about everything else.

| | |
| --- | --- |
| Deck | plane, value 0.30 |
| Parapet | low wall along +Y at y = +14, 1.1 m, value 0.45 |
| Light masts | cylinders, 5.5 m, spaced down the deck, value 0.55 |
| Car | one `sedan` instance, `size [1.9, 4.7, 1.42]`, at `[0, 0, 0]` |
| Figure | 1.78 m, upright |
| City | distant scaled cubes beyond the parapet, value 0.55–0.62 |

One car, one footprint, three placements. Proportions are what a viewer tracks
across a cut without knowing they are tracking it.

Numbers below are blocking intent. The specs will carry the final ones.

---

## Shot 1 — the approach — 4.0 s, 35 mm

The camera is low and beyond the car, looking back down the deck. The figure
walks in from the far end toward the driver's door, growing into a readable
mid-shot; the car fills the right of frame throughout.

Walking toward the lens is deliberate: it is the framing that puts the face on
screen longest, which is the only reason this shot is first.

| t | beat |
| --- | --- |
| 0.0 | wide, figure small at the far end of the deck, car large on the right |
| 1.6 | figure closer, sun raking across the deck between them |
| 3.1 | mid-shot, face readable, car flank still holding the right of frame |
| 4.0 | figure arrives at the driver's door and stops |

Camera around `[-4.6, 3.2, 1.05]` easing back to `[-5.4, 4.4, 1.10]`, `look_at`
tracking the figure. Figure `[-4.2, -4.6, 0]` → `[-1.35, -0.3, 0]` — 5.2 m in
4 s, 1.3 m/s, an ordinary walking pace.

**The figure translates as a rigid body; the model supplies the gait.** It has an
overwhelming prior that a person moving across a deck is walking. The blockout
gives trajectory and timing, the model gives the legs — which is this project's
whole thesis pointed at a human.

That does mean shot 1 moves two variables at once, gait and face. Read it
accordingly: shot 2 is the clean read on identity.

**Built:** car, deck, parapet, masts, figure, its path.
**Invented:** gait, face, clothing, paint, sky, city.

## Shot 2 — the door — 5.0 s, 24 mm

A push in on the three-quarter front from the opposite side, so the figure is
seen from a **different angle than shot 1** — which is the entire point. Two
light masts pass close to the lens on the way.

The masts are not decoration. Parallax of foreground objects crossing frame is
not something a prompt can ask for, and it is the clearest available evidence
that the camera is authored rather than imagined.

The figure stands still, one hand on the top of the open driver's door, looking
out over the parapet.

| t | beat |
| --- | --- |
| 0.0 | wide, car small in frame, two masts between camera and car |
| 1.4 | first mast wipes the left of frame |
| 2.9 | second mast wipes closer and faster, car filling the centre |
| 3.6 | the figure is revealed past the mast, at the driver's door |
| 5.0 | tight on figure and door together, face large in frame |

Camera `[-7.5, -8.5, 1.65]` → `[-2.6, -2.2, 1.55]`, about eight metres in five
seconds. `look_at` starts on the body and ends on the figure. Masts at
`[-4.6, -6.2]` and `[-3.4, -3.9]`, both within half a metre of the camera path.

**Built:** car, open door, figure, both masts, deck, parapet.
**Invented:** face, clothing, hair — from `<Subject 1>`, and this is the frame
where we find out whether that worked.

## Shot 3 — leaving — 4.0 s, 50 mm

The camera is down at deck level near the parapet and does not travel. The car
starts at rest, accelerates past, leaves frame. The camera lets it go and holds
on the empty deck.

| t | beat |
| --- | --- |
| 0.0 | car static in the middle distance, low sun behind it |
| 1.1 | it starts moving, nose lifting |
| 2.6 | it crosses the lens, close and fast, filling frame |
| 3.3 | out of frame; empty deck, sun, dust in the light |
| 4.0 | hold |

Car animates `location` `[0, 0, 0]` → `[0, 26, 0]` with `in` easing: away from a
standstill, quickest at the end, around 47 km/h as it passes. Camera
`[-2.4, 6.0, 0.45]`, static, `look_at` tracking until about t = 3.0 and then
stopping, so the car exits frame rather than being followed out.

The driver is behind glass at speed here. Count that as a beat, not as evidence —
a face read through a windscreen in four frames settles nothing either way.

This is the one shot where the subject moves, and it moves as a rigid body along
a line, which is what the spec animates natively.

**Built:** car, its path, deck, parapet, masts.
**Invented:** wheel rotation, motion blur, dust, light.

---

## What has to hold across the cuts

- **The character references.** The same files in both shots, declared as the
  same `<Subject 1>`, held `fully_preserved`, and cited as the authority for the
  person and for nothing else.
- **Sun azimuth.** Identical in all three. Everything else may drift; this
  cannot.
- **Car proportions.** One asset, one footprint.
- **Deck surface.** Same value, so three clips read as one location.
- **Look references.** The same three on all three generations.

## How we will know

Shots 1 and 2 put the same person at two distances and two angles. Cut them
together and the question answers itself; `mosaic` will also hold them side by
side, which is the fairer look, since a face judged from memory across a cut
flatters the result.

The failure worth naming in advance is not a bad face — it is **two plausible
people**. That reads as fine in isolation and falls apart on the cut, which is
exactly why this needs two shots rather than one.

## Order of work

**Block everything before generating anything.** All three shots to blockout,
cut together into one thirteen-second sequence, watched as an edit. Only when
that holds does anything get sent to a model.

1. Shots 1, 2, 3 to spec and blockout, in that order, **one at a time**. Each
   shot is reported and approved before the next is started.
2. Concatenate the three previews into one clip, by hand with ffmpeg. No command
   for it yet — see the note at the end.
3. Watch it. Fix timing, framing and blocking at this stage — it is free here
   and it is not free later.
4. Then prepare the prompts and generate, again in shot order.

**The gate in step 1 is the point.** A shot approved individually can still be
wrong for the edit, but a shot that is wrong on its own is certainly wrong for
the edit, and finding that out after three are built means rebuilding around a
mistake instead of fixing it.

This is a change from how nyc was made, and the reason is that nyc was one shot.
A single ten-second take either works or does not; three shots have a property
no individual shot has, which is **how they cut**. A beat that is two seconds
too long, a reveal that lands before the eye has found the frame, a third shot
that repeats the second's angle — none of that is visible in a shot viewed
alone, and all of it survives into the generations unchanged, because the
blockout is the authority for timing and framing. Generating first would mean
paying to discover editorial problems that a grey render shows for nothing.

Within step 4, shot order matters for its own reason: shot 1 is where the
subject declaration is written and first tested, and shot 2 is only meaningful
against something to be consistent *with*. Generating the reveal first would
produce a face with nothing to compare it to.

**One gap to close before step 2.** `mosaic` tiles clips side by side; nothing
here concatenates them end to end. That is a small ffmpeg job either way — the
question is whether it is worth a command, and it probably is, since cutting a
sequence together is going to be a recurring need the moment shots stop being
solitary.
