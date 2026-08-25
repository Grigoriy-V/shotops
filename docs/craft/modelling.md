# Building geometry for a blockout

*What we have learned about modelling for this pipeline, and the experiment
behind each rule.*

This is not a modelling tutorial and not a survey. It is the set of rules that
have earned their place here by costing something — a wasted generation, a
rebuilt asset, a wrong measurement — written so the next person, or the next
agent, does not pay for them again.

**A rule gets added here when an experiment produced it, and the entry links to
that experiment.** A rule with no evidence behind it is an opinion, and opinions
in a rules file are how a rules file stops being read. Where the evidence is a
shot, it links to that shot's `notes.md`; where it is a paid run, to its
`generations.md` entry.

Three other files hold the neighbouring things, and the boundary is worth
keeping: [`AGENTS.md`](../../AGENTS.md) is the short list of working agreements;
[`docs/research/craft.md`](../research/craft.md) is what the *video model* does
with what we give it; a shot's `notes.md` is what building that particular shot
taught. This file is about the geometry itself.

**Everything below came from one shot** — a ten-second continuous camera flying
fast down a dense static street. That is one point in a large space. The rules
are not wrong, but none of them has been tested against a second kind of shot,
and some will turn out to be about *that* shot rather than about blockouts. See
[method.md](../design/method.md) for which parts of the system are already
general and which are still n = 1.

## Before anything else

**The scene spec is the deliverable.** Blender and the video model are consumers
of it. Prefer editing a field to regenerating a scene: a spec that gets rebuilt
every time it is wrong has no history worth reading.

**Look before believing.** A spec you have not rendered is a guess. `views` is
cheap and answers the question a single frame cannot — where everything actually
is, and where the camera actually goes.

---

## Scale and units

**Work in metric, Z-up, at true size.** Speed, lens and framing then follow from
the numbers instead of being guessed at. A 20 mm lens covering 112 m of street
in 5 s *is* 80 km/h, and nobody had to decide that it felt fast enough.

Scale errors are invisible in a grey blockout and obvious in the result: the
video model knows what a street looks like and will render your 7 m car as a
7 m car.

## How much detail, and where

**A primitive only has to look like its object at the distance it is seen
from.** Distance buys inference — a box in a row along a kerb reads as a parked
car because the street around it says so. Proximity spends it: the same box at
under a metre, filling a third of frame, came back from the model as a box.

*Evidence: [generation 001](../../projects/nyc/sequences/seq_010/sh_0010/generations.md),
where two cars at 0.89 m returned as untextured white boxes while everything
around them rendered.*

**So detail exactly what the camera goes close to, and nothing else.** The same
shot has fifty buildings that are single scaled cubes, and they are fine,
because nothing gets within twenty metres of them.

**Three things decide whether a close object survives, and all three have to
hold.** A clear instruction naming it in the prompt; blocking specific enough
that its silhouette says what it is; and a look reference that actually contains
that object. Miss any one and the result is not wrong so much as *unpredictable* —
the model fills the gap with something plausible, and plausible is not the same
as yours.

*Evidence: [generation 006](../../projects/nyc/sequences/seq_010/sh_0010/generations.md),
where the rooftop water tank — a bare cylinder filling a third of frame in the
last seconds — came back as a brick building with windows. All three conditions
failed at once: the prompt never mentions a water tank, a cylinder is the
silhouette of a great many things, and the three look references are of other
places. The model did produce water towers in that shot; it put them where its
references had them, not where the geometry did.*

The reason this is worth stating as its own rule rather than folding into the
one above: **distance was not the problem here.** The tank was the closest thing
in frame. What it lacked was any of the three sources that say what a shape is.

**A featureless plane filling frame is where the model starts inventing.** Two
seconds of blank wall during a climb came back as guesswork; eight ledges and
three piers at 4 m intervals — still nothing but scaled cubes — came back as
window rows and read as a climb.

*Evidence: [nyc/sh_0010 notes](../../projects/nyc/sequences/seq_010/sh_0010/notes.md),
"What the first render changed".*

## Silhouette

**The silhouette is what a video model reads, so build the profile, not the
parts.** A body box under a roof box is two stacked slabs, which at a metre is
the shape of a flatbed. The slope from bonnet to roof is the thing a car has in
profile that nothing else on a street has, and adding it is what turned the
boxes into cars.

**Overlapping panels read as scaffolding.** Three boxes making a cabin — a roof
panel with a raked pane at each end — leave the panes protruding past the roof
at the sides and a visible gap at the belt line. One closed solid does not.

*Evidence: [`assets/car_compare.json`](../../projects/nyc/assets/car_compare.json)
and its
[grid](../../projects/nyc/assets/artifacts/assets_car_compare_0190ac_sheet_v001.jpg) —
the same car built both ways at three footprints.*

**Give a form its shoulders.** Narrowing the greenhouse to 0.76 of the body
width, and tapering it in plan from 0.80 at the belt to 0.72 at the roof, is
what puts body colour down both sides of the glass. Without it a cabin is a lid.

## Colour and value

**Separate objects by value, deliberately.** Road 0.30, kerbs 0.45, blocks
0.55–0.62, facade 0.50 with ledges at 0.66. A scene at one flat grey gives the
model almost nothing; the value steps survive into the result as separate
surfaces.

**Colour in a blockout is a marker, not a specification.** It says *there is one
object here and this is where it ends*, so a prompt has something to point at.
What the object is finally painted comes from the look reference. Cars authored
red came back as a yellow taxi and a dark saloon — and the run that did *not*
release the model from the marker painted the whole frame in that hue.

*Evidence: [generations 002 and 003](../../projects/nyc/sequences/seq_010/sh_0010/generations.md).*

The practical consequence: pick one hue per *class* of thing, chosen to be
distinct from its neighbours rather than to be what the object would really be.

## Assets and instances

**Anything built from a rule goes in an asset, not baked into the scene.** Eight
cars of eight primitives landed in a scene as sixty-four objects with the rule
that made them thrown away; changing the windscreen rake meant sixty-four hand
edits. The same cars are now eight lines and one asset file.

*Evidence: [`assets/sedan.json`](../../projects/nyc/assets/sedan.json), and the
`instances` list in
[`street_a.json`](../../projects/nyc/sequences/seq_010/sh_0010/street_a.json).*

**Author in the unit space of the asset's own bounding box.** Every number in
those cars was already a fraction of the footprint — a roof 0.76 as wide as the
body, wheels at 0.235 of the height — so one recipe covers a saloon and a van at
their own proportions. If you find yourself writing a number in metres inside an
asset, the asset is only correct at one size.

**A shape that must change with proportion needs vertices, not a rotated
primitive.** A rotated box carries one stored angle. A windscreen raked 34.8° on
a 4.6 m car should be 34.4° on a 5.6 m one and 46.9° on a short tall one,
because the rake is rise over run — and vertices declared in unit space get
that for free while a stored angle cannot.

*Evidence: the `mesh` part in
[`assets/sedan_solid.json`](../../projects/nyc/assets/sedan_solid.json), measured
against the boxed version in the grid above. It also came out at six parts
instead of eight.*

**Turn instances about Z only.** A yaw folds exactly into a part's own XYZ
euler; a general rotation would need composing, and a wrong composition is
invisible in a grey render and obvious in the result.

**Expand in one place.** Blender, `audit` and `check` must be looking at the
same geometry. Anything that expanded separately would be measuring a different
shot — which is exactly the mistake the interpolation made before it was lifted
out of the render script.

## Camera and clearance

**Author the camera first, then dress the scene.** The move is the shot; the
geometry exists to make the move legible. Render once the camera exists and
before the dressing, because that render is what tells you what the dressing is
for.

**Proximity is what sells speed.** Parallax past close objects reads as
velocity; an empty corridor at the same speed reads as a drift. This is why the
cars are at 0.95 m and not at three metres.

**Never let the camera pass through geometry, and do not trust your eyes for
it.** A camera inside a car renders as nothing at all, so a contact sheet cannot
catch it. Run `audit`: it is free, it measures the baked path rather than the
keys, and it exits non-zero on a penetration.

**Retiming slides the move against fixed dressing.** A clearance that held
before a timing change does not hold after one. Three cars were being driven
through after the crest moved two seconds earlier.

**Measure clearance along an object's whole length, not at the moment that looks
tightest.** The closest approach to a 5 m car is at the far end of it, where the
camera has already begun to come back — placing against the weave peak alone
left barely half the intended gap.

*Evidence: [nyc/sh_0010 notes](../../projects/nyc/sequences/seq_010/sh_0010/notes.md),
"Retimed: the crest two seconds earlier".*

## Movement

**A continuous move uses `smooth` easing.** `ease` is a smoothstep, and
smoothstep has zero velocity at *both* ends, so a chain of eased keys arrives,
halts and sets off again at every one. `linear` has the opposite fault: constant
speed inside a segment and an instant change of direction at the key, which
makes a position track a polyline with corners.

**Read the values you are writing as a curve, not as a list of positions.**
Speed follows key spacing, which is how a move gets steered without anyone
typing a velocity.

## What has not been settled

- **Scene-level rules for what to colour.** "One hue per class" is a suggestion,
  not something `check` can enforce.
- **Framing.** `audit` measures where the camera is and what it nearly hits; it
  says nothing about whether the subject is in frame, how much of the frame it
  fills, or which side it sits on. That half of the loop is designed and not
  built — see [feedback-loop.md](../design/feedback-loop.md).
- **The cut.** Screen direction and the 180° line are geometry, and the geometry
  is in the spec, so they are checkable — but nothing has two shots yet.
