# Notes — NYC flight

*What building this shot established. [brief.md](brief.md) is what was asked for;
this is what the asking turned into, and what the blockout taught on the way.
Renders referenced here are in [artifacts/](artifacts).*

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

**Two wide weaves, not four quick ones.** Full width, x = +4.5 at t = 1.6 and
x = −4.5 at t = 3.2. A weave the model can follow has to last long enough to be
read as one move; four fast ones would be a texture, not a manoeuvre.

**Cars and poles are set at ±5.4 and ±7.6 m** — inside the weave, outside the
camera. The flight passes close to them and never through them. Proximity is what
sells speed; parallax reads as velocity where an empty corridor at the same speed
reads as a drift.

**The shot settles at the end.** `out` easing on the last location key, the camera
losing speed from t = 9.2 and coming to rest looking out at y = 130. The reveal is
the point of the shot; it needs a moment to land, and a camera still accelerating
through it throws it away.

**Roll is the body.** ±13° through the weaves, −6° at the roof crest, back to 0 by
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
±3.9 m to make that gap honest. Closest approach in the whole shot is now
**0.85 m**, to `car_06` at t = 2.88.

Worth keeping: the clearance is measured along the car's whole 5 m length, not at
the weave peak. The tightest moment is at the far end of the car, where the
camera has already started to come back — placing off the peak alone left 0.51 m
where 0.90 was intended.

**The tail went black.** With 3.4 s to fill, the camera levelled off 6 m above the
deck, which puts the roof 47° below a lens that sees 27° — three of the eight
contact-sheet frames were an empty rectangle. Dropping to deck height overcorrected
into the opposite failure: a 4 m stair hut and a 6 m water tower sitting on the
axis at 6 m range, enormous on a 20 mm lens. It settles now about 5 m above the
deck, aimed 4° down, with the roof objects moved wide and back so they clip the
frame edges and the back parapet lays along the bottom.

## Open

- **Roll sign** unverified, as above.
- **The prompt says "shot on 24mm anamorphic"** while the camera is 20 mm, and
  naming a lens at all is camera vocabulary in a prompt where the camera is
  already geometry. Both worth resolving before anything paid runs.
- **The bay, the bridge and the sunset are not built** — deliberately, as the
  experiment described in the brief. This was cheap to defer when the reveal was
  1.4 s long. At 3.4 s it is a third of the shot pointed at an empty frame: above
  the roof line there is no geometry at all, so there is nothing for the model to
  hold and nothing for a style still to anchor to. Either a distant silhouette
  band gets built, or the shot ends on the roof rather than on the view. Not a
  decision to take quietly.
- **The path audit is a throwaway script.** It found all three car penetrations
  and it does not live in the repository. It should be a command.
- **Nothing generated yet.** No paid call has been made for this shot.
