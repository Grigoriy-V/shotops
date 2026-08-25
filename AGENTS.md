# Working agreements

## Discussion ends when the user says it ends

Do not move from talking about work to doing it until told to. A conclusion that
seems settled, a plan that seems agreed, and an obvious next step are all still
discussion. Silence is not consent, and neither is a good argument.

**Exempt:** documentation, notes and briefs. Writing down what was decided is
part of the conversation, not a jump ahead of it.

**Not exempt:** code, scene specs, refactors, renames — anything that changes how
the thing behaves. Propose it, then wait.

If the discussion has produced something worth keeping, write the note and say
what you would build next. Then stop.

## Never publish without explicit permission

Committing is local and reversible; pushing is publication and is not.

- **`git commit`** — allowed. Commit finished work without being asked, in
  focused commits with a subject that says what changed and why. Never attribute
  the work to yourself, in the message or anywhere else.
- **`git push`**, creating a remote, making a repository public — only when
  asked, and never as a follow-on to a commit. A commit is not a licence to push,
  and "the obvious next step" is not permission.

Say what is committed and what is still only local. The user decides what leaves
the machine.

## Never make a paid API call without explicit permission

Ask first, every time. State what the call is, which model and resolution, and
what it is expected to cost. Then wait for a clear yes. Approval for one run is
not approval for the next one, and "the obvious next step" is not approval
either.

**Paid — always ask:**

| Command | What it spends |
| --- | --- |
| `generate`, `all` | PiAPI video generation. Billed on **input + output** duration, so a 5s blockout under a 5s shot is charged as 10s. |
| `styleframe` | CometAPI image generation (GPT Image 2). |
| `fetch` | Free in itself, but only ever use it to recover a result that is **already** paid for — never as a way to start work. |

**Free — run freely:**

`check`, `audit`, `render`, `views`, `frames`, `sheet`, `extract`, `compare`,
`takes`, `tools/check_env.py`, the test suite. Everything Blender does is local
and costs nothing. Prefer these: most questions about a shot can be answered
from the blockout before any money moves.

Uploading the blockout to Supabase is free but still outward-facing; it only
happens as part of `generate`, which is gated anyway.

## Verify before claiming

Compare like with like — same normalised time, not just "some frame from each".
Use `compare`, which builds one sheet from both clips so there is nothing to
misalign by hand. Comparing frame 5 of a blockout against frame 8 of a result
once produced a confident and completely wrong verdict here.

State what is *not* held alongside what is. Label unconfirmed hypotheses as
hypotheses. When one turns out wrong, say so plainly and move on.

## Secrets

Keys live in `.env`, which is gitignored. Never print a key value, never put one
in a command line, never paste one into chat. `tools/check_env.py` reports which
keys are set without revealing them.

## Where things live

A shot is a directory: `projects/<project>/sequences/<seq>/<shot>/`, holding its
`shot.json`, one or more scene specs, `brief.md` — what was asked for — and
`notes.md` — what building it taught. Work not tied to a sequence goes in
`projects/<project>/assets/`. A scene's identity is its path, never a field
inside it. See [docs/design/pipeline-structure.md](docs/design/pipeline-structure.md).

A project may add its own checks without touching the core — designed, not built:
[docs/design/core-and-extensions.md](docs/design/core-and-extensions.md).

## Every change ships with its check

Mathematical where the change is measurable, visual where it is not, both where
they disagree — and a fix if either fails. Not "I will check it later" and not
"the diff looks right": a change to geometry gets `audit`, a change to framing
gets a render you actually look at.

The tooling exists to make that cheap, never to replace it. And when a check
cannot be expressed with what exists, say so in the commit and in the shot's
`notes.md` rather than letting it pass silently — an unmeasurable risk that
nobody wrote down is the one that reaches a paid generation.

## Nothing that worked may live outside the repository

**A run that only exists in a flag is a run nobody can repeat.** Model, prompt
and `style_references` go in `shot.json`'s `generation` block. Flags are for
probing without editing anything; the moment a configuration is the right one,
it goes in the file. A shot whose best version lives in a chat log is not
source-controlled, whatever the repository says.

**Do not rewrite a prompt that has been run and judged good.** `full_prompt`
sends the scene's text byte for byte with nothing prepended, and that is the
right field for a wording someone tested. Improving it into a near-miss trades a
known result for an unknown one. `prompt` — the look half, with the reference
contract generated — is for looks still being searched for.

## Read before you author

These agreements are process: what you are allowed to do and what you must never
do. **They do not tell you how to build a shot.** Three files do, and the
boundary between them is worth keeping:

| | |
| --- | --- |
| [docs/craft/modelling.md](docs/craft/modelling.md) | How to build geometry a video model can read — units, detail budget, silhouette, colour, assets, clearance, easing. Every rule linked to the experiment that produced it. **Read this before authoring a scene.** |
| [docs/scene-spec.md](docs/scene-spec.md) | The spec format itself, field by field |
| [docs/design/method.md](docs/design/method.md) | How we decide what to build next, and which tools are still n = 1 |

When something costs you a lesson, write it into `modelling.md` **with a link to
the evidence** — a rule with no incident behind it is an opinion, and opinions in
a rules file are how a rules file stops being read.

Findings about the *video model* — what it holds, where it drifts, what a
blockout has to supply — go in [docs/research/craft.md](docs/research/craft.md).
What a particular shot taught goes in that shot's `notes.md`, next to the spec
that proved it. What a paid run did goes in its `generations.md`.

## Keep the working record in the shot

Every view, sheet, sketch or debug render that gets made -- including anything
shown in chat -- is written into the shot. Chat is not storage: an image that
only exists in a conversation is lost to the next session and to anyone else.

- `<shot>/preview/` — the blockout video, and nothing else. It is the
  deliverable, and it should not have to be hunted for.
- `<shot>/frames/` — individual stills, named by position through the shot. Not
  evidence: these are the input a style frame gets generated from.
- `<shot>/artifacts/` — sheets, views, debug renders. The evidence.

Names are `<sequence>_<shot>_<scene>_<id>_<kind>_v###`. The id is
`project.scene_id(spec)` — six hex of the spec's content, so everything made from
one state of the scene carries the same one. The version counts only its own
kind, so "the fourth sheet" means the fourth sheet.

Never hand-name a file: `target.name(kind, sid, target.next_version(kind))` picks
it. Hash the spec that actually produced the file — for `sheet`, that is the
take's own `scene.json`, not the scene file as it stands now.

`frames` is the one that costs real space — five PNGs is about 1.6 MB, and every
version of it stays in history. Run it when heading for a generation, not after
every render. `views` and `sheet` are cheap; use those to iterate.

This is a deliberate exception to "outputs are derived, so `out/` is gitignored".
These are not outputs, they are the record of how a decision was reached: the
frame that showed the wall was empty, the sheet that proved the camera held. Keep
them small (downscaled JPEG, short video) and let them be committed.

`out/` still holds the real renders and generations, still disposable, still
reproducible from the spec.
