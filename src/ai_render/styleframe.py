"""Turn one blockout frame into a style reference, with GPT Image 2 via CometAPI.

ByteDance's white-model workflow uses two references, not one:

    保持 @视频1 中的镜头运动 ... 不变，以 @图片1 作为材质、光照、色彩和整体氛围参考

The blockout owns everything spatial. A still owns material, lighting, colour
and mood. The catch is that the still has to agree with the blockout, or the two
references pull against each other -- which is what a text-to-image style frame
does, since it invents its own composition.

So the style frame is an **edit of the blockout's own frame**: same camera, same
framing, same object positions, with only surfaces and light replaced. The video
model then gets a look reference anchored to the exact geometry it is being
asked to render.

`generate_from_frame` is the method to use. `generate_from_text` remains for
exploring a look before a blockout exists, but it should not be fed to a shot.

Note on `input_fidelity`: gpt-image-2 processes inputs at high fidelity always
and **rejects the parameter**, so it is deliberately not sent.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

BASE_URL = os.environ.get("COMETAPI_BASE_URL", "https://api.cometapi.com/v1")
DEFAULT_MODEL = os.environ.get("AI_RENDER_IMAGE_MODEL", "gpt-image-2")

# gpt-image-2's size list has no 1K-class 16:9 entry. For edits, "auto" keeps the
# input frame's proportions, which is exactly what we want -- the style frame
# must stay registered with the blockout.
SIZE_BY_RATIO = {
    "16:9": "1536x1024",
    "21:9": "1536x1024",
    "4:3": "1536x1024",
    "3:2": "1536x1024",
    "1:1": "1024x1024",
    "9:16": "1024x1536",
    "3:4": "1024x1536",
}

# The whole job of this instruction is to stop the model reframing. It is
# allowed to touch surfaces and light, and nothing else.
EDIT_INSTRUCTION = (
    "This image is an untextured grey 3D blockout frame. Re-render it as a "
    "photorealistic live-action still. Keep the composition absolutely "
    "unchanged: identical camera angle, focal length, framing and perspective; "
    "identical object positions, proportions, silhouettes and edges; identical "
    "wall, floor and ceiling geometry. Do not move, add, remove, resize or "
    "recompose anything. Change only surface materials and lighting."
)

TEXT_INSTRUCTION = (
    "A single cinematic still frame for look development. Show materials, "
    "lighting quality, colour and atmosphere clearly. No text, no watermark."
)


def default_size(aspect_ratio):
    return SIZE_BY_RATIO.get(aspect_ratio, "1536x1024")


def _key():
    key = os.environ.get("COMETAPI_KEY")
    if not key:
        raise RuntimeError(
            "COMETAPI_KEY is not set -- style frames use GPT Image 2 through CometAPI.\n"
            "Add it to .env (.env is gitignored)."
        )
    return key


def _save(response, out_path):
    if response.status_code >= 400:
        raise RuntimeError(f"CometAPI images {response.status_code}: {response.text[:800]}")
    data = (response.json().get("data") or [{}])[0]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # The endpoint returns either inline base64 or a URL depending on the model
    # and the gateway; handle both rather than guessing.
    if data.get("b64_json"):
        out_path.write_bytes(base64.b64decode(data["b64_json"]))
    elif data.get("url"):
        from .providers.base import download

        download(data["url"], out_path)
    else:
        raise RuntimeError(f"no image in response: {response.text[:400]}")

    print(f"[styleframe] ok -- {out_path} ({out_path.stat().st_size / 1e6:.2f} MB)")
    return out_path


def generate_from_frame(frame_path, prompt, out_path, size="auto", model=None, quality="high"):
    """Restyle one blockout frame, preserving its composition."""
    import requests

    frame_path = Path(frame_path)
    if not frame_path.exists():
        raise RuntimeError(f"no blockout frame at {frame_path} -- run `render` first")
    model = model or DEFAULT_MODEL

    data = {
        "model": model,
        "prompt": f"{EDIT_INSTRUCTION}\n\nMaterials and lighting to apply: {prompt}",
        "quality": quality,
        "n": "1",
    }
    if size and size != "auto":
        data["size"] = size

    print(f"[styleframe] {model} edit of {frame_path.name} ({quality}, size={size})")
    with open(frame_path, "rb") as handle:
        response = requests.post(
            f"{BASE_URL}/images/edits",
            headers={"Authorization": f"Bearer {_key()}"},
            data=data,
            files=[("image[]", (frame_path.name, handle, "image/png"))],
            timeout=600,
        )
    return _save(response, out_path)


def generate_from_text(prompt, out_path, size=None, model=None, quality="high"):
    """Pure text-to-image. For look exploration only -- it invents its own
    composition, which fights the blockout if fed to a shot."""
    import requests

    model = model or DEFAULT_MODEL
    payload = {
        "model": model,
        "prompt": f"{TEXT_INSTRUCTION}\n\n{prompt}",
        "size": size or "1536x1024",
        "quality": quality,
        "n": 1,
    }
    print(f"[styleframe] {model} text-to-image @ {payload['size']} ({quality})")
    response = requests.post(
        f"{BASE_URL}/images/generations",
        headers={"Authorization": f"Bearer {_key()}"},
        json=payload,
        timeout=600,
    )
    return _save(response, out_path)
