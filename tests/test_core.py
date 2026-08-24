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
        mathutils.Quaternion = lambda v: v
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

print("sample() -- degenerate input")
check("zero-length segment", bs.sample([{"t": 1.0, "value": [5.0]}, {"t": 1.0, "value": [9.0]}], 1.0), [5.0])
check("single key", bs.sample([{"t": 0.0, "value": [3.0]}], 7.0), [3.0])

print("spec validation -- the demo scene")
demo = spec_mod.load(ROOT / "scenes" / "demo_cube.json")
check("demo duration", demo["duration"], 5.0)
check("demo object count", len(demo["objects"]), 4)


def expect_error(label, mutate):
    scene = json.loads((ROOT / "scenes" / "demo_cube.json").read_text(encoding="utf-8"))
    mutate(scene)
    try:
        spec_mod.validate(scene)
    except spec_mod.SpecError as exc:
        print(f"  ok   {label} -> {exc}")
        return
    failures.append(f"{label}: expected a SpecError, got none")
    print(f"  FAIL {label}: no error raised")


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
