# How this gets built

*Written 2026-08-25, two days in. This is the rule for deciding what to build
next, and it exists because the obvious alternative — design the pipeline, then
fill it in — is the one that fails quietly.*

## Examples first, tools second

**We build a real shot, watch what it costs, and extract the tool from that.**
Not: imagine what a pipeline needs and implement it. Neither of us knows yet
what this needs, and a tool built from a hypothesis is indistinguishable from a
correct one until something uses it.

Everything in the repository that has earned its place arrived this way. The
`smooth` easing mode exists because a flight stopped dead at every keyframe.
`audit` exists because a retiming drove the camera through three cars. Assets
and instances exist because sixty-four baked objects made a one-line change into
sixty-four edits. The `mesh` part exists because a stored rake angle is only
right at one footprint.

None of those were on a roadmap. All of them were obvious the moment the shot
demanded them.

## n = 1, and say so

**One shot has been built.** Every rule and every tool here is shaped by it: a
single continuous ten-second camera flying fast down a dense static street. That
is one point in a large space, and nothing yet distinguishes what is general from
what merely worked once.

The honest inventory today:

| General — will survive the next shot | n = 1 — shaped by this one |
| --- | --- |
| Hierarchy, inheritance, artifact naming, takes | `audit` in its entirety |
| `check`, the spec format, validation | Clearance as *closest approach along a path* |
| Interpolation and the easing modes | Stalls and the speed profile |
| Assets and instances, unit-space authoring | Which measurements are worth printing |
| `style_references`, `full_prompt`, the provider layer | |
| `views`, `frames`, `sheet`, `compare` | |

The right-hand column is not a criticism. Clearance-along-a-path is exactly what
a fast flythrough needs and says nothing at all about a locked-off two-shot.
Marking it as n = 1 is what stops it being mistaken for the shape of the system.

**This table is meant to be edited.** When something moves from right to left, it
moved because a second shot used it, and that is the whole signal.

## Where a tool waits before it is a tool

A hypothesis does not go in the core. It goes in the project or the shot as a
local check, and it is promoted when a third shot writes it again. The mechanism
is [core-and-extensions.md](core-and-extensions.md); the reason it exists is this
page.

## What we are deliberately not building

**A shot-diff tool.** The idea was a command that reads two specs and reports
the difference in shot terms rather than in lines. It does not survive contact:
an agent reads a diff perfectly well, `git revert` already reverts, and every
version's preview and contact sheet is committed, so a human can look. What is
left is not tooling — it is the convention that a change to geometry ships with
its numbers in the commit message and in the shot's `notes.md`.

The residue that *is* real: the diff tells you what changed, not what it did.
Moving one keyframe half a second is two lines and once drove the camera through
three cars. But that is a measurement gap, not a diff gap, and it is filled by
`audit` and by the rule below — not by a new command.

**The frustum half of the feedback loop.** Whether the subject is in frame, what
fraction of frame height it fills, which side it sits on. Three of this shot's
four failures were framing, so the temptation is strong. It is being held back
on purpose: designed from memory of a shot that *lacked* a subject, it would
come out as a check about empty walls. **A shot that needs it should pull it into
existence.** See [feedback-loop.md](feedback-loop.md).

**A general plugin system.** Checks are the extension we know is needed. Asset
generators and exporters would fit the same discovery, and that is a reason to
keep the design compatible, not a reason to build it.

## The rule that replaces all of the above

**Every change ships with its check.** Mathematical where the change is
measurable, visual where it is not, both where they disagree, and a fix if
either fails. A tool exists to make that cheap. It does not exist to replace it,
and no amount of tooling makes an unchecked change safe.

This is why the missing measurement matters more than the missing command: a
check you cannot express is a check that does not happen, whoever is diligent.
