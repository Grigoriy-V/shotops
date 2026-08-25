"""Checks that run without Blender: spec validation and the baking math.

build_scene.py lives inside Blender, but its interpolation is stdlib-only, so we
import it with stub bpy/mathutils modules and exercise the math directly.
"""

import base64
import importlib
import json
import math
import os
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_render import spec as spec_mod  # noqa: E402


class Quat:
    """Enough of mathutils.Quaternion to check camera-angle composition.

    Real quaternion algebra, not a placeholder: the thing worth testing about
    `orient()` is the multiplication order, and a stub that discarded it would
    pass whatever the code did.
    """

    def __init__(self, value, angle=None):
        if angle is None:
            self.w, self.x, self.y, self.z = (float(c) for c in value)
        else:  # axis-angle
            ax, ay, az = value
            length = math.sqrt(ax * ax + ay * ay + az * az) or 1.0
            half = angle / 2.0
            s = math.sin(half) / length
            self.w, self.x, self.y, self.z = math.cos(half), ax * s, ay * s, az * s

    def __matmul__(self, other):
        a, b = self, other
        return Quat((
            a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
            a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
            a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
            a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
        ))

    def dot(self, other):
        return self.w * other.w + self.x * other.x + self.y * other.y + self.z * other.z

    def parts(self):
        return [self.w, self.x, self.y, self.z]


def _load_blender_script(name):
    """Import one of blender/*.py with bpy and mathutils stubbed out."""
    if "bpy" not in sys.modules:
        bpy = types.ModuleType("bpy")
        bpy.ops = types.SimpleNamespace()
        bpy.context = types.SimpleNamespace()
        bpy.data = types.SimpleNamespace()
        sys.modules["bpy"] = bpy

        mathutils = types.ModuleType("mathutils")
        mathutils.Vector = lambda v: v
        mathutils.Quaternion = Quat
        sys.modules["mathutils"] = mathutils

    sys.path.insert(0, str(ROOT / "blender"))
    return importlib.import_module(name)


bs = _load_blender_script("build_scene")
failures = []


def check(label, got, want, tol=1e-6):
    if isinstance(want, list) and all(isinstance(v, (int, float)) for v in want):
        ok = len(got) == len(want) and all(abs(a - b) <= tol for a, b in zip(got, want))
    elif isinstance(want, (int, float)) and not isinstance(want, bool):
        ok = abs(got - want) <= tol
    else:
        ok = got == want
    if not ok:
        failures.append(f"{label}: got {got}, want {want}")
    print(f"  {'ok  ' if ok else 'FAIL'} {label}")


print("sample() -- keyframe evaluation")
track = [
    {"t": 0.0, "value": [0.0, 0.0, 0.0], "ease": "linear"},
    {"t": 4.0, "value": [8.0, 0.0, 4.0]},
]
check("clamps before first key", bs.sample(track, -1.0), [0.0, 0.0, 0.0])
check("clamps after last key", bs.sample(track, 99.0), [8.0, 0.0, 4.0])
check("hits keys exactly", bs.sample(track, 4.0), [8.0, 0.0, 4.0])
check("linear midpoint", bs.sample(track, 2.0), [4.0, 0.0, 2.0])

eased = [{"t": 0.0, "value": [0.0], "ease": "ease"}, {"t": 2.0, "value": [10.0]}]
check("smoothstep midpoint == linear", bs.sample(eased, 1.0), [5.0])
check("smoothstep eases in", bs.sample(eased, 0.2)[0], 10.0 * (0.1**2) * (3 - 2 * 0.1))
check("smoothstep endpoint", bs.sample(eased, 2.0), [10.0])

three = [
    {"t": 0.0, "value": [0.0], "ease": "linear"},
    {"t": 1.0, "value": [10.0], "ease": "linear"},
    {"t": 3.0, "value": [30.0]},
]
check("picks the right segment", bs.sample(three, 2.0), [20.0])

print("sample() -- smooth carries velocity through a key")


def velocity(track, t, h=1e-4):
    a, b = bs.sample(track, t - h), bs.sample(track, t + h)
    return [(bv - av) / (2 * h) for av, bv in zip(a, b)]


two = [{"t": 0.0, "value": [0.0, 0.0], "ease": "smooth"}, {"t": 2.0, "value": [10.0, 4.0]}]
check("two keys are exactly linear", bs.sample(two, 0.5), [2.5, 1.0])

# An even run of keys: nothing about it should vary in speed at all.
even = [{"t": float(i), "value": [10.0 * i], "ease": "smooth"} for i in range(5)]
check("hits every key", [bs.sample(even, float(i))[0] for i in range(5)], [0.0, 10.0, 20.0, 30.0, 40.0])
check("even spacing stays even", round(bs.sample(even, 1.5)[0], 6), 15.0)

# The failure this mode exists to fix: `ease` stops dead on the shared key.
stops = [dict(k, ease="ease") for k in even]
check("ease stalls at the key", velocity(stops, 2.0)[0] < 0.01, True)
check("smooth does not stall", round(velocity(even, 2.0)[0], 6), 10.0)
before, after = velocity(even, 2.0 - 0.3), velocity(even, 2.0 + 0.3)
check("velocity is continuous across the key", round(before[0] - after[0], 6), 0.0)

# Speed follows key spacing, which is how the move gets steered.
uneven = [
    {"t": 0.0, "value": [0.0], "ease": "smooth"},
    {"t": 1.0, "value": [20.0], "ease": "smooth"},
    {"t": 3.0, "value": [30.0], "ease": "smooth"},
    {"t": 6.0, "value": [33.0]},
]
check("wide keys are slower than tight ones", velocity(uneven, 0.5)[0] > velocity(uneven, 4.5)[0], True)
check("no stall at an uneven key", velocity(uneven, 1.0)[0] > 1.0, True)

print("sample() -- degenerate input")
check("zero-length segment", bs.sample([{"t": 1.0, "value": [5.0]}, {"t": 1.0, "value": [9.0]}], 1.0), [5.0])
check("single key", bs.sample([{"t": 0.0, "value": [3.0]}], 7.0), [3.0])

print("spec validation -- the demo scene")
DEMO_SHOT = ROOT / "projects" / "demo" / "sequences" / "seq_010" / "sh_0010"
DEMO_SCENE = DEMO_SHOT / "cube.json"
demo, demo_target = spec_mod.load_target(DEMO_SCENE)
check("demo duration comes from the shot", demo["duration"], 5.0)
check("demo object count", len(demo["objects"]), 4)
check("demo fps comes from the project", demo["fps"], 24)


def expect_error(label, mutate):
    # Deep copy: these mutations reach into nested lists, and a shallow copy
    # would quietly corrupt the shared spec for every later check.
    scene = json.loads(json.dumps(demo))
    mutate(scene)
    try:
        spec_mod.validate(scene)
    except spec_mod.SpecError as exc:
        print(f"  ok   {label} -> {exc}")
        return
    failures.append(f"{label}: expected a SpecError, got none")
    print(f"  FAIL {label}: no error raised")


print("camera angles -- reading")
cam = {"roll": -6.0, "animation": {"pan": [{"t": 0.0, "value": [0.0]}, {"t": 2.0, "value": [20.0]}]}}
check("static angle", bs.angle(cam, "roll", 1.0), -6.0)
check("absent angle is zero", bs.angle(cam, "tilt", 1.0), 0.0)
check("animated angle beats static", bs.angle(cam, "pan", 1.0), 10.0)

print("camera angles -- composition")
_real_aim = bs.aim
bs.aim = lambda loc, target: Quat((1.0, 0.0, 0.0, 0.0))  # identity, so only the offsets show
check("no angles is identity", bs.orient([0, 0, 0], [0, 1, 0]).parts(), [1.0, 0.0, 0.0, 0.0])
check(
    "roll turns about the view axis",
    bs.orient([0, 0, 0], [0, 1, 0], roll=90.0).parts(),
    Quat((0.0, 0.0, 1.0), math.radians(90.0)).parts(),
)
check(
    "zero is identical to absent",
    bs.orient([0, 0, 0], [0, 1, 0], pan=0.0, tilt=0.0, roll=0.0).parts(),
    bs.orient([0, 0, 0], [0, 1, 0]).parts(),
)
composed = bs.orient([0, 0, 0], [0, 1, 0], pan=30.0, tilt=15.0, roll=45.0)
expected = (
    Quat((0.0, 1.0, 0.0), math.radians(30.0))
    @ Quat((1.0, 0.0, 0.0), math.radians(15.0))
    @ Quat((0.0, 0.0, 1.0), math.radians(45.0))
)
check("order is pan, tilt, roll", composed.parts(), expected.parts())
wrong_order = (
    Quat((0.0, 0.0, 1.0), math.radians(45.0))
    @ Quat((1.0, 0.0, 0.0), math.radians(15.0))
    @ Quat((0.0, 1.0, 0.0), math.radians(30.0))
)
check(
    "order actually matters (guards the check above)",
    1.0 if abs(composed.dot(wrong_order)) < 0.999 else 0.0,
    1.0,
)
bs.aim = _real_aim

print("camera angles -- validation")
expect_error("roll as a list", lambda s: s["camera"].update(roll=[5.0]))
expect_error("roll as a string", lambda s: s["camera"].update(roll="45deg"))
expect_error("pan track of the wrong width", lambda s: s["camera"].setdefault("animation", {}).update(
    pan=[{"t": 0.0, "value": [0.0, 1.0]}]
))

print("project structure")
from ai_render import project as project_mod  # noqa: E402

check("shot scene resolves", project_mod.resolve(DEMO_SCENE).kind == "shot", True)
check(
    "identity comes from the path",
    project_mod.resolve(DEMO_SCENE).out_parts == ("demo", "seq_010", "sh_0010", "cube"),
    True,
)
check("shot directory resolves via shot.json", project_mod.resolve(DEMO_SHOT).scene == "cube", True)
check(
    "standalone scene keeps one segment",
    project_mod.resolve(ROOT / "nowhere" / "loose.json").out_parts == ("loose",),
    True,
)
check(
    "asset path is recognised",
    project_mod.resolve(ROOT / "projects" / "demo" / "assets" / "prop.json").kind == "asset",
    True,
)


def expect_project_error(label, path):
    try:
        project_mod.resolve(path)
    except project_mod.ProjectError as exc:
        print(f"  ok   {label} -> {exc}")
        return
    failures.append(f"{label}: expected a ProjectError, got none")
    print(f"  FAIL {label}: no error raised")


expect_project_error("a level file is not a scene", DEMO_SHOT / "shot.json")
expect_project_error("project file is not a scene", ROOT / "projects" / "demo" / "project.json")

print("still positions -- first and last always included")
rf = _load_blender_script("render_frames")
check("five spans the shot", rf.positions(5), [0.0, 0.25, 0.5, 0.75, 1.0])
check("two is just the ends", rf.positions(2), [0.0, 1.0])
check("one does not divide by zero", rf.positions(1), [0.0])
check("names round to whole percent", ["t%03d" % round(p * 100) for p in rf.positions(5)],
      ["t000", "t025", "t050", "t075", "t100"])

print("audit -- bounds and clearance")
from ai_render import audit as audit_mod  # noqa: E402

check("a cube's half extents follow size and scale",
      audit_mod._half_extents({"type": "cube", "size": 1.0, "scale": [1.9, 4.6, 1.5]}),
      (0.95, 2.3, 0.75))
check("a plane is flat", audit_mod._half_extents({"type": "plane", "size": 2.0})[2], 0.0)
check("a cylinder is radius by depth",
      audit_mod._half_extents({"type": "cylinder", "size": 0.34, "depth": 0.25}),
      (0.34, 0.34, 0.125))
# A wheel: a cylinder laid on its side, so the depth axis becomes X.
laid = audit_mod._rotated_extents(
    {"type": "cylinder", "size": 0.34, "depth": 0.25, "rotation": [0, 90, 0]}
)
check("rotating 90 about Y swaps X and Z", [round(v, 6) for v in laid], [0.125, 0.34, 0.34])
check("an unrotated object is untouched",
      audit_mod._rotated_extents({"type": "cube", "size": 2.0}), (1.0, 1.0, 1.0))
# A mesh is measured from its own vertices, symmetric about the origin. That
# over-estimates a lopsided part rather than under-estimating it, and a
# clearance that errs has to err toward "too close".
check("a mesh is measured from its vertices",
      audit_mod._half_extents({"type": "mesh",
                               "vertices": [[-0.4, 0.27, -0.16], [0.36, -0.32, 0.16]],
                               "scale": [2.0, 1.0, 1.0]}),
      (0.8, 0.32, 0.16))
check("animated scale is measured at its widest",
      audit_mod._half_extents({
          "type": "cube", "size": 1.0, "scale": [1.0, 1.0, 1.0],
          "animation": {"scale": [{"t": 0.0, "value": [1.0, 1.0, 1.0]},
                                  {"t": 1.0, "value": [4.0, 1.0, 1.0]}]},
      })[0], 2.0)

check("distance to a box is zero inside it",
      audit_mod._box_distance([0, 0, 0], [0, 0, 0], (1, 1, 1)), 0.0)
check("distance is measured to the face",
      audit_mod._box_distance([3, 0, 0], [0, 0, 0], (1, 1, 1)), 2.0)
check("and to the corner when past two faces",
      audit_mod._box_distance([4, 4, 0], [0, 0, 0], (1, 1, 1)), math.sqrt(18))

# The failure this command exists for: a camera flying straight through a car.
through = {
    "fps": 24, "duration": 1.0,
    "camera": {"look_at": [0, 10, 1], "animation": {"location": [
        {"t": 0.0, "value": [0.0, -10.0, 1.0], "ease": "linear"},
        {"t": 1.0, "value": [0.0, 10.0, 1.0]},
    ]}},
    "objects": [{"name": "car", "type": "cube", "size": 1.0,
                 "location": [0, 0, 0.75], "scale": [1.9, 4.6, 1.5]}],
}
gaps = audit_mod.clearances(through, audit_mod.path(through))
check("a penetration reads as zero clearance", gaps[0]["distance"], 0.0)
lines, hits = audit_mod.report(through)
check("and is reported as a hit", [h["name"] for h in hits], ["car"])

aside = json.loads(json.dumps(through))
aside["objects"][0]["location"] = [5.0, 0.0, 0.75]
clear = audit_mod.clearances(aside, audit_mod.path(aside))
check("moved aside, the gap is body edge to camera", round(clear[0]["distance"], 6), 4.05)
check("nothing is reported as a hit", audit_mod.report(aside)[1], [])

print("audit -- motion")
fps = 24
straight = audit_mod.motion(audit_mod.path(through), fps)
check("constant speed on a linear track", round(straight[-1]["speed"], 3), 20.0)
check("and no acceleration", round(straight[-1]["accel"], 3), 0.0)
check("a linear move has no stalls", audit_mod.stalls(straight), [])

# `ease` on every key is the arrive-halt-continue fault, and it has to be
# caught in the middle of a move but not at the end of one.
halting = {
    "fps": 24, "duration": 4.0,
    "camera": {"look_at": [0, 0, 0], "animation": {"location": [
        {"t": 0.0, "value": [0.0, 0.0, 0.0], "ease": "ease"},
        {"t": 2.0, "value": [40.0, 0.0, 0.0], "ease": "ease"},
        {"t": 4.0, "value": [80.0, 0.0, 0.0]},
    ]}},
    "objects": [],
}
halting_stalls = audit_mod.stalls(audit_mod.motion(audit_mod.path(halting), fps))
check("a chain of eased keys stalls at the join", len(halting_stalls), 1)
check("and the stall is at the key, not at the end",
      abs(halting_stalls[0]["t"] - 2.0) < 0.2, True)

smoothed = json.loads(json.dumps(halting))
for key in smoothed["camera"]["animation"]["location"]:
    key["ease"] = "smooth"
check("smooth easing does not stall",
      audit_mod.stalls(audit_mod.motion(audit_mod.path(smoothed), fps)), [])

settling = json.loads(json.dumps(halting))
settling["camera"]["animation"]["location"] = [
    {"t": 0.0, "value": [0.0, 0.0, 0.0], "ease": "out"},
    {"t": 4.0, "value": [80.0, 0.0, 0.0]},
]
check("a shot that comes to rest is not a stall",
      audit_mod.stalls(audit_mod.motion(audit_mod.path(settling), fps)), [])

print("project structure -- artifact names")
import tempfile as _tempfile  # noqa: E402

nyc_scene = ROOT / "projects" / "nyc" / "sequences" / "seq_010" / "sh_0010" / "street_a.json"
nyc = project_mod.resolve(nyc_scene)
check("stem carries sequence, shot and scene", nyc.stem, "seq_010_sh_0010_street_a")
check("no project in the name", "nyc" not in nyc.stem, True)
check("id and kind sit between scene and version",
      nyc.name("preview", "a3f9c1", 3), "seq_010_sh_0010_street_a_a3f9c1_preview_v003")
check("a still carries its position",
      nyc.name("still", "a3f9c1", 2, "t050"), "seq_010_sh_0010_street_a_a3f9c1_still_v002_t050")
check("standalone falls back to the scene", project_mod.resolve(ROOT / "loose.json").stem, "loose")

print("scene id -- content, not a counter")
spec_a = {"duration": 10.0, "objects": [{"name": "road", "scale": [14, 130, 1]}]}
spec_b = {"objects": [{"scale": [14, 130, 1], "name": "road"}], "duration": 10.0}
check("same content, same id", project_mod.scene_id(spec_a), project_mod.scene_id(spec_b))
check("key order does not matter", project_mod.scene_id(spec_a), project_mod.scene_id(spec_b))
moved = json.loads(json.dumps(spec_a))
moved["objects"][0]["scale"][0] = 14.5
check("one number changes it", project_mod.scene_id(moved) != project_mod.scene_id(spec_a), True)
check("six hex characters", len(project_mod.scene_id(spec_a)), 6)
check("matches the name pattern", re.fullmatch(r"[0-9a-f]{6}", project_mod.scene_id(spec_a)) is not None, True)

with _tempfile.TemporaryDirectory() as _tmp:
    shot_dir = Path(_tmp) / "projects" / "p" / "sequences" / "seq_010" / "sh_0010"
    shot_dir.mkdir(parents=True)
    (shot_dir / "a.json").write_text("{}", encoding="utf-8")
    fresh = project_mod.resolve(shot_dir / "a.json")
    check("first version is 1", fresh.next_version("preview"), 1)

    fresh.dir_for("preview").mkdir()
    (fresh.dir_for("preview") / f"{fresh.name('preview', 'aaaaaa', 1)}.mp4").write_text("x", encoding="utf-8")
    check("counts what is on disk", fresh.next_version("preview"), 2)

    # Each kind counts itself: "the fourth preview" has to mean the fourth
    # preview, not the fourth file of any sort in the shot.
    check("another kind is unaffected", fresh.next_version("views"), 1)
    fresh.dir_for("views").mkdir()
    (fresh.dir_for("views") / f"{fresh.name('views', 'aaaaaa', 6)}.jpg").write_text("x", encoding="utf-8")
    check("views counts views", fresh.next_version("views"), 7)
    check("sheet shares the directory but not the count", fresh.next_version("sheet"), 1)
    check("preview still unaffected", fresh.next_version("preview"), 2)

    # A new scene id does not restart the count -- otherwise two files could
    # both be "preview v001".
    (fresh.dir_for("preview") / f"{fresh.name('preview', 'bbbbbb', 2)}.mp4").write_text("x", encoding="utf-8")
    check("counts across ids", fresh.next_version("preview"), 3)

    # Deleting an old file must not renumber a name that is already committed.
    (fresh.dir_for("preview") / f"{fresh.name('preview', 'aaaaaa', 1)}.mp4").unlink()
    check("high-water mark, not a count", fresh.next_version("preview"), 3)

    (shot_dir / "b.json").write_text("{}", encoding="utf-8")
    other = project_mod.resolve(shot_dir / "b.json")
    check("a sibling scene counts separately", other.next_version("preview"), 1)

print("project structure -- inheritance")
merged = project_mod.merge(
    {"fps": 24, "render": {"stills": 8, "shadow": True}},
    {"render": {"stills": 3}},
)
check("nested dicts merge", merged["render"] == {"stills": 3, "shadow": True}, True)
check("untouched parent value survives", merged["fps"] == 24, True)
replaced = project_mod.merge({"objects": [1, 2, 3]}, {"objects": [9]})
check("lists replace rather than merge", replaced["objects"] == [9], True)

print("spec validation -- rejects bad specs")
expect_error("unknown object type", lambda s: s["objects"][1].update(type="dodecahedron"))
expect_error("unsorted keyframes", lambda s: s["camera"]["animation"]["location"].reverse())
expect_error("keyframe past duration", lambda s: s["camera"]["animation"]["location"][1].update(t=99.0))
expect_error("wrong vector width", lambda s: s["objects"][0].update(location=[1, 2]))
expect_error("unknown ease", lambda s: s["objects"][1]["animation"]["rotation"][0].update(ease="bouncy"))
expect_error("duplicate names", lambda s: s["objects"][2].update(name="hero"))
expect_error("missing camera", lambda s: s.pop("camera"))
expect_error("empty prompt", lambda s: s["generation"].update(prompt=""))
expect_error("non-numeric vector", lambda s: s["objects"][0].update(location=[1, "x", 3]))
expect_error("bad reference_mode", lambda s: s["generation"].update(reference_mode="magic"))
expect_error("duration out of range", lambda s: s["generation"].update(duration=99))
expect_error("too many stills", lambda s: s["render"].update(stills=50))
expect_error("frames mode without stills", lambda s: (s["generation"].update(reference_mode="frames"), s["render"].update(stills=1)))
expect_error("style_references not a list", lambda s: s["generation"].update(style_references="a.png"))
expect_error("empty style_references", lambda s: s["generation"].update(style_references=[]))
expect_error("blank style reference", lambda s: s["generation"].update(style_references=["a.png", "  "]))
expect_error("blank full_prompt", lambda s: s["generation"].update(full_prompt="   "))
expect_error("mesh with no vertices", lambda s: s["objects"][0].update(type="mesh", faces=[[0, 1, 2]]))
expect_error(
    "face index past the end",
    lambda s: s["objects"][0].update(
        type="mesh", vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]], faces=[[0, 1, 7]]
    ),
)
expect_error(
    "a face with two corners",
    lambda s: s["objects"][0].update(
        type="mesh", vertices=[[0, 0, 0], [1, 0, 0], [0, 1, 0]], faces=[[0, 1]]
    ),
)
expect_error("no prompt of either kind", lambda s: s["generation"].pop("prompt"))


def expect_ok(label, mutate):
    scene = json.loads(json.dumps(demo))
    mutate(scene)
    try:
        spec_mod.validate(scene)
        print(f"  ok   {label}")
    except spec_mod.SpecError as exc:
        failures.append(f"{label}: unexpected SpecError {exc}")
        print(f"  FAIL {label}: {exc}")


expect_ok(
    "full_prompt alone is enough",
    lambda s: (s["generation"].pop("prompt"), s["generation"].update(full_prompt="send this")),
)

print("assets -- an instance is the recipe times the footprint")
from ai_render import assets as assets_mod  # noqa: E402

SEDAN = {
    "parts": [
        {"name": "body", "type": "cube", "size": 1.0,
         "location": [0.0, 0.0, 0.48], "scale": [1.0, 1.0, 0.4]},
        {"name": "screen", "type": "cube", "size": 1.0,
         "location": [0.0, 0.195, 0.84], "scale": [0.76, 0.18, 0.05],
         "rotation": [-34.8, 0, 0]},
        {"name": "wheel", "type": "cylinder", "size": 0.235, "depth": 0.14,
         "location": [-0.43, -0.3, 0.235], "rotation": [0, 90, 0]},
    ]
}


_assets = Path(_tempfile.mkdtemp())
(_assets / "sedan.json").write_text(json.dumps(SEDAN), encoding="utf-8")
(_assets / "odd.json").write_text(
    json.dumps({"parts": [{"name": "odd", "type": "cube", "rotation": [10, 0, 20]}]}),
    encoding="utf-8",
)


def expand_one(instance):
    return assets_mod.expand({"objects": [], "instances": [instance]}, _assets)


base ={"asset": "sedan", "name": "car", "location": [5.9, -104, 0], "size": [1.9, 4.6, 1.5]}
made = expand_one(base)["objects"]
by_name = {o["name"]: o for o in made}
check("one instance, three parts", len(made), 3)
check("parts are named after the instance", sorted(by_name), ["car_body", "car_screen", "car_wheel"])
# The unit convention: x and y from the centre, z up from the ground.
check("body sits at 0.48 of the height", by_name["car_body"]["location"], [5.9, -104.0, 0.72])
check("and is the full footprint", by_name["car_body"]["scale"], [1.9, 4.6, 0.6])
# `size` on a cube is the base edge scale already multiplies; scaling it here
# would apply the footprint twice and make every boxed part the wrong size.
check("a cube keeps its literal size", by_name["car_body"]["size"], 1.0)
check("a radius is a fraction of height", by_name["car_wheel"]["size"], 0.235 * 1.5)
check("a depth is a fraction of width", by_name["car_wheel"]["depth"], 0.14 * 1.9)

# The point of the whole thing: a bigger footprint, the same recipe.
van = expand_one({**base, "size": [2.1, 5.6, 1.8]})["objects"]
van_body = next(o for o in van if o["name"] == "car_body")
check("a van comes out of the same asset", van_body["scale"], [2.1, 5.6, 0.72])

# A yaw turns the offsets and folds into each part's own euler, which is exact
# because Rz(yaw) @ Ry(b) @ Rx(c) is itself an XYZ euler with z = yaw.
turned = expand_one({**base, "rotation": [0, 0, 180]})["objects"]
turned_by_name = {o["name"]: o for o in turned}
check("yaw mirrors the offset", turned_by_name["car_screen"]["location"][1], -104 - 0.195 * 4.6)
check("and lands in the part's z", turned_by_name["car_screen"]["rotation"], [-34.8, 0.0, 180.0])
check("x offsets mirror too", turned_by_name["car_wheel"]["location"][0], 5.9 + 0.43 * 1.9)

check("no instances, no change", assets_mod.expand({"objects": [1]}, None), {"objects": [1]})

# A mesh part has no size or depth to carry the footprint, so it rides on the
# object scale -- which is the point of it. The polygons are placed in unit
# space, so the rake of a raked face follows the proportions instead of being a
# stored angle that is only right for one car.
(_assets / "solid.json").write_text(json.dumps({"parts": [
    {"name": "greenhouse", "type": "mesh", "location": [0.0, 0.0, 0.84],
     "vertices": [[-0.4, 0.27, -0.16], [0.4, 0.27, -0.16], [-0.36, 0.12, 0.16], [0.36, 0.12, 0.16]],
     "faces": [[0, 1, 3, 2]]}
]}), encoding="utf-8")
solid = expand_one({**base, "asset": "solid"})["objects"][0]
check("a mesh takes the footprint through scale", solid["scale"], [1.9, 4.6, 1.5])
check("and keeps its unit vertices", solid["vertices"][0], [-0.4, 0.27, -0.16])


def rake(size):
    obj = assets_mod.expand(
        {"objects": [], "instances": [{"asset": "solid", "name": "c", "location": [0, 0, 0], "size": size}]},
        _assets,
    )["objects"][0]
    belt, roof = obj["vertices"][0], obj["vertices"][2]
    run = abs(roof[1] - belt[1]) * obj["scale"][1]
    rise = abs(roof[2] - belt[2]) * obj["scale"][2]
    return math.degrees(math.atan2(rise, run))


# The whole reason a mesh exists here: a longer car has a shallower windscreen,
# and a rotated box cannot know that because its angle was stored once.
check("rake on the 4.6 m car", round(rake([1.9, 4.6, 1.5]), 1), 34.8)
check("shallower on a 5.6 m car", round(rake([2.1, 5.6, 1.8]), 1), 34.4)
check("steeper on a short tall one", rake([2.4, 3.8, 1.9]) > 45.0, True)


def expect_asset_error(label, instance):
    try:
        expand_one(instance)
        failures.append(f"{label}: expected an AssetError")
        print(f"  FAIL {label}")
    except assets_mod.AssetError as exc:
        print(f"  ok   {label} -> {exc}")


expect_asset_error("tilted instance", {**base, "rotation": [15, 0, 0]})
expect_asset_error("size that is not three numbers", {**base, "size": [1.9, 4.6]})
expect_asset_error("instance naming no asset", {"name": "car", "location": [0, 0, 0]})
# Rz(yaw) @ Rz(rz) @ Ry(ry) @ Rx(rx) is not an XYZ euler when there is a turn
# between the two Z rotations, and a wrong composition is invisible in a grey
# render and obvious in the result.
expect_asset_error(
    "yaw onto a part already turning about Z and X",
    {**base, "asset": "odd", "rotation": [0, 0, 90]},
)
expect_asset_error("an asset that is not there", {**base, "asset": "hatchback"})

print("style references -- where they come from, and in what order")
from ai_render.cli import _style_references  # noqa: E402

with _tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "styleframes").mkdir()
    for stem in ("a", "b", "c"):
        (root / "styleframes" / f"{stem}.png").write_bytes(b"")
    take = root / "take"
    take.mkdir()

    class FakeTarget:
        scene_path = root / "scene.json"

    spec_refs = {"style_references": ["styleframes/a.png", "styleframes/b.png"]}
    resolved = _style_references(None, spec_refs, FakeTarget(), take)
    check("spec paths resolve against the shot directory", [p.name for p in resolved], ["a.png", "b.png"])

    flagged = _style_references([str(root / "styleframes" / "c.png")], spec_refs, FakeTarget(), take)
    check("flags beat the spec's list", [p.name for p in flagged], ["c.png"])

    # Order is the only thing binding a file to its @image tag, so a reversed
    # list has to come back reversed rather than sorted back into place.
    backwards = {"style_references": ["styleframes/b.png", "styleframes/a.png"]}
    check(
        "order is preserved, not sorted",
        [p.name for p in _style_references(None, backwards, FakeTarget(), take)],
        ["b.png", "a.png"],
    )

    check("no references at all is fine", _style_references(None, {}, FakeTarget(), take), [])
    (take / "styleframe.png").write_bytes(b"")
    check(
        "a styleframe in the take is the last resort",
        [p.name for p in _style_references(None, {}, FakeTarget(), take)],
        ["styleframe.png"],
    )
    try:
        _style_references(None, {"style_references": ["nope.png"]}, FakeTarget(), take)
        failures.append("missing style reference: expected FileNotFoundError")
        print("  FAIL missing reference is caught before uploading")
    except FileNotFoundError:
        print("  ok   missing reference is caught before uploading")

print("cometapi -- size table")
from ai_render.providers.cometapi import CometSeedance, resolve_size  # noqa: E402

check("720p 16:9", resolve_size({}) == "1280x720", True)
check("480p 9:16", resolve_size({"resolution": "480p", "aspect_ratio": "9:16"}) == "480x854", True)
check("explicit WxH passes through", resolve_size({"resolution": "1470x630"}) == "1470x630", True)
for label, gen in [("bad tier", {"resolution": "4k"}), ("bad ratio", {"aspect_ratio": "5:4"})]:
    try:
        resolve_size(gen)
        failures.append(f"resolve_size {label}: expected ValueError")
        print(f"  FAIL resolve_size {label}")
    except ValueError:
        print(f"  ok   resolve_size rejects {label}")

print("providers -- shared reference contract")
from ai_render.providers.base import build_reference_prompt, get_provider  # noqa: E402

described = build_reference_prompt("a granite monolith", "frames", 3)
video_desc = build_reference_prompt("a granite monolith", "video", 1)
check("frames mode tags every still", all(f"@image{i}" in described for i in (1, 2, 3)), True)
check("frames mode keeps the look prompt", "a granite monolith" in described, True)
check("video mode uses the native @video1 tag", "@video1" in video_desc, True)
# Bracket syntax is a wrapper convention; the native API ignores it, which is
# what silently unbound the reference on the first live run.
check("no bracket-style tags anywhere", "[Video" not in video_desc and "[Image" not in described, True)
check("enumerates what to keep", "motion trajectory" in video_desc, True)
check("excludes the blockout's own look", "do not copy" in video_desc.lower(), True)

# The sentence that separated generation 003 from 002. Without it the model
# reads a red box as art direction instead of as a marker, and paints the whole
# frame that colour -- so this is a contract term, not decoration.
styled = build_reference_prompt("a granite monolith", "video", 1, styles=3)
check("tags every look reference", all(f"@image{i}" in styled for i in (1, 2, 3)), True)
check(
    "hands appearance to the images alone",
    "appearance is determined solely by" in styled.lower(),
    True,
)
check(
    "and takes no framing from them",
    "no camera, framing or object placement" in styled,
    True,
)
check("no style references, no split", "@image1" not in video_desc, True)
one = build_reference_prompt("a granite monolith", "video", 1, styles=1)
check("one reference reads as singular", "use it as the reference" in one, True)

print("providers -- a tested prompt is sent as tested")
from ai_render.providers.base import resolve_prompt, unbound_image_tags  # noqa: E402

# The whole point of full_prompt: a prompt someone ran and judged good must
# arrive byte for byte, contract and all. Anything assembled around it would be
# substituting an untested string for a tested one.
verbatim = "Maintain the camera movement from Video 1.\n\nUse Image 1 and Image 2."
check(
    "full_prompt goes out untouched",
    resolve_prompt({"full_prompt": verbatim, "prompt": "ignored"}, "video", 1, styles=2),
    verbatim,
)
check(
    "without it the contract is built",
    resolve_prompt({"prompt": "a granite monolith"}, "video", 1, styles=0),
    build_reference_prompt("a granite monolith", "video", 1),
)
check("blank full_prompt falls through", resolve_prompt({"full_prompt": "", "prompt": "x"}, "video", 1)[-1], "x")

# A verbatim prompt can name more images than the scene will attach, and the
# result is a shot describing something that was never uploaded.
check("names an image nobody uploaded", unbound_image_tags(verbatim, 1), [2])
check("all bound is quiet", unbound_image_tags(verbatim, 2), [])
check("fewer named than attached is fine", unbound_image_tags(verbatim, 5), [])
check("@image form counts too", unbound_image_tags("use @image3 heavily", 2), [3])
check("no image talk at all", unbound_image_tags("a granite monolith", 0), [])

print("cometapi -- response url extraction")
for label, body in [
    ("flat video_url", {"video_url": "http://a/v.mp4"}),
    ("nested video.url", {"video": {"url": "http://a/v.mp4"}}),
    ("data list of dicts", {"data": [{"url": "http://a/v.mp4"}]}),
    ("data list of strings", {"data": ["http://a/v.mp4"]}),
    ("output string", {"output": "http://a/v.mp4"}),
]:
    check(label, CometSeedance._extract_url(body) == "http://a/v.mp4", True)
check("no url found -> None", CometSeedance._extract_url({"status": "completed"}) is None, True)

print("providers -- registry and piapi guards")
from ai_render.providers.piapi import PiapiSeedance  # noqa: E402
from ai_render.providers.h3zero import H3Zero, validate_h3_prompt  # noqa: E402

check("default provider is piapi", get_provider("piapi").name == "piapi/seedance", True)
check("comet still reachable", get_provider("comet").name == "cometapi/seedance", True)
check("h3zero is registered", get_provider("h3zero").name == "h3zero/minimax-h3", True)
check("h3 alias is registered", get_provider("h3").model, "turbo_4")

print("providers -- model variant precedence")
os.environ.pop("AI_RENDER_PIAPI_TASK_TYPE", None)
check("falls back to the mini tier", get_provider("piapi").task_type == "seedance-2-mini", True)
os.environ["AI_RENDER_PIAPI_TASK_TYPE"] = "seedance-2-fast"
check("env overrides the fallback", get_provider("piapi").task_type == "seedance-2-fast", True)
check("argument overrides env", get_provider("piapi", model="seedance-2").task_type == "seedance-2", True)
os.environ.pop("AI_RENDER_PIAPI_TASK_TYPE", None)
try:
    PiapiSeedance(task_type="seedance-2-mini").generate(
        Path("nope.mp4"), {"prompt": "x", "resolution": "1080p"}, Path("out.mp4")
    )
    failures.append("1080p on mini: expected ValueError")
    print("  FAIL 1080p rejected on mini tier")
except ValueError:
    print("  ok   1080p rejected on the mini tier")
try:
    get_provider("nope")
    failures.append("unknown provider: expected ValueError")
    print("  FAIL unknown provider rejected")
except ValueError:
    print("  ok   unknown provider rejected")

# The CLI always passes style_image; a provider missing it is a TypeError at
# call time, i.e. after the blockout has already been uploaded.
import inspect  # noqa: E402

for provider_name in ("piapi", "comet", "h3zero"):
    params = inspect.signature(get_provider(provider_name).generate).parameters
    check(f"{provider_name} accepts style_images", "style_images" in params, True)
    # The CLI hands over a callback that writes the task id into the manifest
    # before polling starts. A provider missing it is a TypeError after the
    # blockout has been uploaded; a provider that accepts it and never calls it
    # loses the only handle on a paid generation.
    check(f"{provider_name} accepts on_task", "on_task" in params, True)

print("h3zero -- prompt grammar and direct multipart job")
validate_h3_prompt("Keep <Video 1>; use <Picture 1>.", 1)
saved_h3_auth = {
    name: os.environ.get(name)
    for name in (
        "AI_RENDER_H3ZERO_AUTH",
        "AI_RENDER_H3ZERO_MODAL_KEY",
        "AI_RENDER_H3ZERO_MODAL_SECRET",
    )
}
try:
    os.environ["AI_RENDER_H3ZERO_AUTH"] = "modal-proxy"
    os.environ["AI_RENDER_H3ZERO_MODAL_KEY"] = "wk-test"
    os.environ["AI_RENDER_H3ZERO_MODAL_SECRET"] = "ws-test"
    check(
        "h3 modal proxy credentials become request headers",
        H3Zero._auth_headers(),
        {"Modal-Key": "wk-test", "Modal-Secret": "ws-test"},
    )
finally:
    for name, value in saved_h3_auth.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
for label, prompt, pictures in [
    ("lowercase tag", "Keep <video 1>.", 0),
    ("missing video", "Use <Picture 1>.", 1),
    ("zero picture", "Keep <Video 1>; use <Picture 0>.", 1),
    ("unbound picture", "Keep <Video 1>; use <Picture 2>.", 1),
    ("unbound audio", "Keep <Video 1>; hear <Audio 1>.", 0),
]:
    try:
        validate_h3_prompt(prompt, pictures)
        failures.append(f"h3zero {label}: expected ValueError")
        print(f"  FAIL h3zero rejects {label}")
    except ValueError:
        print(f"  ok   h3zero rejects {label}")

h3_events = []
h3_captured = {}
h3 = H3Zero(sampling_profile="turbo_4", poll_interval=0.0)


def _h3_request(method, path, form=None, files=None):
    if method == "POST" and path == "/api/jobs":
        h3_events.append("submit")
        h3_captured["prompt"] = form["prompt"]
        h3_captured["config"] = json.loads(form["config"])
        h3_captured["files"] = files
        return 202, {"id": "h3-job-42"}
    if method == "GET":
        h3_events.append("poll")
        return 200, {"id": "h3-job-42", "status": "completed", "progress": {"phase": "done"}}
    if method == "POST" and path.endswith("/acknowledge"):
        h3_events.append("ack")
        return 204, None
    raise AssertionError((method, path))


def _h3_download(path, out_path):
    h3_events.append("download")
    out = Path(out_path)
    out.write_bytes(b"fake-h3-mp4")
    return out


h3._request = _h3_request
h3._download = _h3_download
with _tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    blockout = tmp / "blockout.mp4"
    picture = tmp / "look.png"
    blockout.write_bytes(b"mp4")
    picture.write_bytes(b"png")
    h3.generate(
        blockout,
        {
            "full_prompt": "Seedance prompt must not be reused",
            "reference_mode": "video",
            "resolution": "480p",
            "aspect_ratio": "16:9",
            "duration": 5,
            "h3zero": {
                "sampling_profile": "turbo_4",
                "full_prompt": "Keep <Video 1>; use <Picture 1> for appearance.",
            },
        },
        tmp / "final.mp4",
        style_images=[picture],
        on_task=lambda task_id: h3_events.append(f"id:{task_id}"),
    )

check("h3 task id is saved before polling", h3_events[:3], ["submit", "id:h3-job-42", "poll"])
check("h3 acknowledges only after download", h3_events[-2:], ["download", "ack"])
check("h3 uses its own verbatim prompt", h3_captured["prompt"], "Keep <Video 1>; use <Picture 1> for appearance.")
check("h3 submits references mode", h3_captured["config"]["mode"], "references")
check("h3 submits native 480p canvas", (h3_captured["config"]["width"], h3_captured["config"]["height"]), (864, 480))
check("h3 reference upload order is stable", [item[0] for item in h3_captured["files"]], ["reference_0", "reference_1"])
check("h3 blockout is Video 1", h3_captured["config"]["references"][0]["kind"], "video")

try:
    get_provider("comet").generate(
        Path("a.mp4"), {"prompt": "x"}, Path("o.mp4"), style_images=[Path("s.png")]
    )
    failures.append("comet style_images: expected ValueError")
    print("  FAIL comet refuses style frames explicitly")
except ValueError:
    print("  ok   comet refuses style frames explicitly")

for label, gen in [
    ("bad resolution", {"prompt": "x", "resolution": "4k"}),
    ("bad aspect ratio", {"prompt": "x", "aspect_ratio": "5:4"}),
    ("stills mode", {"prompt": "x", "reference_mode": "frames"}),
]:
    try:
        PiapiSeedance().generate(Path("nope.mp4"), gen, Path("out.mp4"))
        failures.append(f"piapi {label}: expected ValueError")
        print(f"  FAIL piapi rejects {label}")
    except ValueError:
        print(f"  ok   piapi rejects {label}")
    except Exception as exc:  # must fail on validation, before any network call
        failures.append(f"piapi {label}: wrong error {type(exc).__name__}: {exc}")
        print(f"  FAIL piapi {label} raised {type(exc).__name__}")

print("piapi -- a failed task reports the reason, not the category")
from ai_render.providers.piapi import _distinct  # noqa: E402


class _Reply:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class _PollSession:
    def __init__(self, payload):
        self.payload = payload

    def get(self, url, timeout=None):
        return _Reply(self.payload)


# Taken verbatim from task a0d1ee95, which was rejected: the category the API
# returns is unactionable, the sentence that says what to change is in the logs,
# and the task's internal retry repeats it.
rejected = {
    "data": {
        "status": "failed",
        "error": {"message": "Your content violated community guidelines."},
        "logs": [
            "audio: enabled=false",
            "The request was rejected due to copyright restrictions. Please try different inputs.",
            "Attempt 1 failed (content restriction), retrying.",
            "The request was rejected due to copyright restrictions. Please try different inputs.",
        ],
    }
}
try:
    PiapiSeedance(poll_interval=0.0)._poll(_PollSession(rejected), "task-1")
    failures.append("piapi failed task: expected RuntimeError")
    print("  FAIL a failed task raises")
except RuntimeError as exc:
    check("keeps the vendor's category", "community guidelines" in str(exc), True)
    check("carries the actual reason", "copyright restrictions" in str(exc), True)
    check("collapses the internal retry", str(exc).count("copyright restrictions") == 1, True)

check("_distinct keeps first-seen order", _distinct(["b", "a", "b", " a "]), ["b", "a"])
check("_distinct drops blanks", _distinct(["", "   ", "x"]), ["x"])

print("piapi -- the task id reaches the caller before polling")
import ai_render.providers.piapi as piapi_mod  # noqa: E402
import ai_render.upload as upload_mod  # noqa: E402


class _Uploader:
    def upload(self, path):
        return f"https://example/{Path(path).name}", lambda: None


class _Created:
    status_code = 200

    @staticmethod
    def json():
        return {"data": {"task_id": "task-42"}}


class _PostSession:
    def post(self, url, json=None, timeout=None):
        created.update(json or {})
        return _Created()


created = {}
order = []
saved_session = piapi_mod.PiapiSeedance.__dict__["_session"]
saved_poll = piapi_mod.PiapiSeedance.__dict__["_poll"]
saved_download = piapi_mod.download
saved_uploader = upload_mod.get_uploader
try:
    piapi_mod.PiapiSeedance._session = staticmethod(lambda: _PostSession())
    piapi_mod.PiapiSeedance._poll = lambda self, session, task_id, first_delay=None: (
        order.append(f"poll:{task_id}") or "https://example/final.mp4"
    )
    piapi_mod.download = lambda url, out_path: (Path(out_path).write_bytes(b"0"), Path(out_path))[1]
    upload_mod.get_uploader = lambda: _Uploader()
    with _tempfile.TemporaryDirectory() as tmp:
        piapi_mod.PiapiSeedance(task_type="seedance-2-fast").generate(
            Path("blockout.mp4"),
            {"prompt": "a street at dusk", "duration": 4},
            Path(tmp) / "final.mp4",
            on_task=lambda task_id: order.append(f"id:{task_id}"),
        )
finally:
    piapi_mod.PiapiSeedance._session = saved_session
    piapi_mod.PiapiSeedance._poll = saved_poll
    piapi_mod.download = saved_download
    upload_mod.get_uploader = saved_uploader

check("on_task fires, and before the poll", order, ["id:task-42", "poll:task-42"])

# Audio follows the API's own default rather than ours. Sending false by default
# made every run a different job from generation 003, whose log reads
# `audio: enabled=true` -- and 003 is the take the shot's config reproduces.
check("audio defaults to on", created["input"]["audio"], True)
check("omni_reference is not optional", created["input"]["mode"], "omni_reference")
# Empty is the workspace default and what the playground sends. Pinning it to
# "public" was ours, not the API's.
check("service_mode is left to the workspace", created["config"]["service_mode"], "")

print("upload -- content type follows the file, not the assumption")
from ai_render.upload import content_type_for  # noqa: E402

check("mp4 -> video/mp4", content_type_for("a/preview.mp4") == "video/mp4", True)
# A PNG uploaded as video/mp4 is rejected by the model gateway *after* the task
# is created, which is the expensive place to find out.
check("png -> image/png", content_type_for("a/styleframe.png") == "image/png", True)
check("jpg -> image/jpeg", content_type_for("a/ref.JPG") == "image/jpeg", True)
check("webp -> image/webp", content_type_for("a/ref.webp") == "image/webp", True)
try:
    content_type_for("a/notes.txt")
    failures.append("content_type_for: expected ValueError for .txt")
    print("  FAIL unknown extension rejected")
except ValueError:
    print("  ok   unknown extension rejected")

print("upload -- piapi's own store, and its limits")
from ai_render.upload import PiapiUploader, configured_name, get_uploader as _get_uploader  # noqa: E402

os.environ.pop("AI_RENDER_UPLOADER", None)
check("supabase stays the default", configured_name(), "supabase")
os.environ["AI_RENDER_UPLOADER"] = "piapi"
check("env selects piapi", configured_name(), "piapi")
os.environ.pop("AI_RENDER_UPLOADER", None)
try:
    _get_uploader("nope")
    failures.append("uploader registry: expected ValueError")
    print("  FAIL unknown uploader rejected")
except ValueError:
    print("  ok   unknown uploader rejected")

# PiAPI's limits are tighter than ours: .mov and .webm are in CONTENT_TYPES but
# not on their accepted list, and 10 MB is a hard ceiling. Both must fail here,
# before a file is base64'd and posted.
uploader = PiapiUploader(key="test-key")
with _tempfile.TemporaryDirectory() as tmp:
    small = Path(tmp) / "preview.mp4"
    small.write_bytes(b"0" * 1024)
    mov = Path(tmp) / "preview.mov"
    mov.write_bytes(b"0" * 1024)
    huge = Path(tmp) / "big.mp4"
    huge.write_bytes(b"0" * (PiapiUploader.MAX_BYTES + 1))

    uploader._check(small)  # must not raise
    print("  ok   a normal blockout passes the local checks")
    for label, victim in [("a .mov", mov), ("an oversized file", huge)]:
        try:
            uploader._check(victim)
            failures.append(f"piapi uploader {label}: expected ValueError")
            print(f"  FAIL piapi uploader rejects {label}")
        except ValueError:
            print(f"  ok   piapi uploader rejects {label}")

saved_key = os.environ.pop("PIAPI_KEY", None)
try:
    PiapiUploader()
    failures.append("piapi uploader: expected RuntimeError without a key")
    print("  FAIL piapi uploader needs a key")
except RuntimeError:
    print("  ok   piapi uploader needs a key")
finally:
    if saved_key is not None:
        os.environ["PIAPI_KEY"] = saved_key

# No delete endpoint exists, so cleanup does nothing -- but it must still be
# callable and silent, because the provider runs every cleanup in a finally
# block and an exception there would mask the real result.
import requests as _requests  # noqa: E402


class _Uploaded:
    status_code = 200

    @staticmethod
    def json():
        return {"code": 200, "data": {"url": "https://storage.theapi.app/v/1.mp4"}, "message": ""}


sent = {}


def _fake_post(url, json=None, headers=None, timeout=None):
    sent.update(url=url, body=json, headers=headers)
    return _Uploaded()


saved_post = _requests.post
try:
    _requests.post = _fake_post
    with _tempfile.TemporaryDirectory() as tmp:
        blockout = Path(tmp) / "preview.mp4"
        blockout.write_bytes(b"blockout-bytes")
        url, cleanup = PiapiUploader(key="test-key").upload(blockout)
finally:
    _requests.post = saved_post

check("returns the url from data.url", url, "https://storage.theapi.app/v/1.mp4")
check("authenticates with x-api-key", sent["headers"]["x-api-key"], "test-key")
check("sends the file name", sent["body"]["file_name"], "preview.mp4")
check(
    "sends the bytes base64-encoded",
    base64.b64decode(sent["body"]["file_data"]),
    b"blockout-bytes",
)
cleanup()
print("  ok   cleanup is callable and silent")

print("runs -- one task, one directory")
import tempfile as _tempfile  # noqa: E402

from ai_render import runs as runs_mod  # noqa: E402

with _tempfile.TemporaryDirectory() as tmp:
    runs_mod.OUT = Path(tmp)

    take_a = runs_mod.new_take("scn", spec={"name": "scn", "duration": 4.0})
    check("take creates frames dir", (take_a / "frames").is_dir(), True)
    check("take snapshots the spec", json.loads((take_a / "scene.json").read_text())["duration"] == 4.0, True)

    # Two takes inside the same second must not collide.
    take_b = runs_mod.new_take("scn", spec={"name": "scn"})
    take_c = runs_mod.new_take("scn", spec={"name": "scn"})
    check("takes never collide", len({take_a, take_b, take_c}) == 3, True)
    check("all three are listed", len(runs_mod.list_takes("scn")) == 3, True)
    check("latest is the newest", runs_mod.latest_take("scn") == runs_mod.list_takes("scn")[-1], True)
    check("resolve by name", runs_mod.resolve_take("scn", take_a.name) == take_a, True)

    gen_a = runs_mod.new_generation(take_a, "seedance-2-mini", "480p")
    gen_b = runs_mod.new_generation(take_a, "seedance-2-mini", "480p")
    check("generation names carry model and res", "seedance-2-mini_480p" in gen_a.name, True)
    check("repeat generations never collide", gen_a != gen_b, True)
    check("generations listed, frames excluded", len(runs_mod.list_generations(take_a)) == 2, True)

    # `generation` is a real manifest field; it must not collide with the
    # positional parameter name.
    runs_mod.write_manifest(gen_a, scene="scn", model="seedance-2-mini", generation={"duration": 5})
    runs_mod.write_manifest(gen_a, finished_at="later")
    manifest = json.loads((gen_a / "run.json").read_text())
    check("manifest merges, does not clobber", manifest["model"] == "seedance-2-mini", True)
    check("manifest keeps the new field", manifest["finished_at"] == "later", True)

    for label, call in [
        ("unknown take", lambda: runs_mod.resolve_take("scn", "nope")),
        ("no takes at all", lambda: runs_mod.latest_take("missing-scene")),
    ]:
        try:
            call()
            failures.append(f"runs {label}: expected RuntimeError")
            print(f"  FAIL runs rejects {label}")
        except RuntimeError:
            print(f"  ok   runs rejects {label}")

print("env -- .env loading")
import os  # noqa: E402
import tempfile  # noqa: E402

from ai_render import env as env_mod  # noqa: E402

with _tempfile.TemporaryDirectory() as tmp:
    env_path = Path(tmp) / ".env"
    env_path.write_text(
        "# a comment\n"
        "\n"
        "COMETAPI_KEY=abc123\n"
        'QUOTED="with spaces"\n'
        "SINGLE='sq'\n"
        "export EXPORTED=yes\n"
        "SPACED = padded \n"
        "URL=https://api.example.com/v1?a=1\n",
        encoding="utf-8",
    )
    os.environ["COMETAPI_KEY"] = "from-real-env"
    loaded = env_mod.load(env_path)

    check("parses plain value", loaded["COMETAPI_KEY"] == "abc123", True)
    check("strips double quotes", loaded["QUOTED"] == "with spaces", True)
    check("strips single quotes", loaded["SINGLE"] == "sq", True)
    check("handles export prefix", loaded["EXPORTED"] == "yes", True)
    check("trims whitespace", loaded["SPACED"] == "padded", True)
    check("keeps = inside values", loaded["URL"] == "https://api.example.com/v1?a=1", True)
    check("real env wins over .env", os.environ["COMETAPI_KEY"] == "from-real-env", True)
    check("unset key takes .env value", os.environ["QUOTED"] == "with spaces", True)
    del os.environ["COMETAPI_KEY"]

    check("missing file is not an error", env_mod.load(Path(tmp) / "nope") == {}, True)

    bad = Path(tmp) / "bad.env"
    bad.write_text("NOT_A_PAIR\n", encoding="utf-8")
    try:
        env_mod.load(bad)
        failures.append("malformed .env: expected ValueError")
        print("  FAIL malformed line rejected")
    except ValueError as exc:
        print(f"  ok   malformed line rejected -> {exc}")

print()
if failures:
    print(f"FAILED ({len(failures)}):")
    for line in failures:
        print(f"  - {line}")
    sys.exit(1)
print("all checks passed")
