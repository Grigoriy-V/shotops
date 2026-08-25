"""ai_render -- scene spec in, finished shot out."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import audit, blender_runner, compare, env, project, runs, spec as spec_mod, styleframe
from .providers import get_provider
from .providers.base import unbound_image_tags

ROOT = Path(__file__).resolve().parents[2]
EXTRACT_SCRIPT = ROOT / "blender" / "extract_frames.py"


def _load(scene_path):
    """Resolve a scene path into its spec and its place in the hierarchy.

    Returns `(spec, target)`. `target.out_parts` is the identity `out/` mirrors;
    `target.label` is what to print.
    """
    return spec_mod.load_target(scene_path)


def _rel(path):
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def cmd_check(args):
    scene, target = _load(args.scene)
    frames = round(scene.get("duration", 5.0) * scene.get("fps", 24))
    print(f"ok -- {target.label}: {len(scene.get('objects', []))} objects, {frames} frames")
    if scene.get("role") == "asset":
        print("note: role 'asset' -- scratch work, not a candidate for the shot")
    generation = scene.get("generation") or {}
    if not generation:
        print("note: no 'generation' block, so only `render` will work")
    # Checked here rather than in `spec` because only the CLI knows where the
    # scene file sits, and a reference that does not exist is a failure worth
    # catching now: the alternative is finding out after the blockout has been
    # uploaded and the meter has started.
    base = target.scene_path.parent
    missing = [r for r in generation.get("style_references", []) if not (base / r).exists()]
    if missing:
        print(f"error: style reference not found: {', '.join(missing)}", file=sys.stderr)
        return 1
    references = generation.get("style_references") or []
    if references:
        count = len(references)
        print(f"ok -- {count} style reference{'s' if count != 1 else ''}, tagged @image1..{count}")
    if generation.get("full_prompt"):
        print("note: 'full_prompt' is sent verbatim -- the reference contract is not prepended")
        unbound = unbound_image_tags(generation["full_prompt"], len(references))
        if unbound:
            named = ", ".join(f"Image {n}" for n in unbound)
            print(
                f"error: the prompt names {named}, but only {len(references)} "
                "style reference(s) will be attached",
                file=sys.stderr,
            )
            return 1
    return 0


def cmd_render(args):
    scene, target = _load(args.scene)
    take = runs.new_take(target.out_parts, spec=scene)
    # The merged spec goes to Blender, not the file on disk: inherited defaults
    # are part of the scene, and the snapshot in the take must be what rendered.
    blender_runner.render(take / "scene.json", take / "preview.mp4", verbose=args.verbose)
    print(f"[render] take {_rel(take)}")
    return 0


def cmd_audit(args):
    """Measure the baked camera move: speed, stalls, and clearance to everything.

    Free, instant, and answers what a grey contact sheet cannot -- a camera
    inside a car looks like nothing at all from inside it. Exits non-zero on a
    penetration so it can gate a render.
    """
    scene, target = _load(args.scene)
    lines, hits = audit.report(scene, closest=args.closest)
    print(f"[audit] {target.label}")
    for line in lines:
        print("  " + line)

    if hits:
        print(
            f"error: the camera passes through {len(hits)} object(s)",
            file=sys.stderr,
        )
        return 1
    tightest = audit.clearances(scene, audit.path(scene))
    if args.min_clearance and tightest and tightest[0]["distance"] < args.min_clearance:
        print(
            f"error: closest approach {tightest[0]['distance']:.2f} m to "
            f"{tightest[0]['name']}, under the {args.min_clearance:.2f} m asked for",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_views(args):
    """Render the scene from outside the shot, and keep the result with the shot."""
    import json
    import tempfile

    scene, target = _load(args.scene)
    name = target.name("views", project.scene_id(scene), target.next_version("views"))
    sheet_path = target.dir_for("views") / f"{name}.jpg"

    # The merged spec is what describes the scene; the file on disk is only its
    # most specific layer. The individual PNGs are never kept -- they are four
    # times the sheet's size, this directory gets committed, and re-rendering
    # them costs three seconds.
    with tempfile.TemporaryDirectory() as tmp:
        merged = Path(tmp) / "scene.json"
        merged.write_text(json.dumps(scene, indent=2, ensure_ascii=False), encoding="utf-8")
        made = blender_runner.render_views(merged, Path(tmp) / "views", verbose=args.verbose)
        sheet = compare.grid(made, sheet_path, columns=2, labelled=True)

    print(f"[views] {len(made)} views -> {_rel(sheet)}")
    return 0


def cmd_frames(args):
    """Render individual stills through the shot into `<shot>/frames/`.

    These are an input, not a record: a style frame gets generated from one of
    them, so they are rendered straight from the spec at full size rather than
    pulled out of a compressed preview. Evenly spaced, first and last always
    included -- five gives 0, 25, 50, 75 and 100 percent.
    """
    import json
    import shutil
    import tempfile

    scene, target = _load(args.scene)
    sid = project.scene_id(scene)
    version = target.next_version("still")
    out_dir = target.dir_for("still")
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        merged = Path(tmp) / "scene.json"
        merged.write_text(json.dumps(scene, indent=2, ensure_ascii=False), encoding="utf-8")
        made = blender_runner.render_frames(
            merged, Path(tmp) / "frames", count=args.count, verbose=args.verbose
        )
        kept = []
        for path in made:
            # One version covers the set; `t050` is the position within it, which
            # is what says which moment a still is.
            out = out_dir / f"{target.name('still', sid, version, path.stem)}.png"
            shutil.copyfile(path, out)
            kept.append(out)

    total = sum(p.stat().st_size for p in kept) / 1e6
    print(f"[frames] {len(kept)} frames -> {_rel(out_dir)} ({total:.1f} MB)")
    for path in kept:
        print(f"           {path.name}")
    return 0


def cmd_sheet(args):
    """Keep a take with the shot: the blockout in preview/, its stills in artifacts/.

    The video is the thing actually being judged, so it belongs in the record
    too. It is small -- a 10s grey blockout is under a megabyte -- and without it
    the sheet is eight frames with no motion between them. They carry different
    version numbers, being different kinds of thing, and the same scene id,
    having come from one render.
    """
    import json
    import shutil

    _, target = _load(args.scene)
    take = runs.resolve_take(target.out_parts, args.take)
    frames = sorted((take / "frames").glob("*.png"))
    if not frames:
        print(f"error: no stills in {_rel(take / 'frames')}", file=sys.stderr)
        return 2

    # The take's own snapshot, not the scene file as it stands now: these belong
    # to the spec that rendered them, which may since have moved on.
    sid = project.scene_id(json.loads((take / "scene.json").read_text(encoding="utf-8")))

    sheet = compare.grid(
        frames,
        target.dir_for("sheet") / f"{target.name('sheet', sid, target.next_version('sheet'))}.jpg",
        columns=4,
        labelled=True,
    )
    print(f"[sheet] {len(frames)} frames -> {_rel(sheet)}")

    preview = take / "preview.mp4"
    if preview.exists():
        out_dir = target.dir_for("preview")
        out_dir.mkdir(parents=True, exist_ok=True)
        kept = out_dir / f"{target.name('preview', sid, target.next_version('preview'))}.mp4"
        shutil.copyfile(preview, kept)
        print(f"[sheet] preview -> {_rel(kept)} ({kept.stat().st_size / 1e6:.1f} MB)")
    return 0


def _style_references(flags, generation, target, take):
    """The `@image1..N` look references, in tag order.

    Three sources, most explicit first: repeated `--style` flags, the merged
    spec's `generation.style_references`, and finally a `styleframe.png` sitting
    in the take. The spec's list is the one that matters -- a look that lives in
    a flag is a look nobody can reproduce, and the run that fixed the NYC shot
    was unrepeatable for exactly that reason.

    Spec paths resolve against the shot directory, not the working directory, so
    a shot carries its references with it.
    """
    if flags:
        paths = [Path(f) for f in flags]
    elif generation.get("style_references"):
        base = target.scene_path.parent
        paths = [(base / ref).resolve() for ref in generation["style_references"]]
    else:
        fallback = take / "styleframe.png"
        return [fallback] if fallback.exists() else []

    missing = [p for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "style reference not found: " + ", ".join(str(_rel(p)) for p in missing)
        )
    return paths


def cmd_generate(args):
    scene, target = _load(args.scene)
    generation = scene.get("generation")
    if not generation:
        print("error: scene has no 'generation' block", file=sys.stderr)
        return 2

    # `all` has no --take: it always generates from the take it just rendered.
    take = runs.resolve_take(target.out_parts, getattr(args, "take", None))
    preview = take / "preview.mp4"
    if not preview.exists():
        print(f"error: no blockout at {_rel(preview)} -- run `render` first", file=sys.stderr)
        return 2

    # Overrides let you probe cheaply without editing the scene, then rerun at
    # the scene's own settings once the shot is right.
    if args.resolution:
        generation = {**generation, "resolution": args.resolution}
    model = args.model or generation.get("model")

    try:
        style_images = _style_references(args.style, generation, target, take)
    except FileNotFoundError as missing:
        print(f"error: {missing}", file=sys.stderr)
        return 2

    # Checked again here, not only in `check`: --style can change the count out
    # from under a verbatim prompt, and this is the last free moment.
    unbound = unbound_image_tags(generation.get("full_prompt") or "", len(style_images))
    if unbound:
        named = ", ".join(f"Image {n}" for n in unbound)
        print(
            f"error: the prompt names {named}, but {len(style_images)} style "
            "reference(s) are attached",
            file=sys.stderr,
        )
        return 2

    provider = get_provider(args.provider, model=model)
    resolved_model = getattr(provider, "task_type", None) or getattr(provider, "model", "default")
    out_dir = runs.new_generation(take, resolved_model, generation.get("resolution", "720p"))

    runs.write_manifest(
        out_dir,
        scene=target.label,
        take=take.name,
        provider=provider.name,
        model=resolved_model,
        generation=generation,
        style_references=[str(_rel(p)) for p in style_images],
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    print(f"[generate] {_rel(out_dir)}")

    try:
        provider.generate(
            preview,
            generation,
            out_dir / "final.mp4",
            style_images=style_images,
            # Written the moment the task exists, not when it finishes: after
            # this point the run is the provider's, and the id is the only way
            # back to it. `fetch` recovers a paid generation with it; without
            # it, a run that dies mid-poll is unrecoverable and a failure a
            # week old cannot be looked up at all.
            on_task=lambda task_id: runs.write_manifest(out_dir, task_id=task_id),
        )
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
    scene, target = _load(args.scene)
    generation = scene.get("generation") or {}
    take = runs.resolve_take(target.out_parts, args.take)

    prompt = args.prompt or (generation.get("style_prompt") or generation.get("prompt"))
    if not prompt:
        # `full_prompt` is deliberately not a fallback: it carries the video
        # reference contract, which means nothing to an image model.
        print(
            "error: no look prompt -- pass --prompt, or give the scene a "
            "'style_prompt' or 'prompt' in its generation block",
            file=sys.stderr,
        )
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
    _, target = _load(args.scene)
    take = runs.resolve_take(target.out_parts, args.take)
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
    _, target = _load(args.scene)
    takes = runs.list_takes(target.out_parts)
    if not takes:
        print(f"no takes for {target.label} yet")
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
    out_dir = Path(out_dir).resolve()
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
    # Blender exits 0 whether or not it wrote anything, so check rather than
    # announce: this is the step that used to report success into the void.
    made = sorted(out_dir.glob("frame_*.png"))
    if not made:
        raise RuntimeError(f"extraction reported success but produced nothing in {out_dir}")
    print(f"[extract] {len(made)} stills -> {_rel(out_dir)}")
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
        ("audit", cmd_audit, "measure the camera move: speed, stalls, clearance"),
        ("render", cmd_render, "Blender -> a new take with preview.mp4"),
        ("generate", cmd_generate, "blockout -> final.mp4 via the video model"),
        ("all", cmd_all, "render, then generate"),
        ("takes", cmd_takes, "list takes and generations for a scene"),
        ("views", cmd_views, "top/front/side/3-quarter of the scene, camera path drawn"),
        ("frames", cmd_frames, "individual stills through the shot -> <shot>/frames/"),
        ("sheet", cmd_sheet, "keep a take with the shot: blockout to preview/, stills to artifacts/"),
        ("styleframe", cmd_styleframe, "GPT Image 2 -> <take>/styleframe.png"),
        ("compare", cmd_compare, "side-by-side sheet: blockout vs result"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument(
            "scene",
            help="path to a scene .json, or to a shot directory "
            "(which renders the scene its shot.json selects)",
        )
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
            p.add_argument(
                "--style",
                action="append",
                metavar="PATH",
                help="look reference image, repeatable -- first becomes @image1. "
                "Beats the scene's 'style_references', which beats <take>/styleframe.png.",
            )
        if name == "audit":
            p.add_argument(
                "--closest", type=int, default=8,
                help="how many objects to list, tightest first (default: 8)",
            )
            p.add_argument(
                "--min-clearance", type=float, default=0.0,
                help="fail if anything comes closer than this, in metres. "
                "A penetration always fails regardless.",
            )
        if name == "frames":
            p.add_argument(
                "--count", type=int, default=5,
                help="how many stills, evenly spaced, first and last included (default: 5)",
            )
        if name in ("generate", "styleframe", "compare", "sheet"):
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
    except project.ProjectError as exc:
        print(f"path error -- {exc}", file=sys.stderr)
        return 2
    except (RuntimeError, ValueError) as exc:
        print(f"error -- {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
