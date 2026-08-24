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

`check`, `render`, `views`, `sheet`, `extract`, `compare`, `takes`,
`tools/check_env.py`, the test suite. Everything Blender does is local and costs
nothing. Prefer these: most questions about a shot can be answered from the
blockout before any money moves.

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

## Scene authoring

The scene spec is the deliverable; Blender and the video model are consumers of
it. Prefer editing a field over regenerating a scene.

**Work in real units.** Metric, Z-up, objects at their true size. Speed, lens and
framing then follow from the numbers instead of being guessed. Scale errors are
invisible in a grey blockout and obvious in the result.

**Author the camera first, then dress the scene.** The move is the shot; the
geometry exists to make the move legible. Render once the camera exists and
before the dressing, because that render is what tells you what the dressing is
for.

**Never let the camera pass through geometry.** Close is the point; penetration
is a mistake. Retiming a move slides it against fixed dressing, so a path that
was clear before a timing change is not clear after one — measure the baked
path, do not assume.

**A continuous move uses `smooth` easing.** The other modes shape one segment at
a time and stop at every key; a flight authored with `ease` arrives, halts and
sets off again at each one. Read the values you are writing as a curve, not as a
list of positions.

**Look before believing.** A spec you have not rendered is a guess. `views` is
cheap and answers the question a frame cannot — where everything is, and where
the camera actually goes.

Craft findings — what a video model holds, where it drifts, what a blockout has
to supply — are not rules and do not belong here. Survey material goes in
[docs/research/craft.md](docs/research/craft.md); what a particular shot taught
goes in that shot's `notes.md`, next to the spec that proved it.

## Keep the working record in the shot

Every view, sheet, sketch or debug render that gets made -- including anything
shown in chat -- is written to `<shot>/artifacts/`. Chat is not storage: an image
that only exists in a conversation is lost to the next session and to anyone
else.

This is a deliberate exception to "outputs are derived, so `out/` is gitignored".
These are not outputs, they are the record of how a decision was reached: the
frame that showed the wall was empty, the sheet that proved the camera held. Keep
them small (downscaled JPEG/PNG), name them with a stamp, and let them be
committed.

`out/` still holds the real renders and generations, still disposable, still
reproducible from the spec.
