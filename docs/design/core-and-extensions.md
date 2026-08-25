# The core, and what a project is allowed to add to it

*Decided 2026-08-25. **Not built** — no code implements any of this yet. It is
written down so the next person building it does not have to re-derive the
shape, and so that anything built before it can be judged against it.*

## The problem

Two things are true at once and they pull in opposite directions.

**The core has to stay small.** Every tool in it is a claim that this is how
shots work, and we have made one shot. A core that grows by guessing is a core
full of tools nobody uses, and each one is a thing the next agent has to read
and decide is irrelevant.

**Projects and shots will need their own checks anyway.** A particular shot has
a particular thing that must not go wrong — a clearance that matters, a value
that must stay inside a range, a piece of dressing that must stay in frame — and
it is knowable only in that shot. Waiting for it to be general means it is not
checked at all in the meantime.

So there is a layer missing. Without it there are only two states, and both are
bad: put a hypothesis straight into the core, or have no check at all.

## The shape

The repository already accepted this idea for *data*. `projects/<proj>/assets/`
is a project extending the system without touching the core. This is the same
move for *code*.

**The extension point is checks, not commands.** If a project could add
commands, its `audit` eventually collides with the core's `audit`, and from
there it is a conversation about shadowing and precedence. If a project adds
only checks, the command surface stays the core's and *what gets checked*
becomes the project's. Two projects with a `speed.py` never learn of each
other's existence.

They live along the same path the spec inherits down, so there is one mental
model in the repository and not two:

```
projects/<proj>/checks/*.py
projects/<proj>/sequences/<seq>/checks/*.py
projects/<proj>/sequences/<seq>/<shot>/checks/*.py
```

`check` runs the core validation first, then discovers and runs the local ones,
and reports how many ran and from where. The existence of a local check must
never be a surprise — the first unexplained failure is what stops people running
the command at all.

A check is one file with one function and a docstring that says what it protects:

```python
"""The camera must not thread a gap under 0.6 m between a car and the kerb.

Written after the 2026-08-25 retiming: moving the crest two seconds earlier
slid the path against fixed dressing and drove the camera through three cars.
See notes.md, "Retimed: the crest two seconds earlier".
"""


def check(spec, target, tools):
    for hit in tools.audit.clearances(spec, tools.audit.path(spec)):
        if hit.name.startswith("car_") and hit.distance < 0.6:
            yield f"{hit.name} at {hit.distance:.2f} m, t={hit.t:.2f}"
```

## The contract

**A check may not modify the spec.** Read-only, always. A check that writes
makes the scene depend on whether the check ran, and reproducibility is the
whole point of the repository.

**The dependency is one-way.** The core never imports a local check; it
discovers, executes and collects. Local checks import the core only through a
declared, narrow surface — the merged spec, `interpolate`, and the measuring
half of `audit`. The smaller and more explicitly named that surface, the less
breaks when the core moves.

**Every check carries the incident that produced it.** Same rule as
[modelling.md](../craft/modelling.md): a check with no history is unreadable in
a month, and an unreadable check gets worked around rather than fixed.

**Findings are labelled with their origin.** A failure says which file raised
it, so nobody has to guess whether the core or the shot is unhappy.

## Why the layer exists at all

Not to keep the core clean. **To let the core grow out of practice instead of
out of our predictions.**

A check written for one shot and never written again was correctly not in the
core. The same check appearing in a third shot has earned its way in, and the
move is a promotion, not a redesign. This is the mechanism behind
[method.md](method.md): the layer is where a tool proves itself before it costs
everyone something.

It runs in the other direction too, and that matters more than it sounds.
`audit` today is one fixed report shaped by one shot — a fast camera passing
close to dense static geometry. When a second kind of shot arrives, some of
those measurements will turn out to be local rather than general, and they need
somewhere to move *out* to. A core with no extension layer can only accumulate.

## What to design against

**Stale checks kill the habit.** They pile up, drift out of date, and start
failing for reasons nobody remembers — and then `check` becomes the command
everybody skips. Two things follow: a failure message has to say what to do
about it, and deleting a check that has outlived its shot must be ordinary,
not a negotiation.

**`check` will execute code from the repository.** For your own projects that is
exactly the point. Cloning someone else's project and running `check` is running
their code, and that should be said out loud rather than discovered.

## Open

- **Whether the same point covers more than checks.** Asset generators and
  custom exporters would fit the same discovery. Deliberately not decided:
  checks are the thing we know is needed, and a general plugin system built now
  would be built from guesses.
- **What `tools` actually contains.** The narrow surface has to be enumerated
  before anything can be written against it.
- **Whether shot-level is one directory too many.** Project and sequence may be
  enough in practice; nobody has written a real one yet.
