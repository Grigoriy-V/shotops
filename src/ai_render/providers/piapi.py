"""Seedance via PiAPI (https://api.piapi.ai/api/v1/task).

This is the route that actually delivers structure control, and the reason is a
single field: `mode`. PiAPI exposes `text_to_video | first_last_frames |
omni_reference`, and only `omni_reference` attaches mixed-media references to
the generation. CometAPI's Seedance route has no such switch -- it accepts a
`video_urls` value and returns a perfectly good clip that owes nothing to the
reference. Verified by comparing blockout and result frame for frame: PiAPI in
omni_reference holds camera trajectory, blocking and shot scale; CometAPI did
not.

Reference tags are positional -- `@video1` is the first entry in `video_urls`.
The reference video still has to be reachable by URL, so `upload.py` publishes
the blockout to Supabase Storage and deletes it afterwards.

Billing note from the API's own logs: "billing includes input + output
duration". A 5s reference feeding a 5s output is charged as 10s, so the blockout
is not free here the way it is in Blender.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from .base import VideoProvider, build_reference_prompt, download

BASE_URL = os.environ.get("PIAPI_BASE_URL", "https://api.piapi.ai/api/v1")

# Mini is the iteration tier: cheapest, and PiAPI bills input + output duration,
# so the blockout is charged too. Move up to seedance-2 for finals.
FALLBACK_TASK_TYPE = "seedance-2-mini"

# Not enforced -- PiAPI adds task types faster than this list can track, and a
# closed whitelist would reject a working one. Listed for the error message and
# for `ai_render models`.
KNOWN_TASK_TYPES = [
    "seedance-2-mini",
    "seedance-2-fast",
    "seedance-2",
    "seedance-2-mini-less-restriction",
    "seedance-2-fast-less-restriction",
    "seedance-2-less-restriction",
]

RESOLUTIONS = {"480p", "720p", "1080p"}
ASPECT_RATIOS = {"21:9", "16:9", "4:3", "1:1", "3:4", "9:16", "auto"}
TERMINAL_OK = {"completed", "success", "succeeded"}
TERMINAL_BAD = {"failed", "error", "cancelled", "staged"}


class PiapiSeedance(VideoProvider):
    name = "piapi/seedance"

    def __init__(self, task_type=None, poll_interval=5.0, timeout=1800.0):
        # Precedence: explicit argument (CLI flag or scene field) beats the
        # environment, which beats the built-in iteration default.
        self.task_type = (
            task_type
            or os.environ.get("AI_RENDER_PIAPI_TASK_TYPE")
            or FALLBACK_TASK_TYPE
        )
        self.poll_interval = poll_interval
        self.timeout = timeout

    @staticmethod
    def _session():
        key = os.environ.get("PIAPI_KEY")
        if not key:
            raise RuntimeError(
                "PIAPI_KEY is not set.\n"
                "Copy .env.example to .env and put your PiAPI key in it (.env is gitignored)."
            )
        import requests

        session = requests.Session()
        session.headers.update({"X-API-Key": key, "Content-Type": "application/json"})
        return session

    def generate(self, reference_video, generation, out_path, style_images=None):
        mode = generation.get("reference_mode", "video")
        if mode != "video":
            raise ValueError(
                f"the PiAPI provider only implements reference_mode 'video', got {mode!r}. "
                "Stills-based modes exist on the CometAPI provider but are not exercised."
            )

        resolution = str(generation.get("resolution", "720p"))
        if resolution not in RESOLUTIONS:
            raise ValueError(f"resolution must be one of {sorted(RESOLUTIONS)}, got {resolution!r}")
        if resolution == "1080p" and self.task_type != "seedance-2":
            raise ValueError(
                f"1080p is only available on seedance-2, not {self.task_type!r}. "
                "Use --model seedance-2, or drop to 720p."
            )
        aspect_ratio = generation.get("aspect_ratio", "16:9")
        if aspect_ratio not in ASPECT_RATIOS:
            raise ValueError(f"aspect_ratio must be one of {sorted(ASPECT_RATIOS)}, got {aspect_ratio!r}")

        session = self._session()
        from ..upload import get_uploader

        uploader = get_uploader()
        url, cleanup = uploader.upload(Path(reference_video))
        image_urls = []
        cleanups = [cleanup]
        try:
            # Upload order is the tag order: the first file becomes @image1.
            # Nothing downstream can recover the mapping if this is shuffled,
            # so the list arrives ordered and is used as given.
            for image in style_images or []:
                style_url, style_cleanup = uploader.upload(Path(image))
                cleanups.append(style_cleanup)
                image_urls.append(style_url)

            payload = {
                "model": "seedance",
                "task_type": self.task_type,
                "input": {
                    "prompt": build_reference_prompt(
                        generation["prompt"], mode, 1, styles=len(image_urls)
                    ),
                    # The whole ballgame: without omni_reference the references
                    # are accepted and then ignored.
                    "mode": "omni_reference",
                    "duration": int(generation.get("duration", 5)),
                    "resolution": resolution,
                    "aspect_ratio": aspect_ratio,
                    "video_urls": [url],
                    "audio": bool(generation.get("generate_audio", False)),
                },
                "config": {"service_mode": "public"},
            }
            if image_urls:
                payload["input"]["image_urls"] = image_urls
            if "seed" in generation:
                payload["input"]["seed"] = int(generation["seed"])

            style_note = (
                f" + {len(image_urls)} style reference{'s' if len(image_urls) != 1 else ''}"
                if image_urls
                else ""
            )
            print(
                f"[generate] piapi/{self.task_type} -- {payload['input']['duration']}s "
                f"@ {resolution} {aspect_ratio}, mode=omni_reference{style_note}"
            )
            response = session.post(f"{BASE_URL}/task", json=payload, timeout=180)
            if response.status_code >= 400:
                raise RuntimeError(f"PiAPI {response.status_code}: {response.text[:800]}")

            body = response.json()
            data = body.get("data") or body
            task_id = data.get("task_id") or data.get("id")
            if not task_id:
                raise RuntimeError(f"no task id in response: {body!r}")

            video_url = self._poll(session, task_id)
        finally:
            for drop in cleanups:
                drop()

        out = download(video_url, out_path)
        print(f"[generate] ok -- {out} ({out.stat().st_size / 1e6:.1f} MB)")
        return out

    def fetch(self, task_id, out_path):
        """Download an already-finished task.

        Generation is the expensive half; delivery is the fragile half. When a
        download fails after the model has run, this recovers the result instead
        of paying to make it again.
        """
        url = self._poll(self._session(), task_id, first_delay=0.0)
        out = download(url, out_path)
        print(f"[fetch] ok -- {out} ({out.stat().st_size / 1e6:.1f} MB)")
        return out

    def _poll(self, session, task_id, first_delay=None):
        print(f"[generate] task {task_id} -- polling")
        deadline = time.time() + self.timeout
        delay = self.poll_interval if first_delay is None else first_delay
        last = None
        while time.time() < deadline:
            time.sleep(delay)
            delay = self.poll_interval
            response = session.get(f"{BASE_URL}/task/{task_id}", timeout=60)
            if response.status_code >= 400:
                raise RuntimeError(f"PiAPI poll {response.status_code}: {response.text[:400]}")
            data = response.json().get("data") or {}
            status = str(data.get("status", "")).lower()

            if status != last:
                print(f"[generate]   {status or 'unknown'}")
                last = status

            if status in TERMINAL_OK:
                url = (data.get("output") or {}).get("video")
                if not url:
                    raise RuntimeError(f"task completed but no video url: {data!r}")
                for line in data.get("logs") or []:
                    print(f"[generate]   {line}")
                return url
            if status in TERMINAL_BAD:
                error = data.get("error") or {}
                message = error.get("message") or error.get("raw_message") or data
                raise RuntimeError(f"task {status}: {message}")

        raise RuntimeError(f"task {task_id} did not finish within {self.timeout:.0f}s")
