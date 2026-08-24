"""ai_render -- scene spec in, finished shot out."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import blender_runner, compare, env, runs, spec as spec_mod, styleframe
from .providers import get_provider

ROOT = Path(__file__).resolve().parents[2]
EXTRACT_SCRIPT = ROOT / "blender" / "extract_frames.py"


def _load(scene_path):
    scene = spec_mod.load(scene_path)
    return scene, spec_mod.scene_name(scene, scene_path)


def _rel(path):
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def cmd_check(args):
    scene, name = _load(args.scene)
    frames = round(scene.get("duration", 5.0) * scene.get("fps", 24))
    print(f"ok -- {name}: {len(scene.get('objects', []))} objects, {frames} frames")
    if not scene.get("generation"):
        print("note: no 'generation' block, so only `render` will work")
    return 0


def cmd_render(args):
    scene, name = _load(args.scene)
    take = runs.new_take(name, spec=scene)
    blender_runner.render(args.scene, take / "preview.mp4", verbose=args.verbose)
    print(f"[render] take {_rel(take)}")
    return 0


def cmd_generate(args):
    scene, name = _load(args.scene)
    generation = scene.get("generation")
    if not generation:
        print("error: scene has no 'generation' block", file=sys.stderr)
        return 2

    # `all` has no --take: it always generates from the take it just rendered.
    take = runs.resolve_take(name, getattr(args, "take", None))
    preview = take / "preview.mp4"
    if not preview.exists():
        print(f"error: no blockout at {_rel(preview)} -- run `render` first", file=sys.stderr)
        return 2

    # Overrides let you probe cheaply without editing the scene, then rerun at
    # the scene's own settings once the shot is right.
    if args.resolution:
        generation = {**generation, "resolution": args.resolution}
    model = args.model or generation.get("model")

    # A style still is opt-in and lives with its take, so several generations
    # can share one rather than paying for it each time.
    style_image = Path(args.style) if args.style else take / "styleframe.png"
    if not style_image.exists():
        if args.style:
            print(f"error: no style frame at {style_image}", file=sys.stderr)
            return 2
        style_image = None

    provider = get_provider(args.provider, model=model)
    resolved_model = getattr(provider, "task_type", None) or getattr(provider, "model", "default")
    out_dir = runs.new_generation(take, resolved_model, generation.get("resolution", "720p"))

    runs.write_manifest(
        out_dir,
        scene=name,
        take=take.name,
        provider=provider.name,
        model=resolved_model,
        generation=generation,
        style_frame=str(_rel(style_image)) if style_image else None,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    print(f"[generate] {_rel(out_dir)}")

    try:
        provider.generate(preview, generation, out_dir / "final.mp4", style_image=style_image)
    except Exception as exc:
        # A failed attempt is still a record worth keeping -- it is the reason
        # the next attempt is different.
        runs.write_manifest(
            out_dir, failed_at=datetime.now(timezone.utc).isoformat(), error=str(exc)[:2000]
        )
        raise

    runs.write_manifest(out_dir, finished_at=datetime.now(timezone.utc).isoformat())
    if args.extract:
        _extract(out_dir / "final.mp4", out_dir / "final_frames", args.extract, args.verbose)
        # The blockout stills exist already; a sheet costs nothing and removes
        # any chance of comparing mismatched moments by hand.
        if (take / "frames").is_dir():
            sheet = compare.build(take / "frames", out_dir / "final_frames", out_dir / "compare.png")
            print(f"[compare] {_rel(sheet)}")
    return 0


def cmd_styleframe(args):
    scene, name = _load(args.scene)
    generation = scene.get("generation") or {}
    take = runs.resolve_take(name, args.take)

    prompt = args.prompt or (generation.get("style_prompt") or generation.get("prompt"))
    if not prompt:
        print("error: no prompt -- pass --prompt or give the scene a generation block", file=sys.stderr)
        return 2
    out_path = take / "styleframe.png"

    if args.text:
        # Look exploration only: this invents its own composition, so it must
        # not be fed to a shot alongside the blockout.
        size = args.size or styleframe.default_size(generation.get("aspect_ratio", "16:9"))
        styleframe.generate_from_text(prompt, out_path, size=size, quality=args.quality)
        print("[styleframe] warning: text-to-image frame does not match the blockout's framing")
        return 0

    # Default and correct path: restyle the blockout's own frame, so the style
    # reference stays registered with the geometry the shot will use.
    source = Path(args.source) if args.source else take / "frames" / f"frame_{args.frame:02d}_.png"
    styleframe.generate_from_frame(
        source, prompt, out_path, size=args.size or "auto", quality=args.quality
    )
    print(f"[styleframe] take {_rel(take)} -- `generate` will now use it automatically")
    return 0


def cmd_compare(args):
    _, name = _load(args.scene)
    take = runs.resolve_take(name, args.take)
    generations = runs.list_generations(take)
    if not generations:
        print(f"error: no generations in {_rel(take)}", file=sys.stderr)
        return 2
    out_dir = take / args.generation if args.generation else generations[-1]
    result_frames = out_dir / "final_frames"
    if not result_frames.is_dir():
        print(
            f"error: no stills in {_rel(result_frames)} -- run "
            f"`extract {_rel(out_dir / 'final.mp4')}` first",
            file=sys.stderr,
        )
        return 2
    sheet = compare.build(take / "frames", result_frames, out_dir / "compare.png")
    print(f"[compare] {_rel(sheet)}")
    return 0


def cmd_all(args):
    rc = cmd_render(args)
    return rc or cmd_generate(args)


def cmd_takes(args):
    _, name = _load(args.scene)
    takes = runs.list_takes(name)
    if not takes:
        print(f"no takes for {name} yet")
        return 0
    for take in takes:
        generations = runs.list_generations(take)
        print(f"{take.name}  ({len(generations)} generation{'s' if len(generations) != 1 else ''})")
        for generation in generations:
            final = generation / "final.mp4"
            state = f"{final.stat().st_size / 1e6:.1f} MB" if final.exists() else "no output"
            print(f"    {generation.name}  {state}")
    return 0


def _extract(video, out_dir, count, verbose):
    """Pull stills so a result can be compared against the blockout frame for
    frame -- same indices, same time points. Blender decodes it, so no ffmpeg."""
    if not video.exists():
        print(f"error: no video at {_rel(video)}", file=sys.stderr)
        return 2
    cmd = [
        blender_runner.find_blender(), "-b", "-noaudio", "-P", str(EXTRACT_SCRIPT),
        "--", str(video), str(out_dir), str(count),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if verbose or proc.returncode != 0:
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"frame extraction failed with code {proc.returncode}")
    print(f"[extract] {count} stills -> {_rel(out_dir)}")
    return 0


def cmd_fetch(args):
    """Recover a finished task whose download failed. Generation is the
    expensive half; never pay for it twice over a transport error."""
    provider = get_provider(args.provider)
    if not hasattr(provider, "fetch"):
        print(f"error: {provider.name} cannot fetch by task id", file=sys.stderr)
        return 2
    out = Path(args.out)
    provider.fetch(args.task_id, out)
    if args.extract:
        _extract(out, out.parent / f"{out.stem}_frames", args.extract, args.verbose)
    return 0


def cmd_extract(args):
    video = Path(args.video)
    return _extract(video, video.parent / f"{video.stem}_frames", args.count, args.verbose)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ai_render", description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="stream Blender output")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, handler, help_text in [
        ("check", cmd_check, "validate a scene spec without rendering"),
        ("render", cmd_render, "Blender -> a new take with preview.mp4"),
        ("generate", cmd_generate, "blockout -> final.mp4 via the video model"),
        ("all", cmd_all, "render, then generate"),
        ("takes", cmd_takes, "list takes and generations for a scene"),
        ("styleframe", cmd_styleframe, "GPT Image 2 -> <take>/styleframe.png"),
        ("compare", cmd_compare, "side-by-side sheet: blockout vs result"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("scene", help="path to a scene .json")
        if name in ("generate", "all"):
            p.add_argument("--provider", default="piapi", help="video provider (default: piapi)")
            p.add_argument(
                "--resolution",
                help="override the scene's resolution, e.g. 480p",
            )
            p.add_argument(
                "--model",
                help="model variant within the provider (PiAPI task type, e.g. seedance-2). "
                "Beats the scene's 'model' field, which beats AI_RENDER_PIAPI_TASK_TYPE.",
            )
            p.add_argument(
                "--extract",
                nargs="?",
                type=int,
                const=8,
                default=0,
                help="also pull N stills from the result and build a comparison sheet",
            )
            p.add_argument("--style", help="style reference image (default: <take>/styleframe.png)")
        if name in ("generate", "styleframe", "compare"):
            p.add_argument("--take", help="use a specific take (default: the newest)")
        if name == "styleframe":
            p.add_argument("--prompt", help="override the scene's look prompt")
            p.add_argument(
                "--frame", type=int, default=1,
                help="which blockout still to restyle (default: 1, the first)",
            )
            p.add_argument("--source", help="restyle this image instead of a blockout still")
            p.add_argument(
                "--text", action="store_true",
                help="text-to-image instead of an edit -- look exploration only, "
                "the result will not match the blockout's framing",
            )
            p.add_argument("--size", help="default: auto, which keeps the frame's proportions")
            p.add_argument("--quality", default="high", choices=["low", "medium", "high", "auto"])
        if name == "compare":
            p.add_argument("--generation", help="which generation (default: the newest)")
        p.set_defaults(func=handler)

    p = sub.add_parser("fetch", help="download an already-finished task by id")
    p.add_argument("task_id")
    p.add_argument("out", help="destination .mp4")
    p.add_argument("--provider", default="piapi")
    p.add_argument("--extract", nargs="?", type=int, const=8, default=0)
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("extract", help="pull stills from a video for comparison")
    p.add_argument("video", help="path to an .mp4")
    p.add_argument("--count", type=int, default=8, help="number of stills (default: 8)")
    p.set_defaults(func=cmd_extract)

    args = parser.parse_args(argv)
    env.load()
    try:
        return args.func(args)
    except spec_mod.SpecError as exc:
        print(f"spec error -- {exc}", file=sys.stderr)
        return 2
    except (RuntimeError, ValueError) as exc:
        print(f"error -- {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
