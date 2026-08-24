"""Print the exact prompts that would be sent, without calling anything.

    python tools/show_prompts.py scenes/demo_room.json

Both prompts are assembled from a scene's look text plus a fixed contract, and
neither is visible in the scene file. Being able to read them before paying is
worth more than guessing from the source.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_render import spec as spec_mod, styleframe  # noqa: E402
from ai_render.providers.base import build_reference_prompt  # noqa: E402

scene_path = sys.argv[1] if len(sys.argv) > 1 else "scenes/demo_room.json"
scene = spec_mod.load(scene_path)
generation = scene.get("generation") or {}
look = generation.get("prompt", "")

rule = "=" * 78


def section(title, body):
    print(f"\n{rule}\n{title}\n{rule}\n{body}")


section(
    "STYLEFRAME  ->  POST /v1/images/edits  (gpt-image-2, image[]=frame_01_.png)",
    f"{styleframe.EDIT_INSTRUCTION}\n\nMaterials and lighting to apply: {look}",
)

for style in (False, True):
    label = "with @image1 style frame" if style else "no style frame"
    section(
        f"GENERATE  ->  PiAPI omni_reference  ({label})",
        build_reference_prompt(look, generation.get("reference_mode", "video"), 1, style=style),
    )

print(f"\n{rule}")
print(json.dumps({k: v for k, v in generation.items() if k != "prompt"}, indent=2, ensure_ascii=False))
