# Project → sequence → shot → scene

*Proposed 2026-08-24, implemented 2026-08-25. Kept as the reasoning behind the
layout; `src/ai_render/project.py` is the implementation.*

Before this, everything was flat: `scenes/*.json` in, `out/<scene>/<take>/<generation>/`
out. That was right for one demo room. It stopped being right the moment there was
a second shot, and the cost of changing it grew with every take on disk.

## The hierarchy

```
projects/
  nyc/                              <- project
    project.json                    <- fps, resolution, aspect, defaults
    assets/                         <- work that belongs to no sequence
      water_tower.json
    sequences/
      seq_010/                      <- sequence
        sequence.json
        sh_0010/                    <- shot
          shot.json                 <- duration, generation defaults, selection
          brief.md                  <- the authored intent
          street_a.json             <- scene: one way of staging the shot
          street_b.json             <- scene: another, in parallel
```

Outputs mirror the input path exactly, so any artifact can be read backwards to
the thing that made it:

```
out/nyc/seq_010/sh_0010/street/20260824-153012/20260824-153500_seedance-2-mini_480p/
```

Long, and worth it. A path that encodes project, sequence, shot, scene, take and
generation answers "what is this file" without opening anything.

## Inheritance is the point

Each level sets defaults; the level below overrides only what differs. `fps`,
`resolution` and `aspect_ratio` belong to the project — a sequence that needs a
different frame rate says so in one line, and a shot that does not care stays
silent.

This is how studio pipelines already work, and it is also what keeps diffs
meaningful: **a shot file should contain what makes that shot different, not a
copy of everything true about the project.** A spec that repeats its parents is a
spec where real changes hide among boilerplate.

Resolution order, most specific wins: scene → shot → sequence → project →
built-in defaults.

**`generation` sits at the shot level, and that is not a default — it is where
it belongs.** The prompt, the model and the look references describe the shot
being delivered. The scenes beneath it are parallel variants, competing ways to
stage the same thing, and a comparison between two of them means nothing if they
were generated differently. A scene overrides a generation field only when that
field is the thing the variant exists to test.

## Numbering

Studio convention, and it earns its keep: `seq_010`, `sh_0010`, incrementing by
ten. Inserting a shot between two others is then a naming problem that is already
solved — `sh_0015` — rather than a renumbering that invalidates every path in
`out/` and every reference in a commit message.

Names stay human-readable at the scene level, where insertion order does not
matter: `street.json`, `rooftop.json`.

## A scene is a variant, not a segment

Settled. Several scenes in one shot are **parallel attempts at the same shot**,
or scratch work in service of it. They are siblings. Nothing is joined in time,
nothing is composited, and a shot is never assembled out of its scenes — it is
one of them.

That keeps the shot as the atomic creative unit, which is what it is everywhere
else in production, and it keeps the structure flat: no ordering field, no
transition handling, no rule about what happens where two scenes meet.

Two consequences worth making explicit:

**Selection is a decision, so it gets recorded.** `shot.json` names the scene the
shot currently *is*. Changing that line is a one-line diff with an author and a
date on it — "we went with `street_b`" stops being something remembered in a
comment thread and becomes part of the history. This is the whole thesis applied
to the one decision studios lose most often.

**Not every scene is a candidate.** A scene can also be scratch — a temporary
construction, an asset being built in place — that was never meant to become the
shot. An optional `role` distinguishes them, defaulting to `variant`:

```jsonc
{ "name": "water_tower_test", "role": "asset" }
```

Marking it costs one line and stops a scratch file from silently counting as a
contender.

## Assets, outside the sequence structure

A project also has an `assets/` directory, level with `sequences/`, for work that
belongs to the project but not to any shot: a prop being built, a test scene, a
piece of geometry meant for reuse.

Two reasons it exists from the start. **Not everything needs a sequence** — being
forced to invent `seq_000/sh_0000` to try something out is exactly the kind of
pipeline friction this project is supposed to remove. And **it is where the asset
library goes** when [ideas 2 and 3](ideas.md) happen: ready-made assets and
generated geometry both need somewhere project-scoped to live.

When they do, the reproducibility rule from that note applies here: an asset a
shot depends on must be pinned by hash or version, never by mutable path.
Otherwise a shot stops reproducing from its spec, and the version-control claim
quietly becomes false.

Assets render like anything else, into `out/<project>/assets/<name>/<take>/`.

## What to build now, and what to leave

**Now, because migration hurts later:** the directory shape, the numbering
convention, inheritance, and output paths that mirror inputs.

**Later, when there is a reason:** shot status and task tracking, dependencies
between shots, editorial order and cut assembly, time and cost analysis per shot.
These are the platform ambitions from the README's *Where this goes*, and none of
them is needed to make one shot correctly.

**The demos move.** `demo_cube` and `demo_room` become a `demo` project rather
than a compatibility exception. They are documentation as much as content, and
documentation that shows the old shape would teach the wrong thing on day one.

The cost is real and should be expected: they are referenced in the README, in
`AGENTS.md`, in the test suite and in every example command. That is the migration,
and it is cheaper now — with one published shot and no external users — than at
any later point.
