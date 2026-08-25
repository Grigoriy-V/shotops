# Notes — NYC flight

*What building this shot established. [brief.md](brief.md) is what was asked for;
this is what the asking turned into, and what the blockout taught on the way.
The blockout is in [preview/](preview); the sheets and views behind these notes
are in [artifacts/](artifacts).*

## The numbers the scene is built on

Metric, Z-up, everything at real size, so the motion has a speed rather than a
feeling of one.

| | |
| --- | --- |
| Road | 14 m wide, 130 m long, plane at z = 0 |
| Sidewalks | 3 m, raised 0.3 m |
| Side blocks | 18 × 22 m footprint, 24–34 m tall, five a side |
| End building | 44 m wide, 12 m deep, 30 m tall, face at y = 0 |
| Cars | 1.9 × 4.6 × 1.5 m |
| Lamp posts | 9 m, at x = ±7.6 |
| Lens | 20 mm on a 36 mm sensor |

Those give the shot its speed for free: the camera covers 112 m of street in the
first 5 s — 22 m/s, about 80 km/h — then climbs 30 m in the next 3.6 s. Neither
number was chosen; both fell out of the geometry.

## Staging, and why each piece is there

**The street is a dead end.** The end building sits square across it at y = 0, 44
m wide against a 14 m road, so it fills frame long before the camera arrives. The
turn upward then needs no motivation — the wall is the only thing left.

**Two wide weaves, not four quick ones.** Full width, x = +3.9 at t = 1.5 and
x = −3.9 at t = 3.0. A weave the model can follow has to last long enough to be
read as one move; four fast ones would be a texture, not a manoeuvre.

**Cars at the kerbs at ±5.9 m, poles at ±7.6 m,** and two cars standing out in
the road at the weave peaks. The flight passes close to them and never through
them. Proximity is what sells speed; parallax reads as velocity where an empty
corridor at the same speed reads as a drift.

**The shot settles at the end.** `out` easing on the last location key, the camera
losing speed from t = 9.2 and coming to rest looking out at y = 130. The reveal is
the point of the shot; it needs a moment to land, and a camera still accelerating
through it throws it away.

**Roll is the body.** ±13° through the weaves, −5° at the roof crest, back to 0 by
the end. Without it the weave reads as sliding rather than banking. This is why
the spec grew `roll`/`pan`/`tilt` at all — see
[camera-orientation.md](../../../../../docs/design/camera-orientation.md). The
sign convention was picked, not derived; whether −13 into a right-hand weave is
the right way round is still open.

## What the first render changed

The camera was authored first and rendered before any dressing, which is the only
reason these were caught cheaply. Both were predicted, and both were worse than
predicted.

**The wall was a blank grey rectangle** for two full seconds of climb — the
single largest stretch of frame in the shot, with nothing in it to track. Fixed
with rhythm rather than detail: eight ledges up the face at 4 m intervals and
three vertical piers, all in primitives. A featureless plane filling frame is
where a video model has nothing to hold onto and starts inventing.

**Cresting the roof revealed a void.** Nothing above the parapet but background,
so the climb arrived nowhere. The roof got a parapet front and back, a water tower
with legs, two AC units and a stair hut — enough for the crest to deliver
something, and enough for the horizon to sit behind objects rather than behind
nothing.

**Values are separated deliberately:** road 0.30, sidewalks 0.45, blocks
0.55–0.62, facade 0.50 with ledges at 0.66 and piers at 0.40, parapet 0.68. A
scene at one flat grey gives the model almost nothing; the value steps are what
survive into the result as separate surfaces.

## The camera was jerky, and why

*2026-08-25.* The first cut of the move stopped dead at every keyframe — arrive,
halt, set off again — right through what was supposed to be one continuous
flight. It was not the key values. It was the interpolation.

`ease` is a smoothstep across one segment, and smoothstep has **zero velocity at
both ends**. One eased segment reads as a nice move; a chain of them is a stop at
every key. The `linear` segments in between had the opposite fault — constant
speed inside the segment, and an instant change of direction at the key, which on
a position track makes the path a polyline with corners rather than a curve.

Fixed by adding a fifth mode, `smooth`: cubic Hermite with Catmull-Rom tangents,
which takes its tangent at a key from the keys either side, so the tangent
leaving a key equals the tangent entering it. Velocity is continuous through the
key and the path curves through it. Every camera track here is now `smooth`.

Speed after the change, per second: 22, 22, 24, 26, 26, 18, 15, 6, 3, 1, 1 m/s.
No stall anywhere in the run.

## Retimed: the crest two seconds earlier

The roof crest moved from t = 8.6 to **t = 6.6**, which turns 1.4 s on the view
into 3.4 s. The street run is untouched; the time came out of the climb, which
was doing 30 km/h up a wall — slower than the street below it, and the least
interesting part of the shot to spend time on. It now covers 28 m in about 1.9 s.

Two things broke as a consequence, both caught before they shipped:

**The camera went through three cars.** Retiming slides the path against fixed
dressing, so a clearance that held before did not hold after. The cars were
re-placed against the baked path rather than by eye: six parked along the kerbs,
and two standing out in the road at exactly the two weave peaks, so at each peak
the camera threads the gap between a stopped car and a parked one — at the moment
it is moving fastest and banked hardest. Weave amplitude came in from ±4.6 to
±3.9 m to make that gap honest. Closest approach in the whole shot is under a
metre, to `car_06` at t = 2.88 — `audit` measures it exactly.

Worth keeping: the clearance has to be measured along the car's whole 5 m length,
not at the weave peak. The tightest moment is at the far end of the car, where
the camera has already started to come back — placing against the peak alone left
barely half the gap intended. This is why `audit` walks every frame against every
object's bounds rather than checking the moment that looks tightest.

*The numbers in this section came from a throwaway script, since replaced by
`audit`, which measures this spec at 0.89 m to `car_03` and 0.92 m to `car_06`.
Where the two disagree, the command is the authority.*

**The tail went black.** With 3.4 s to fill, the camera levelled off 6 m above the
deck, which puts the roof 47° below a lens that sees 27° — three of the eight
contact-sheet frames were an empty rectangle. Dropping to deck height overcorrected
into the opposite failure: a 4 m stair hut and a 6 m water tower sitting on the
axis at 6 m range, enormous on a 20 mm lens. It settles now about 5 m above the
deck, aimed 4° down, with the roof objects moved wide and back so they clip the
frame edges and the back parapet lays along the bottom.

## What the first generation confirmed

Full account in [generations.md](generations.md). Two things from it belong here,
because they are about how the scene is built rather than about one run:

**The rooftop backdrop does not need building.** The prompt supplied the bay, the
bridge, the sunset and a distant skyline — none of which exist in the geometry —
and held them for the whole reveal. The experiment the brief set up is answered.

**A primitive only has to look like its object at the distance it is seen from.**
The two mid-road cars came back as raw white boxes. The same cubes read as cars
at twenty metres, in a row along the kerb, where context supplies the answer; at
0.89 m, filling a third of frame, there is no context left and no wheels, cabin
or glass in the silhouette to infer from. Everything that survived close range —
wall, kerb, parapet, poles — is a thing whose primitive shape is its real shape.

The dressing was placed under a metre away on purpose, to sell the speed. That
decision is still right; what was wrong was assuming a box could take it.

## The cars got a silhouette and a colour

*2026-08-25, in answer to generation 001.* Each car was one cube. Each is now
eight primitives: a lower body, a greenhouse set back from centre, a raked
windscreen, a steeper rear screen, and four wheels laid on their sides. The body
is red — chosen so the prompt could name it, though by 003 the prompt no longer
needed to; see the marker note under Open — with dark glass and near-black
tyres, so a car carries three values and a hue where it used to carry one.

**The footprint did not change.** Every part is a fraction of the car's own
width, length and height, and nothing is allowed outside the original box: the
wheels sit flush with the body sides rather than proud of them. That was the
constraint, because the whole point of these two cars is that the camera passes
them at under a metre, and a silhouette bought at the cost of the clearance
would be a bad trade. `audit` says the tightest approach is now **0.95 m** to
`car_03_body` at t = 1.62 and the same to `car_06_body` at t = 2.88 — marginally
wider than before, because the lower body no longer reaches roof height.

**The rake is the part that did the work.** A body box under a roof box is two
stacked slabs, and at a metre that is the shape of a flatbed. The slope from
bonnet to roof is the thing a car has in profile that nothing else on this
street has. Narrowing the greenhouse to 0.76 of the body width did the rest: it
gives the car shoulders, so red reads down both sides of the dark glass.

Everything above is generated from a footprint rather than typed, which is worth
saying because it is the reason a van and a saloon come out at their own
proportions from one rule.

## Open

- ~~Roll sign unverified~~ — **settled.** The bank reads correctly in the
  preview, into the turn in both weaves and at the roof crest. No change needed.
- ~~The prompt says "shot on 24mm anamorphic"~~ — **corrected, not removed.**
  It was taken out as camera vocabulary in a shot where the camera is geometry;
  it came back by hand as `20mm anamorphic` in generations 002 and 003, and that
  is the config that produced the good take, so it is in the spec. It is at
  least no longer contradicting the render.
- ~~The bay, the bridge and the sunset are not built~~ — **settled by generation
  001.** The prompt supplied all of it and held it for the full reveal. No
  silhouette band needs building.
- ~~The path audit is a throwaway script~~ — **it is `audit` now.** Free, no
  Blender, and it fails the command when the camera is inside something.
- ~~Audio comes back enabled~~ — **accepted.** It arrives from a server hint,
  costs nothing extra, and is not worth a switch until something needs it off.
- ~~The car is a recipe, and the spec holds the baked result~~ — **fixed.** The
  rule lives in [`assets/sedan.json`](../../../assets/sedan.json), declared in
  the unit space of the car's own bounding box, and the scene places eight
  instances. Sixty-four objects became eight lines; the windscreen rake is one
  number in one file. Verified rather than assumed: the expanded geometry
  matches the old bake to within 0.5 mm on the six identical cars and 15 mm on
  the three odd-sized ones, and `audit` returns the same clearances to the
  centimetre — 0.95 m to `car_03_body` at t = 1.62, 0.95 m to `car_06_body` at
  t = 2.88. The only line that changed is a wheel's *name*, because a 180°
  instance yaw renumbers them.
- **A non-uniform footprint skews a rotated part — answered, not yet adopted.**
  `assets/sedan.json` stores one windscreen rake, 34.8°, taken from the
  1.9 × 4.6 m car, so the 5.6 m instance is 0.4° out and a short tall one would
  be 12° out. `assets/sedan_solid.json` builds the greenhouse as a single
  deformed block instead of a roof box plus two panes: six parts instead of
  eight, and the rake is derived from the footprint — 34.8° on the saloon,
  34.4° on the estate, 46.9° on a 3.8 × 1.9 m stub. Compared side by side in
  [`assets/artifacts/assets_car_compare_0190ac_sheet_v001.jpg`](../../../assets/artifacts/assets_car_compare_0190ac_sheet_v001.jpg).
  **The shot still uses the boxed asset.** Switching it changes the geometry the
  camera passes at 0.95 m, so it wants its own `audit` and its own decision.
- ~~The two mid-road cars are still unproven~~ — **proven.** Generations 002 and
  003 both bring them back as cars at the 0.95 m pass, with wheels, glass, tail
  lights and plates. The 001 failure does not recur.
- **The red is a marker, not a paint order.** 003 came back with a yellow taxi
  and a dark saloon where the spec says `[0.75, 0.08, 0.06]`. The colour does
  its job — it makes each car one object the prompt can point at — and then the
  look reference decides what that object is actually painted. 002, which did
  *not* tell the model to take appearance from the references, kept the red and
  flattened the whole frame into one warm band. Worth knowing before anyone
  treats a `color` field as art direction.
- **What to colour next is now a real question.** If colour is an attachment
  point rather than a look, then the useful rule is one hue per *class* of
  thing, distinct from its neighbours — not a hue chosen because it is what the
  object would be. Nothing in the spec or in `check` says this yet.
