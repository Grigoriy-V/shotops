# How H3 prompts are structured

*Recorded 2026-08-26. What MiniMax H3's prompt format is, what it can be told
about references, and which of it reaches our self-hosted route. The companion
file [h3-retention.md](h3-retention.md) covers `retention_analysis` on its own,
because it turned out to be the part with real leverage.*

**Confidence.** There is no first-party specification of this format in
MiniMax's public API docs — the platform documents an `H3-Context-IR` step that
"produces a structured representation with richer semantic detail" and does not
publish the structure. Everything below comes from vendor and community prompt
guides, so it is *(medium confidence)* at best, and the disagreement between
them is itself a finding: see [What is actually canonical](#what-is-actually-canonical).
Anything we have run ourselves is marked as such.

## The three reference kinds

H3 attaches exactly three kinds of file, tagged case-sensitively and numbered
per kind in upload order:

| Tag | Limit |
| --- | --- |
| `<Picture N>` | 9 images |
| `<Video N>` | 3 clips, 2–15 s each, 15 s total |
| `<Audio N>` | 3 clips, 2–15 s each, 15 s total |

No more than 12 files combined. *(These limits are in the platform docs and
corroborated by two independent guides — the one thing on this page that is not
second-hand.)*

**There is no `<Character>` or `<Subject>` reference kind** — a character reference is an ordinary picture, and identity is
declared in the prompt rather than at the attachment. That distinction is the
single most useful thing on this page.

*What reaches us:* our provider sends the blockout as `<Video 1>` and look
images as `<Picture 1>` upward, and
[refuses any other video number](../../src/ai_render/providers/h3zero.py) — see
[Chaining shots](#chaining-shots) for what that costs.

## The six fields

```
subject_definitions:
summary:
retention_analysis:
detailed_description:
overall_soundscape:
non_diegetic_music:
```

This is the shape our
[nyc prompts](../../projects/nyc/sequences/seq_010/sh_0010/shot.json) already
use, arrived at before this note existed. Two of the six we have been filling
badly, and both are about references rather than about the picture.

### `subject_definitions`

Declares reusable subjects as **`<Subject N>`** — a persona named once and
referred to by tag everywhere afterwards. The declaration is where a subject's
pictures get bound, and they are bound **inline and per attribute**, not as a
blanket citation:

```
subject_definitions:
<Subject 1> is the fictional adult woman whose facial identity and
shoulder-length copper curls come from <Picture 1>, and whose
forest-green jacket, cream shirt, and dark trousers come from
<Picture 2>.
```

Two properties of that example are worth keeping. **Each picture is cited for
the specific attributes it owns** — one picture for face and hair, another for
wardrobe — so the model is never left to infer which reference governs what.
And the subject is stated as *fictional*, which is how these guides consistently
write people.

The practical rule: wherever `<Subject N>` is introduced, the `<Picture N>` tags
that constitute it are named in the same sentence. A subject declared without
its pictures is prose; a subject declared with them is a binding.

### `retention_analysis`

Classifies how hard each reference is held, using a controlled vocabulary —
`fully_preserved`, `partially_preserved`, `attribute_transfer`, `weak_reference`.
[Its own file](h3-retention.md).

### The rest

`summary` is one sentence of intent. `detailed_description` is the shot itself;
our timestamped-beat style for it came out of nyc and is not something these
guides prescribe. `overall_soundscape` and `non_diegetic_music` are diegetic and
scored audio, and `None` is a valid value for the second.

## Assigning roles, generally

The recurring instruction across every guide is that **each reference must be
told what it controls, or the model blends them.** The roles named are identity
(which person, animal or product must stay recognisable), scene (environment,
lighting, composition), motion (movement, posture, rhythm, camera language), and
voice or style.

One guide is blunter and splits by kind: image references lock "identity: face
structure, hair, distinguishing marks, garment" but not lighting; video
references pin "motion, camera, grade and grain, not identity". That matches
what our own runs found from the other direction — the blockout drives structure
and the look images drive appearance — so it is at least consistent with
evidence we have.

## Consistency across a cut

**What MiniMax actually says.** Lock the subject description into a reusable
*character block* and repeat that same block at the start of every prompt, and
use the same reference image across generations. That is the official guidance
and it is unglamorous: same words, same picture, every shot. `Ref2VA` also lists
"clip continuation" among its capabilities, without saying how.

**What a third-party blog says**, and it is worth keeping separate: pass the
previous shot's *output* back in as a second reference video alongside the
character image, so the next shot inherits grade and grain as well as identity.
*(low confidence — [one vendor blog](https://www.atlascloud.ai/blog/tips/minimax-h3-reference-to-video),
not in the platform docs, which do not address chaining generations at all.)*

The distinction matters because the two cost very different things. The official
route is free and is what the [rooftop spot](../../projects/spot/script.md)
already does. Chaining would need a provider change — we attach one video, the
blockout, and raise on any `<Video 2>` — and it conditions the next shot on a
*generated* frame sequence, which is the classic way drift compounds down a
sequence.

So: the same character pictures in every shot, no chaining, and find out how far
that alone gets us. If it holds, chaining is unnecessary. If it does not, we will
know what problem chaining is being asked to solve, which is the only state in
which spending a provider change on it makes sense.

## Identity anchors

A repeated, cheap trick: give the character one or two **unambiguous physical
marks** — the example is "the scar above the right eyebrow and the folded white
towel" — chosen because they are checkable in every later frame. Consistency of
a generic face is hard to judge and hard to hold; consistency of a specific mark
is neither.

## Two conflicts that do not error

Reported against MiniMax's hosted API, where sending a first-frame `image` and
`refers` together **silently discards one of the two** and charges full price
with no warning in the response.

*Not applicable to our route* — we drive ComfyUI directly and there is no
`refers` parameter — but it is the right kind of failure to keep in mind: a
reference that is ignored looks exactly like a reference that did not work.

The second is ours and already recorded: an accelerator requested on a `base` or
`spectrum` profile builds a LoRA node with a null strength. Same shape of
problem, same reason it is worth naming.

## What is actually canonical

Sources disagree about whether the six-field structure is *the* format or one
house style among several. RunDiffusion documents it field by field with worked
examples; other guides covering the same model use free prose, timing blocks and
negative constraints, and one collection of forty prompts contains no
`retention_analysis` anywhere.

The honest reading: **H3 accepts prose, and the six-field structure is a
discipline for writing prose that the model parses well** — not a schema it
validates. That is consistent with the platform docs describing an intermediate
representation the model derives itself.

Which is good news for us. It means the structure cannot be "wrong", only more
or less legible, and that adopting `<Subject N>` and the retention vocabulary is
a change in wording rather than a bet on an undocumented API.
