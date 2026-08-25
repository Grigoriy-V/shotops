"""Seedance via CometAPI (https://api.cometapi.com/v1/videos).

NOT the recommended route -- see `piapi.py`, which is the default. This one is
kept because it works and because its limits are now known: its Seedance route
has no `mode` switch, so references are accepted and then ignored. Two live runs
produced good-looking clips that owed nothing to the blockout's camera.

A caveat that shapes this whole file: CometAPI's Seedance route documents
`input_reference` as accepting **images only** (JPEG/PNG/WebP). The underlying
model has white-model video control, but the gateway does not document a way to
hand it a video.

`video` mode -- posting the blockout mp4 as input_reference -- is therefore the
only mode this project actually pursues. The point of the pipeline is genuine
video-to-video: the model reading trajectory, framing and timing off the
blockout. Degrading to stills would produce a plausible-looking clip that no
longer honours the camera move, which is worse than a clear failure.

So there is no automatic fallback. If the gateway rejects video references, the
fix is a different provider route -- CometAPI documents real video-to-video on
Runway and Kling -- not a quieter version of this one.

`frames` and `first` remain implemented but unexercised, for the day a
storyboard-shaped reference is genuinely wanted.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from .base import VideoProvider, download, resolve_prompt

BASE_URL = os.environ.get("COMETAPI_BASE_URL", "https://api.cometapi.com/v1")
DEFAULT_MODEL = os.environ.get("AI_RENDER_COMET_MODEL", "seedance-2-5")

# CometAPI takes exact WxH, not a tier name, and rejects anything off-list.
SIZES = {
    "720p": {
        "21:9": "1470x630", "16:9": "1280x720", "4:3": "1112x834",
        "1:1": "960x960", "3:4": "834x1112", "9:16": "720x1280",
    },
    "480p": {
        "21:9": "992x432", "16:9": "854x480", "4:3": "752x560",
        "1:1": "640x640", "3:4": "560x752", "9:16": "480x854",
    },
}

MIME = {".mp4": "video/mp4", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


def resolve_size(generation):
    tier = str(generation.get("resolution", "720p"))
    ratio = generation.get("aspect_ratio", "16:9")
    if "x" in tier:  # caller gave an explicit WxH; trust it
        return tier
    if tier not in SIZES:
        raise ValueError(f"resolution must be one of {sorted(SIZES)} or an explicit WxH, got {tier!r}")
    if ratio not in SIZES[tier]:
        raise ValueError(f"aspect_ratio {ratio!r} not available at {tier} (have: {sorted(SIZES[tier])})")
    return SIZES[tier][ratio]


class CometSeedance(VideoProvider):
    name = "cometapi/seedance"

    def __init__(self, model=None, poll_interval=5.0, timeout=1800.0):
        self.model = model or DEFAULT_MODEL
        self.poll_interval = poll_interval
        self.timeout = timeout

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _session():
        key = os.environ.get("COMETAPI_KEY")
        if not key:
            raise RuntimeError(
                "COMETAPI_KEY is not set.\n"
                "Copy .env.example to .env and put your CometAPI key in it "
                "(.env is gitignored)."
            )
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests is missing -- run: pip install -r requirements.txt") from exc
        session = requests.Session()
        session.headers["Authorization"] = f"Bearer {key}"
        return session

    @staticmethod
    def _reference_files(reference_video, mode):
        """Build the multipart file list for the chosen reference mode."""
        reference_video = Path(reference_video)
        if mode == "video":
            return [reference_video]
        frames_dir = reference_video.parent / "frames"
        frames = sorted(frames_dir.glob("*.png"))
        if not frames:
            raise RuntimeError(
                f"reference_mode={mode!r} needs stills, but {frames_dir} is empty.\n"
                "Re-run `render` -- it writes the blockout mp4 and the sampled frames together."
            )
        return frames[:1] if mode == "first" else frames[:30]

    # ------------------------------------------------------------------ main

    def generate(self, reference_video, generation, out_path, style_images=None, on_task=None):
        import requests

        if style_images:
            raise ValueError(
                "the CometAPI provider cannot attach style references -- its Seedance "
                "route has no omni_reference mode. Use --provider piapi."
            )
        mode = generation.get("reference_mode", "video")
        if mode not in ("video", "frames", "first"):
            raise ValueError(f"reference_mode must be video|frames|first, got {mode!r}")

        session = self._session()
        refs = self._reference_files(reference_video, mode)
        size = resolve_size(generation)
        seconds = str(int(generation.get("duration", 5)))

        data = {
            "prompt": resolve_prompt(generation, mode, len(refs)),
            "model": self.model,
            "seconds": seconds,
            "size": size,
        }
        if "seed" in generation:
            data["seed"] = str(int(generation["seed"]))

        print(f"[generate] {self.model} -- {seconds}s @ {size}, mode={mode}, {len(refs)} reference(s)")

        if mode == "video":
            # Video references are URL-only: the gateway happily accepts an
            # uploaded mp4 but files it under image_urls, and the backend then
            # rejects it. So publish the blockout and pass video_urls instead.
            from ..upload import get_uploader

            url, cleanup = get_uploader().upload(refs[0])
            try:
                response = session.post(
                    f"{BASE_URL}/videos",
                    data={**data, "video_urls": url},
                    timeout=180,
                )
                task = self._start(response, mode)
                if on_task:
                    on_task(task)
                video_url = self._poll(session, task)
            finally:
                cleanup()
            out = download(video_url, out_path)
            print(f"[generate] ok -- {out} ({out.stat().st_size / 1e6:.1f} MB)")
            return out

        handles = []
        try:
            files = []
            for ref in refs:
                handle = open(ref, "rb")
                handles.append(handle)
                files.append(("input_reference", (ref.name, handle, MIME.get(ref.suffix.lower(), "application/octet-stream"))))

            response = session.post(f"{BASE_URL}/videos", data=data, files=files, timeout=180)
        finally:
            for handle in handles:
                handle.close()

        task = self._start(response, mode)
        if on_task:
            on_task(task)
        url = self._poll(session, task)
        out = download(url, out_path)
        print(f"[generate] ok -- {out} ({out.stat().st_size / 1e6:.1f} MB)")
        return out

    @staticmethod
    def _start(response, mode):
        """Check the create-task response and pull out the task id."""
        if response.status_code >= 400:
            hint = ""
            if mode == "video" and response.status_code in (400, 415, 422):
                hint = (
                    "\n\nThis looks like the gateway refusing the video reference itself.\n"
                    "That is a provider problem, not a scene problem -- CometAPI documents real "
                    "video-to-video on its Runway and Kling routes, which would be a new file in "
                    "providers/.\nDo not switch to a stills-based reference_mode to get past it: "
                    "that returns a clip which ignores the camera move."
                )
            raise RuntimeError(f"CometAPI {response.status_code}: {response.text[:800]}{hint}")

        task = response.json()
        task_id = task.get("id") or task.get("task_id")
        if not task_id:
            raise RuntimeError(f"no task id in response: {task!r}")
        return task_id

    def _poll(self, session, task_id):
        print(f"[generate] task {task_id} -- polling")
        deadline = time.time() + self.timeout
        last = None
        while time.time() < deadline:
            time.sleep(self.poll_interval)
            response = session.get(f"{BASE_URL}/videos/{task_id}", timeout=60)
            if response.status_code >= 400:
                raise RuntimeError(f"CometAPI poll {response.status_code}: {response.text[:400]}")
            body = response.json()
            status = str(body.get("status", "")).lower()

            note = f"{status} {body.get('progress', '')}".strip()
            if note != last:
                print(f"[generate]   {note}")
                last = note

            if status in ("completed", "succeeded", "success"):
                url = self._extract_url(body)
                if not url:
                    raise RuntimeError(f"task completed but no video url: {body!r}")
                return url
            if status in ("failed", "error", "cancelled"):
                raise RuntimeError(f"task {status}: {body.get('error') or body}")

        raise RuntimeError(f"task {task_id} did not finish within {self.timeout:.0f}s")

    @staticmethod
    def _extract_url(body):
        """Gateways disagree about where the URL lives; check the usual spots."""
        for key in ("video_url", "url", "output_url"):
            if isinstance(body.get(key), str):
                return body[key]
        for key in ("video", "output", "data", "result"):
            nested = body.get(key)
            if isinstance(nested, str):
                return nested
            if isinstance(nested, dict):
                for inner in ("url", "video_url"):
                    if isinstance(nested.get(inner), str):
                        return nested[inner]
            if isinstance(nested, list) and nested:
                first = nested[0]
                if isinstance(first, str):
                    return first
                if isinstance(first, dict):
                    for inner in ("url", "video_url"):
                        if isinstance(first.get(inner), str):
                            return first[inner]
        return None
