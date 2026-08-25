"""Provider interface.

The video model is the fastest-moving piece of this stack, so it sits behind a
one-method interface. Swapping Seedance for Runway/Kling/Wan means adding a file
here, not touching the scene layer.
"""

from __future__ import annotations

import re
from pathlib import Path


# What the blockout owns, and what must not leak out of it. Taken from
# ByteDance's white-model template, which pins the spatial half of the shot
# before it says a word about look.
KEEP = (
    "camera motion, duration, composition, shot scale, spatial relationships, "
    "object positions, model structure and motion trajectory"
)
DROP = "grey untextured material, flat shading, background, lighting and colour"


def _tags(count):
    """`@image1`, `@image1 and @image2`, `@image1, @image2 and @image3`."""
    names = [f"@image{i}" for i in range(1, count + 1)]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def build_reference_prompt(prompt, mode, count, styles=0):
    """Prepend the reference contract to the look prompt.

    Two things earned their place here the expensive way. The kept properties
    are enumerated rather than gestured at -- "use it for camera and framing"
    is too vague to bind. And the blockout's own appearance is excluded
    explicitly, or the model reads flat grey as art direction.

    `styles` is how many look references are attached. With one or more, the
    contract splits the shot in two: the blockout owns everything spatial, the
    images own material, lighting, colour and mood. Without any, those
    properties are told to no one and the model picks them itself.

    The wording of the split is not invented here. It is what generation 003
    sent by hand, generalised to N images -- and the sentence that did the work
    is **appearance is determined solely by the images**. Saying only "do not
    copy the blockout's colour" leaves the model free to read a red box as
    art direction, which is exactly what generation 002 did.

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
        if styles:
            tags = _tags(styles)
            preamble += (
                f"{ref} is a guide for movement and composition only. Do not rely on "
                f"the appearance of {ref} or of the objects in it. Appearance is "
                f"determined solely by {tags}: use {'them' if styles > 1 else 'it'} as "
                "the reference for material, lighting, colour, reflection and overall "
                f"atmosphere. Take no camera, framing or object placement from "
                f"{'them' if styles > 1 else 'it'} -- those come from {ref} alone."
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
        tags = _tags(count)
        preamble = (
            f"{tags} are consecutive frames of one continuous camera move, in upload order, "
            f"sampled from an untextured grey 3D blockout. Keep the {KEEP} they describe "
            f"exactly unchanged. Do not copy their {DROP}."
        )
    return f"{preamble}\n\nRender it as: {prompt}"


def resolve_prompt(generation, mode, count, styles=0):
    """What actually gets sent, from the scene's own fields.

    `full_prompt` wins and is sent byte for byte, contract and all. That field
    exists because a prompt someone tested is worth more than a prompt this
    module can assemble: the NYC shot's prompt was written by hand, run, and
    judged good, and generating a near-miss of it would be substituting an
    untested string for a tested one.

    `prompt` is the other half of the deal -- the look only, with the contract
    prepended here. It stays the default because most scenes have no tested
    prompt to defend.

    Lives in one place so the two providers cannot drift on which field wins.
    """
    verbatim = generation.get("full_prompt")
    if verbatim:
        return verbatim
    return build_reference_prompt(generation["prompt"], mode, count, styles=styles)


def unbound_image_tags(prompt, available):
    """Image numbers the prompt names that no reference will be uploaded for.

    A prompt saying "Image 1, Image 2, and Image 3" with two references
    attached is a prompt talking about something that will not be there. Cheap
    to catch, and the alternative is finding out from the result.
    """
    referenced = {int(n) for n in re.findall(r"@?[Ii]mage\s*(\d+)", prompt)}
    return sorted(n for n in referenced if n > available)


class VideoProvider:
    name = "base"

    def generate(
        self,
        reference_video: Path,
        generation: dict,
        out_path: Path,
        style_images: list[Path] | None = None,
    ) -> Path:
        """Turn a grey blockout clip into the finished shot.

        `style_images` are the optional `@image1..N` look references, in the
        order they should be tagged. Providers that cannot attach them must say
        so rather than silently dropping them -- a shot that quietly ignores
        your art direction is worse than one that refuses.
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
