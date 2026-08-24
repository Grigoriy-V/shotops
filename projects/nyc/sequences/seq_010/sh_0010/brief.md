# Brief — NYC flight

*Written 2026-08-24. The authored intent for the shot, kept beside the spec it
will produce. When the spec and this file disagree, this file is what was
actually asked for.*

## Original brief, verbatim

> шот около 10 сек, 1 пролётка, без склеек. Дух фильм про человека паука.
> камера пролетает сквозь машины, столбы, виляет влево-вправо, летит по дороги,
> упирается в дом, летит вверх вдоль стены, влетает на крышу, впереди видим
> закат, залив, мост. Локация реф - ньюйорк.
> Для начала можно попробовать, не строить мост и залив в конце - добиться этого
> промптами и стилами

## Working translation

A single continuous ~10s shot. No cuts. One flight.

The camera moves at speed down a city street: through and past cars, past lamp
posts, weaving left and right, low over the road. It meets a building face-on,
turns upward, climbs the wall, crests the roof edge — and ahead, sunset, the bay,
a bridge.

Reference location: New York. Reference feeling: the flight language of a
Spider-Man film — speed, proximity, vertical release.

## Decisions taken while briefing

**No subject in frame.** Pure camera. The flight is the content, so everything
visible in the result is attributable to camera and environment — nothing is
explained away by "the model rendered the figure badly".

**The camera never passes through anything.** It flies *past* cars and poles —
close, but clear. Proximity is the point; penetration is a mistake. This also
keeps the planned "camera path does not intersect geometry" check meaningful
here rather than needing an exemption list.

**Staging, settled.**

- **Two wide weaves** on the street run, not four quick ones — full-width, so
  each one is legible and the model has a chance of holding it.
- **A dead end.** The street runs into the building face square on, so the wall
  is unmistakable and the reason to go vertical needs no explaining.
- **The shot settles.** After cresting the roof edge the camera sheds speed and
  comes to rest on the view. The reveal is the point of the shot and it needs
  time to land.
- **The camera banks.** Roll is required, which the spec did not support when this
  was written — see
  [camera-orientation.md](../../../../../docs/design/camera-orientation.md) for
  the shape it took, which also covers aiming off-centre for future shots.

**Style-frame plan, for later.** Not this stage's problem, but the sequence of
tests is decided:

1. one style still at the head of the shot, plus prompt
2. one at the head and one at the tail, plus prompt
3. N stills at intervals through the shot, plus prompt

This shot changes environment completely from street to open sky, which makes it
the right place to find out how far a single still reaches.

## Scope for the first attempt

**Built in the blockout:** the street, the cars, the poles, the building face,
the roof.

**Not built:** the bay, the bridge, the sunset. Those are to be carried by the
prompt and the style still. This is deliberate — it is the experiment, not an
economy. If the model can furnish a horizon the blockout does not contain, that
is a significant finding about how far the geometry has to go. If it cannot,
that is equally worth knowing, and the fix is known (build a horizon line).

## What this shot is being made to find out

This is the first presentable shot, and the first stage of the project proper.
Its purpose is to produce information for the work that follows:

- does structure hold over **10 seconds**, when everything verified so far was 5
- does it hold under **fast camera motion** with close foreground occluders,
  where the previous test was a slow dolly in an empty room
- does a **single style still** govern the look of a shot whose environment
  changes completely from beginning to end — street, then wall, then open sky
- can the prompt **extend the world** past the edge of the geometry

Four questions at once. Attribution of failure is the main risk, and the plan
should be shaped so that a bad result still says which of the four broke.

## Constraints carried from earlier work

- Camera vocabulary stays out of the prompt. The camera is geometry here; the
  prompt describes surfaces, light and atmosphere. See
  [craft.md](../../../../../docs/research/craft.md).
- The style still must be derived from a blockout frame, not from text, or the
  two references disagree about composition.
- Generation is billed input + output, so a 10s shot against a 10s blockout is
  charged as 20s. Iterate on `seedance-2-mini` at `480p`.
- Nothing paid runs without explicit approval. See
  [AGENTS.md](../../../../../AGENTS.md).

What building the shot then established — dimensions, staging reasons, what the
first render changed — is in [notes.md](notes.md).
