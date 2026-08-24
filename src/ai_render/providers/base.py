"""Provider interface.

The video model is the fastest-moving piece of this stack, so it sits behind a
one-method interface. Swapping Seedance for Runway/Kling/Wan means adding a file
here, not touching the scene layer.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path


# What the blockout owns, and what must not leak out of it. Taken from
# ByteDance's white-model template, which pins the spatial half of the shot
# before it says a word about look.
KEEP = (
    "camera motion, duration, composition, shot scale, spatial relationships, "
    "object positions, model structure and motion trajectory"
)
DROP = "grey untextured material, flat shading, background, lighting and colour"


def build_reference_prompt(prompt, mode, count, style=False):
    """Prepend the reference contract to the look prompt.

    Two things earned their place here the expensive way. The kept properties
    are enumerated rather than gestured at -- "use it for camera and framing"
    is too vague to bind. And the blockout's own appearance is excluded
    explicitly, or the model reads flat grey as art direction.

    With `style=True` the contract splits the shot in two, following
    ByteDance's own white-model template: the blockout owns everything spatial,
    a still owns material, lighting, colour and mood. Without a style still
    those properties are told to no one, and the model picks them itself.

    The `@video1` / `@image1` tags are positional: they refer to upload order in
    `video_urls` / `image_urls`, not to any name in the scene spec.
    """
    if mode == "video":
        ref = "@video1"
        preamble = (
            f"Keep the {KEEP} of {ref} exactly unchanged. "
            f"{ref} is an untextured grey 3D blockout, not the intended look: "
            f"do not copy its {DROP}. "
        )
        if style:
            preamble += (
                "Use @image1 as the reference for material, lighting, colour, reflection "
                f"and overall atmosphere. Replace the white-model surfaces of {ref} with "
                "real materials matching @image1. Take no camera, framing or object "
                "placement from @image1 -- those come from "
                f"{ref} alone."
            )
        else:
            preamble += (
                f"Replace the white-model surfaces of {ref} with the real materials "
                "described below."
            )
    elif mode == "first":
        ref = "@image1"
        preamble = (
            f"Keep the composition, shot scale, spatial relationships and object positions "
            f"of {ref} unchanged. {ref} is an untextured grey 3D blockout, not the intended "
            f"look: do not copy its {DROP}."
        )
    else:
        tags = ", ".join(f"@image{i}" for i in range(1, count + 1))
        preamble = (
            f"{tags} are consecutive frames of one continuous camera move, in upload order, "
            f"sampled from an untextured grey 3D blockout. Keep the {KEEP} they describe "
            f"exactly unchanged. Do not copy their {DROP}."
        )
    return f"{preamble}\n\nRender it as: {prompt}"


class VideoProvider:
    name = "base"

    def generate(
        self,
        reference_video: Path,
        generation: dict,
        out_path: Path,
        style_image: Path | None = None,
    ) -> Path:
        """Turn a grey blockout clip into the finished shot.

        `style_image` is the optional `@image1` look reference. Providers that
        cannot attach one must say so rather than silently dropping it -- a shot
        that quietly ignores your art direction is worse than one that refuses.
        """
        raise NotImplementedError


def download(url, out_path):
    """Fetch a finished clip.

    Uses requests with an explicit User-Agent: some result CDNs return 403 to
    urllib's default agent, and by the time you are downloading, the generation
    is already paid for -- losing it to a header is not acceptable.
    """
    import requests

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "ai_render/0.1 (+https://github.com/)", "Accept": "*/*"}
    with requests.get(url, headers=headers, stream=True, timeout=300) as response:
        response.raise_for_status()
        with open(out_path, "wb") as handle:
            for chunk in response.iter_content(1 << 16):
                handle.write(chunk)
    return out_path


def get_provider(name, model=None):
    """`model` names the variant within a provider -- PiAPI task type, CometAPI
    model id. None keeps the provider's own default."""
    if name in ("piapi", "pi"):
        from .piapi import PiapiSeedance

        return PiapiSeedance(task_type=model)
    if name in ("comet", "cometapi", "seedance"):
        from .cometapi import CometSeedance

        return CometSeedance(model=model)
    raise ValueError(f"unknown provider {name!r} (available: piapi, comet)")
