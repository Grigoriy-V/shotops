"""Checks that run without Blender: spec validation and the baking math.

build_scene.py lives inside Blender, but its interpolation is stdlib-only, so we
import it with stub bpy/mathutils modules and exercise the math directly.
"""

import json
import math
import os
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


def _load_build_scene():
    """Import blender/build_scene.py with bpy and mathutils stubbed out."""
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
    import build_scene

    return build_scene


bs = _load_build_scene()
failures = []


def check(label, got, want, tol=1e-6):
    ok = all(abs(a - b) <= tol for a, b in zip(got, want)) if isinstance(want, list) else abs(got - want) <= tol
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

check("default provider is piapi", get_provider("piapi").name == "piapi/seedance", True)
check("comet still reachable", get_provider("comet").name == "cometapi/seedance", True)

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

for provider_name in ("piapi", "comet"):
    params = inspect.signature(get_provider(provider_name).generate).parameters
    check(f"{provider_name} accepts style_image", "style_image" in params, True)

try:
    get_provider("comet").generate(Path("a.mp4"), {"prompt": "x"}, Path("o.mp4"), style_image=Path("s.png"))
    failures.append("comet style_image: expected ValueError")
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

with tempfile.TemporaryDirectory() as tmp:
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
