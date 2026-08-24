# Working agreements

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

`check`, `render`, `extract`, `compare`, `takes`, `tools/check_env.py`, the test
suite. Everything Blender does is local and costs nothing. Prefer these: most
questions about a shot can be answered from the blockout before any money moves.

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

## Scene authoring

`scenes/*.json` is the deliverable; Blender and the video model are consumers of
it. Prefer editing a field over regenerating a scene.
