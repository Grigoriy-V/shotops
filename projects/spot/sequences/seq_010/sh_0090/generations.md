# Generations — sh_0090, the whole spot in one pass

## Open after this test

The test is closed. What it left open, in the order it would be worth picking up:

**One `base` run on the same cut.** It is the whole of the remaining question
about the camera: if `base` holds the angles, an edit is fine as a reference and
the cost is only steps; if it loses them too, the reference is the problem and
per-shot generation is the answer. Nothing blocks it — a `base` run names no
accelerator and builds a clean graph.

**No seat in the pipeline for a sequence.** `generate --reference` works, but the
run still hangs off a holder take whose blockout is never uploaded, so the
manifest names a scene that had no part in the result.

**Nothing catches the frame-grid drift.** 4.9% here. No warning at generate time,
no retime at publish time, and every comparison has to be built by hand at
matched fractions.

**No way to check an angle except by eye.** The compare stack was assembled
manually. "Shot 2 improved" in entry 002 rests on absence of complaint, not on a
measurement against the blockout.

**Nothing warns that a small primitive will not read.** The opening close-up came
back as an arm and a lens flare. The rule is written in
[modelling.md](../../../../docs/craft/modelling.md) and lives only there.

**`audit.clearances` is wrong for parented parts.** It reads `obj["location"]`
without consulting `parent`, so an animated instance's parts report local
coordinates as world — plausible distances, silently wrong. It arrived with the
empty-parent model built for this project.

**Look is carried by words alone.** The one picture owns the character and
nothing else; "it looks cheap" had only the text to fix it. A separate look
reference was never tried.

## 002 — the same run with the prompt rewritten

`seq_010_sh_0090_cut_a_ab0fdd_render_v002.mp4` · task `468c290e1a544aba985b929a834b4909`

**One variable moved.** Same reference, same picture, same `turbo_8` +
`fl2v_turbo_8`, same seed 1001, same 277 frames / 11.542 s. Only the prompt
changed, from v001 to v002.

Prompt v002 was rebuilt on the nyc skeleton after v001 was judged to read
backwards — it had declared the blockout the sole authority for framing and then
spent its whole description on framing, leaving the look one sentence. v002
restores what nyc had: `summary` as an instruction rather than a logline,
`From <Video 1>:` naming speed, lens and shot scale, an explicit **Invented**
line listing what the geometry cannot supply, camera described in every beat,
and the sun's direction relative to the camera stated per shot.

### The verdict

**Better.** But **shot 4's angle is still broken**, and **shot 3 is still
cringe**.

Test closed here for now.

### What the two runs together establish

**The prompt was not the cause of the lost camera.** Shot 4 lost its angle under
both prompts with everything else held fixed, so the rewrite cannot be credited
or blamed for it. That eliminates the cheapest explanation and leaves the two
recorded under 001: the reference is an *edit* rather than a single take, and
the profile is the third-ranked one. Neither has been separated yet.

**Shot 2 was named as broken in 001 and was not named in 002.** Read as the
prompt buying back one of the two lost angles — but that is a viewer's read of
two clips, not a measurement, and it rests on absence of complaint rather than
on a check against the blockout.

**Direction of performance did not take.** Shot 3 carried the beat written
explicitly and with timings — eyes squeezed shut against the glare, opening to a
squint, gaze off-lens — and it still came back wrong. Writing a performance beat
more precisely is not, on this evidence, what fixes a performance beat.

**The look did move.** That is the one thing the rewrite clearly bought, and it
is consistent with where the words went: v002 spends its budget on light, lens
and grade, and the grade is what improved.

### Artefacts

`cut/seq_010_compare_v002.mp4` stacks the blockout, 001 and 002 on one time base
— which is the only fair way to judge an angle, since a camera judged from
memory across two playbacks flatters whichever was watched second.

## 001 — `turbo_8` crossed, one generation for four shots

`seq_010_sh_0090_cut_a_ab0fdd_render_v001.mp4` · task `2bfd35e307e648e698d27649e2066b12`

| | |
| --- | --- |
| Reference | `cut/seq_010_cut_v002.mp4` — four blockout shots joined end to end |
| Pictures | one: `refs/subject_01.png`, the character sheet |
| Profile | `turbo_8`, accelerator `fl2v_turbo_8` crossed onto `ref2va` |
| Steps / seed | 8 / 1001 |
| Canvas | 1344×768, 768p |
| Wall clock | 11 m 54 s, about $0.60 |
| Returned | 277 frames, 11.542 s against 11.000 requested |

### The verdict

**Bad. It looks cheap — there is no sense of an expensive commercial anywhere in
it.** The lighting and the overall look are the worst of it.

**Shot 2 changed camera angle completely**, and the beat was lost with it: she
was to be reaching for the door *while looking at the sun*, and neither the
angle nor the look survived.

**Shot 4 broke its angle too.**

**Shot 2b is very weak.** Her face was to be lit by the sun and it came back in
shadow. She looks into the lens, which she was never meant to do. And she simply
smiles, where the whole point was the ad-picture beat: eyes narrowed or shut
against the low sun.

### What this actually means

The finding is not about the prompt. **Two of the four shots did not hold their
camera, and camera is the one thing this pipeline exists to guarantee.** A
result that keeps the cuts, the character and the location while losing the
framing has failed at the only claim that distinguishes it from typing a prompt
into any text-to-video model.

*This entry corrects the first read of the run, which reported the cuts landing
and the character carrying across shots 2 and 3 as the headline and did not
check the angles against the blockout at all. Those two things are true and they
are not the point.*

### Two hypotheses, both cheap to separate

**The reference is an edit, and H3 may not take edits.** `<Video 1>` is encoded
into a `minimax_refs` block re-injected at every step and never bound frame to
frame — established in the nyc work. A single continuous take gives the model
one camera to lock onto. Four cuts ask it to infer four separate setups from one
clip, and the conditioning is weakest exactly where the content jumps. If this
is the cause, the fix is not a better prompt but generating shot by shot and
cutting afterwards, which is what we were doing before this run.

**The profile was the third-ranked one.** `fl2v_turbo_8` crossed onto `ref2va`
at 8 steps sat third on the H3 ranking, behind `base` and `spectrum`, and
structure adherence was already the thing it gave up. This run is not evidence
about what `base` would do with the same reference.

**They separate for one run each**, and in this order: the same cut on `base`
first, because if `base` holds the angles then the edit is fine as a reference
and the cost is only steps. If `base` loses them too, the reference is the
problem and per-shot generation is the answer.

### The opening close-up did not read

Three frames of her at 1.2 m came back as an arm, a torso and a lens flare
rather than the shot that was blocked. This is
[modelling.md's rule](../../../../docs/craft/modelling.md) landing again: a
primitive under a metre comes back as something else. It was flagged before the
run; now there is evidence on this shot.

### Timing drift, measured

The frame grid moved the cuts by **4.9%**, not the ~1% predicted before the run:
277 frames over 11.542 s against 11.000 asked for. The cuts therefore land near
3.15 / 5.77 / 8.39 rather than 3.00 / 5.50 / 8.00. Any comparison against the
blockout has to be made at matched *fractions*, never at matched seconds.
