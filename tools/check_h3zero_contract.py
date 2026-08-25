"""Run a scene's real H3Zero payload through the deployment's real validators.

Nothing is sent anywhere and no GPU is allocated. This imports the gateway's own
``parse_config``, ``_validate_reference_declarations`` and
``_assign_reference_tags`` out of the local H3Zero checkout, feeds them exactly
what ``providers/h3zero.py`` would post, and checks that the tags they assign are
the tags the prompt names.

That last check is the reason this exists. A shifted tag is the one failure that
costs a whole generation while looking, in every log, like a success: every file
uploaded, every reference accepted, and each name bound to the wrong picture.

Requires the gitignored checkout described in docs/h3zero-modal.md.

    python tools/check_h3zero_contract.py projects/nyc/.../street_a.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = ROOT / ".tools" / "h3zero"
sys.path.insert(0, str(ROOT / "src"))


def _gateway():
    if not (CHECKOUT / "modal_services" / "gateway.py").is_file():
        raise SystemExit(
            f"the H3Zero checkout is not at {CHECKOUT}.\n"
            "See docs/h3zero-modal.md for the pinned clone and its patches."
        )
    sys.path.insert(0, str(CHECKOUT))
    from modal_services import gateway

    return gateway


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", type=Path)
    parser.add_argument("--checkpoint")
    parser.add_argument("--lora")
    parser.add_argument("--seed")
    parser.add_argument("--resolution")
    args = parser.parse_args()

    gateway = _gateway()
    from ai_render.cli import _load, _style_references
    from ai_render.providers.h3zero import H3Zero, expected_tags, verify_reference_tags

    scene, target = _load(args.scene)
    generation = dict(scene.get("generation") or {})
    if args.resolution:
        generation["resolution"] = args.resolution
    base = target.scene_path.parent
    styles = [(base / name).resolve() for name in generation.get("style_references", [])]

    provider = H3Zero(
        checkpoint=args.checkpoint, accelerator=args.lora, seed=args.seed
    )
    (
        _config, prompt, styles, profile, duration, width, height, resolution,
        checkpoint, accelerator, seed,
    ) = provider._settings(generation, styles)

    references = [
        {"id": "blockout", "kind": "video", "field": "reference_0", "use_audio": False}
    ]
    for index in range(1, len(styles) + 1):
        references.append(
            {"id": f"look_{index}", "kind": "image", "field": f"reference_{index}"}
        )
    request_config = {
        "mode": "references",
        "width": width,
        "height": height,
        "resolution": resolution,
        "duration_seconds": duration,
        "sampling_profile": profile,
        "reference_checkpoint": checkpoint,
        "references": references,
    }
    if accelerator is not None:
        request_config["accelerator_lora"] = accelerator
    if seed is not None:
        request_config["seed"] = seed

    parsed = gateway.parse_config(prompt, json.dumps(request_config))
    print(f"accepted : {duration}s @ {resolution} {width}x{height}, profile {parsed['sampling_profile']}")
    print(f"sampling : {parsed['steps']} steps, {parsed['sampler']} / {parsed['scheduler']}")
    print(
        f"seed     : {parsed['seed']}" if parsed["seed"] is not None
        else "seed     : random -- the worker will draw one per job"
    )

    # Build the graph the worker would build and read the checkpoint back off
    # it, rather than trusting that the field arrived where it was aimed.
    from minimax_h3.workflow import build_reference_workflow

    slots: dict[str, int] = {}
    staged = []
    for index, entry in enumerate(references):
        kind = entry["kind"]
        slot = slots.get(kind, 0)
        slots[kind] = slot + 1
        staged.append({**entry, "slot": slot, "local_filename": f"staged-{index}"})

    workflow = build_reference_workflow(
        prompt=prompt,
        width=width,
        height=height,
        duration_seconds=duration,
        # The worker substitutes a random seed of its own when the request has
        # none, so 0 here stands only for "whatever it draws".
        seed=parsed["seed"] if parsed["seed"] is not None else 0,
        sampling_profile=parsed["sampling_profile"],
        reference_checkpoint=parsed["reference_checkpoint"],
        accelerator_lora=parsed["accelerator_lora"],
        resolution=parsed["resolution"],
        references=staged,
    )
    noise = workflow["noise"]["inputs"]["noise_seed"]
    if parsed["seed"] is not None and noise != parsed["seed"]:
        raise SystemExit(f"error: seed {parsed['seed']} reached the graph as {noise}")
    accelerator = (workflow.get("turbo_lora") or {}).get("inputs", {}).get("lora_name")
    print(
        f"checkpoint: {parsed['reference_checkpoint']} "
        f"-> {workflow['model']['inputs']['unet_name']}"
    )
    print(f"accelerator: {accelerator or 'none (samples the checkpoint directly)'}")

    if (width, height) not in gateway.NATIVE_CANVASES[resolution]:
        raise SystemExit(f"error: {width}x{height} is not a native {resolution} preset")
    print(f"canvas   : a native {resolution} preset")

    declarations = [dict(entry) for entry in parsed["references"]]
    gateway._validate_reference_declarations(declarations)
    gateway._assign_reference_tags(declarations)

    # Raises if the service would number them differently from the provider.
    for reference_id, tag in verify_reference_tags(
        {"request": {"references": declarations}}, len(styles)
    ):
        print(f"  {tag} <- {reference_id}")

    unnamed = [tag for tag in expected_tags(len(styles)) if tag not in prompt]
    if unnamed:
        raise SystemExit(
            f"error: {', '.join(unnamed)} would be attached but the prompt never names it"
        )
    print("prompt   : every attached reference is named in it")
    print("\nok -- the payload would be accepted and tagged as the prompt assumes")


if __name__ == "__main__":
    main()
