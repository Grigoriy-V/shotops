# `retention_analysis`, and why it may matter more than the rest

*Recorded 2026-08-26. Split out of [h3-prompting.md](h3-prompting.md) because
this one field addresses a failure we have already paid for.*

## What it is

One of the six fields in H3's structured prompt. It states, per reference, **how
hard that reference is held** — using four terms that recur across the guides as
a controlled vocabulary rather than as prose:

| Term | What it appears to mean | Evidence |
| --- | --- | --- |
| `fully_preserved` | every named attribute survives unchanged | worked example *(medium confidence)* |
| `partially_preserved` | some attributes carry, others may drift | named only; no example found *(low confidence)* |
| `attribute_transfer` | take a *quality* from this reference without copying its content | worked example *(medium confidence)* |
| `weak_reference` | minimal influence; a hint | named only; no example found *(low confidence)* |

The two we have worked examples for are the two we need. The other two are
recorded so that nobody re-derives the list, not because we understand them.

## The two examples, verbatim

`fully_preserved` — "retain identity, copper curls, mole, proportions, green
jacket, cream shirt, and dark trousers".

Note what that is: **an enumeration, not an adjective.** The strength term
selects the mode; the list that follows is what actually gets held. A
`fully_preserved` with nothing enumerated is a strength setting pointed at
nothing.

`attribute_transfer` — "transfer the three measured steps and slow half-orbit
without copying its visual subject or studio".

## Why this is the interesting one

Read that second example again with this project in mind. It takes **motion and
camera from a video reference while explicitly discarding that video's subject
and setting.**

That is our blockout contract. Exactly. Here is what we have been writing by
hand since nyc:

> `<Video 1>` is a grey untextured 3D blockout of this exact shot. It is the
> sole authority for camera path, timing, framing, and the position and scale of
> every object. Its colours and materials carry no information.

Three sentences of invented English saying `attribute_transfer`. It works — the
nyc runs prove the model understood it — but it is our wording competing with
whatever wording the model was trained to expect, and there is no reason to
prefer ours.

## The claim worth testing

**Our look references may be held too strongly, and the vocabulary is how to
loosen them.**

The current prompt calls the pictures "the sole authority for appearance", which
reads as `fully_preserved` in everything but name. But we do not want them
fully preserved. We want colour, light, material and rendering style — and
emphatically *not* their content.

We have already been billed for the difference. From
[modelling.md](../craft/modelling.md), on generation 006:

> The model did produce water towers in that shot; it put them where its
> references had them, not where the geometry did.

That is a look reference behaving as `fully_preserved` when it should have been
`attribute_transfer`. Three conditions failed at once in that generation and the
reference strength was only one of them — so this is a *hypothesis with a named
mechanism*, not a diagnosis. But it is a cheap one to test, because it costs a
wording change and no code.

## What to write

The mapping this suggests, for any shot in this project:

| Reference | Term | Enumerate |
| --- | --- | --- |
| the blockout | `attribute_transfer` | camera path, timing, framing, position and scale — *without* its colours or materials |
| look pictures | `attribute_transfer` | colour, light, material, rendering style — *without* their subjects, places or objects |
| character pictures | `fully_preserved` | face, hair, build, wardrobe, and any deliberate identity mark |

Two rules fall out of the examples and are worth stating separately, because
both are easy to skip:

**Always enumerate.** The strength term without a list is inert. Every worked
example names the specific attributes.

**Always state the exclusion.** Both examples do — "without copying its visual
subject or studio", "its colours and materials carry no information". The
exclusion is not decoration; in a format with no schema, it is the only thing
distinguishing transfer from preservation.

## Where this gets used first

The [rooftop spot](../../projects/spot/script.md), which puts a character across
two shots and is the first thing here to have a `fully_preserved` subject at
all. It changes two things at once against nyc — the vocabulary and the presence
of a person — so a difference in look-reference behaviour will not be cleanly
attributable. Worth knowing in advance rather than discovering in the verdict.

## Open

- What `partially_preserved` and `weak_reference` actually do. No example found.
- Whether the terms are parsed at all or simply read as ordinary words. Given
  that H3 derives its own intermediate representation, the second is plausible,
  and it would not change the advice: the enumeration and the exclusion carry
  the meaning either way.
- Whether `attribute_transfer` on the look pictures loosens them too far and
  costs us the style that nyc got right.
