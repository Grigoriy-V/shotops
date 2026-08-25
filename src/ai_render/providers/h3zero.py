"""MiniMax H3 through a self-hosted H3Zero Modal endpoint.

H3Zero accepts the blockout and look references directly as multipart files, so
this provider deliberately bypasses ``upload.py``.  The endpoint should be
deployed with Modal proxy authentication.  Its dedicated ``Modal-Key`` and
``Modal-Secret`` values live in the gitignored ``.env`` and are sent as request
headers.  A separate bearer token is also supported for non-Modal gateways.

H3's reference grammar is not Seedance's grammar.  Prompts here live under
``generation.h3zero.full_prompt`` and use case-sensitive ``<Video 1>`` and
``<Picture 1>`` tags.  The provider never rewrites or silently reuses the
top-level, already-tested Seedance prompt.
"""

from __future__ import annotations

from contextlib import ExitStack
import json
import mimetypes
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from .base import VideoProvider


PROFILES = {"turbo_4", "turbo_8", "spectrum", "base"}
DIMENSIONS = {"16:9": (864, 480), "9:16": (480, 864)}
TERMINAL_BAD = {"failed", "expired", "cancelled"}


def _h3_config(generation):
    config = generation.get("h3zero")
    if not isinstance(config, dict):
        raise ValueError(
            "generation.h3zero must be an object with its own full_prompt; "
            "H3 reference tags differ from Seedance tags"
        )
    return config


def validate_h3_prompt(prompt, pictures):
    """Reject unbound or incorrectly-cased H3 reference tags before upload."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("generation.h3zero.full_prompt must be a non-empty string")

    candidates = re.findall(r"<\s*(?:picture|video|audio)\s+\d+\s*>", prompt, flags=re.I)
    invalid = [tag for tag in candidates if not re.fullmatch(r"<(?:Picture|Video|Audio) \d+>", tag)]
    if invalid:
        raise ValueError(
            "H3 reference tags are case-sensitive; use <Video 1>, <Picture 1>, or <Audio 1>"
        )

    videos = {int(value) for value in re.findall(r"<Video (\d+)>", prompt)}
    images = {int(value) for value in re.findall(r"<Picture (\d+)>", prompt)}
    audios = {int(value) for value in re.findall(r"<Audio (\d+)>", prompt)}
    if 1 not in videos:
        raise ValueError("generation.h3zero.full_prompt must bind the blockout as <Video 1>")
    if any(number != 1 for number in videos):
        raise ValueError("only one video is attached, so only <Video 1> is available")
    if any(number < 1 for number in images):
        raise ValueError("H3 picture numbering starts at <Picture 1>")
    unbound = sorted(number for number in images if number > pictures)
    if unbound:
        named = ", ".join(f"<Picture {number}>" for number in unbound)
        raise ValueError(f"the H3 prompt names {named}, but only {pictures} picture(s) are attached")
    if audios:
        raise ValueError("no standalone audio reference is attached, so <Audio N> tags are unavailable")


def _mime(path):
    value = mimetypes.guess_type(str(path))[0]
    if value not in {"video/mp4", "video/quicktime", "video/webm", "image/png", "image/jpeg", "image/webp"}:
        raise ValueError(f"H3Zero does not accept this reference type: {path}")
    return value


class H3Zero(VideoProvider):
    name = "h3zero/minimax-h3"
    uploader = "direct-multipart"
    resolution = "480p"

    def __init__(self, sampling_profile=None, poll_interval=5.0, timeout=1800.0):
        self.sampling_profile = (
            sampling_profile
            or os.environ.get("AI_RENDER_H3ZERO_PROFILE")
        )
        self.model = self.sampling_profile or "turbo_4"
        self.poll_interval = poll_interval
        self.timeout = timeout

    @property
    def base_url(self):
        value = os.environ.get("AI_RENDER_H3ZERO_URL", "").rstrip("/")
        if not value:
            raise RuntimeError(
                "AI_RENDER_H3ZERO_URL is not set. Deploy H3Zero first, then put its Modal URL in .env."
            )
        return value

    @staticmethod
    def _auth_mode():
        explicit = os.environ.get("AI_RENDER_H3ZERO_AUTH")
        if explicit:
            mode = explicit.lower()
        elif os.environ.get("AI_RENDER_H3ZERO_MODAL_KEY") or os.environ.get(
            "AI_RENDER_H3ZERO_MODAL_SECRET"
        ):
            mode = "modal-proxy"
        elif os.environ.get("AI_RENDER_H3ZERO_TOKEN"):
            mode = "bearer"
        else:
            mode = "modal-proxy"
        if mode not in {"modal-proxy", "modal-cli", "bearer", "none"}:
            raise ValueError(
                "AI_RENDER_H3ZERO_AUTH must be modal-proxy, modal-cli, bearer, or none"
            )
        return mode

    @classmethod
    def _auth_headers(cls):
        mode = cls._auth_mode()
        if mode == "modal-proxy":
            key = os.environ.get("AI_RENDER_H3ZERO_MODAL_KEY")
            secret = os.environ.get("AI_RENDER_H3ZERO_MODAL_SECRET")
            if not key or not secret:
                raise RuntimeError(
                    "AI_RENDER_H3ZERO_MODAL_KEY and AI_RENDER_H3ZERO_MODAL_SECRET "
                    "are required for Modal proxy auth"
                )
            return {"Modal-Key": key, "Modal-Secret": secret}
        if mode == "bearer":
            token = os.environ.get("AI_RENDER_H3ZERO_TOKEN")
            if not token:
                raise RuntimeError("AI_RENDER_H3ZERO_TOKEN is required for bearer auth")
            return {"Authorization": f"Bearer {token}"}
        return {}

    @staticmethod
    def _modal_python():
        configured = os.environ.get("AI_RENDER_H3ZERO_MODAL_PYTHON")
        if configured:
            return Path(configured)
        bundled = Path(__file__).resolve().parents[3] / ".tools" / "h3zero" / ".venv" / "Scripts" / "python.exe"
        if bundled.exists():
            return bundled
        return Path(sys.executable)

    def _modal_curl(self, method, path, form=None, files=None, out_path=None):
        command = [
            str(self._modal_python()), "-m", "modal", "curl", "-sS", "-L",
            "-X", method, f"{self.base_url}{path}",
        ]
        for key, value in (form or {}).items():
            command.extend(["--form-string", f"{key}={value}"])
        for field, file_path, media_type in files or []:
            command.extend(["-F", f"{field}=@{Path(file_path).resolve()};type={media_type}"])
        if out_path is not None:
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
            command.extend(["-o", str(Path(out_path).resolve())])
        command.extend(["-w", "\n%{http_code}"])
        completed = subprocess.run(command, capture_output=True, check=False)
        if completed.returncode:
            error = completed.stderr.decode("utf-8", errors="replace")[-800:]
            raise RuntimeError(f"modal curl failed ({completed.returncode}): {error}")
        output = completed.stdout.decode("utf-8", errors="replace")
        payload, marker, status = output.rpartition("\n")
        if not marker or not status.strip().isdigit():
            raise RuntimeError(f"modal curl returned no HTTP status: {output[-800:]}")
        return int(status.strip()), payload

    def _request(self, method, path, form=None, files=None):
        if self._auth_mode() == "modal-cli":
            status, text = self._modal_curl(method, path, form=form, files=files)
            try:
                body = json.loads(text) if text.strip() else None
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"H3Zero returned invalid JSON: {text[:800]}") from exc
            return status, body

        import requests

        headers = self._auth_headers()
        with ExitStack() as stack:
            uploads = {}
            for field, file_path, media_type in files or []:
                handle = stack.enter_context(open(file_path, "rb"))
                uploads[field] = (Path(file_path).name, handle, media_type)
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                data=form,
                files=uploads or None,
                timeout=300,
            )
        try:
            body = response.json() if response.content else None
        except ValueError:
            body = response.text[:800]
        return response.status_code, body

    def _download(self, path, out_path):
        if self._auth_mode() == "modal-cli":
            status, _ = self._modal_curl("GET", path, out_path=out_path)
            if status >= 400:
                raise RuntimeError(f"H3Zero video download returned HTTP {status}")
            return Path(out_path)

        import requests

        headers = {
            "User-Agent": "ai_render/0.1",
            "Accept": "video/mp4",
            **self._auth_headers(),
        }
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(f"{self.base_url}{path}", headers=headers, stream=True, timeout=300) as response:
            response.raise_for_status()
            with open(out, "wb") as handle:
                for chunk in response.iter_content(1 << 16):
                    handle.write(chunk)
        return out

    @staticmethod
    def _expect(status, body, expected, operation):
        if status != expected:
            detail = json.dumps(body, ensure_ascii=False) if isinstance(body, (dict, list)) else str(body)
            raise RuntimeError(f"H3Zero {operation} returned HTTP {status}: {detail[:800]}")

    def _settings(self, generation, style_images):
        mode = generation.get("reference_mode", "video")
        if mode != "video":
            raise ValueError(f"H3Zero only implements reference_mode 'video', got {mode!r}")
        config = _h3_config(generation)
        prompt = config.get("full_prompt")
        styles = [Path(path) for path in style_images or []]
        if len(styles) > 9:
            raise ValueError("H3Zero accepts at most 9 image references")
        validate_h3_prompt(prompt, len(styles))

        profile = self.sampling_profile or config.get("sampling_profile") or "turbo_4"
        # Constructor value is an explicit CLI/environment override.  The CLI
        # instantiates us from the nested scene value when no override exists.
        if profile not in PROFILES:
            raise ValueError(f"H3 sampling_profile must be one of {sorted(PROFILES)}, got {profile!r}")
        resolution = generation.get("resolution", self.resolution)
        if resolution != "480p":
            raise ValueError("H3Zero's production API supports only 480p")
        ratio = generation.get("aspect_ratio", "16:9")
        if ratio not in DIMENSIONS:
            raise ValueError("H3Zero supports only 16:9 or 9:16")
        duration = int(generation.get("duration", 5))
        if not 2 <= duration <= 15:
            raise ValueError("H3 reference generations must be 2 to 15 seconds")
        if generation.get("generate_audio") is False:
            raise ValueError("H3Zero does not expose an output-audio toggle")
        width, height = DIMENSIONS[ratio]
        return config, prompt, styles, profile, duration, width, height

    def generate(self, reference_video, generation, out_path, style_images=None, on_task=None):
        config, prompt, styles, profile, duration, width, height = self._settings(
            generation, style_images
        )
        references = [
            {"id": "blockout", "kind": "video", "field": "reference_0", "use_audio": False}
        ]
        files = [("reference_0", Path(reference_video), _mime(reference_video))]
        for index, image in enumerate(styles, start=1):
            field = f"reference_{index}"
            references.append({"id": f"look_{index}", "kind": "image", "field": field})
            files.append((field, image, _mime(image)))
        request_config = {
            "mode": "references",
            "width": width,
            "height": height,
            "duration_seconds": duration,
            "sampling_profile": profile,
            "references": references,
        }
        print(
            f"[generate] h3zero/{profile} -- {duration}s @ 480p {generation.get('aspect_ratio', '16:9')}, "
            f"1 video + {len(styles)} picture reference(s)"
        )
        print("[generate] prompt sent verbatim from generation.h3zero.full_prompt")
        status, body = self._request(
            "POST",
            "/api/jobs",
            form={"prompt": prompt, "config": json.dumps(request_config, separators=(",", ":"))},
            files=files,
        )
        self._expect(status, body, 202, "submission")
        task_id = (body or {}).get("id")
        if not task_id:
            raise RuntimeError(f"H3Zero returned no job id: {body!r}")
        if on_task:
            on_task(task_id)
        self._poll(task_id)
        out = self._download(f"/api/jobs/{task_id}/video", out_path)
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError("H3Zero download produced an empty file")
        ack_status, ack_body = self._request("POST", f"/api/jobs/{task_id}/acknowledge")
        if ack_status != 204:
            print(
                f"[generate] warning: result saved, but acknowledgement returned HTTP {ack_status}: "
                f"{str(ack_body)[:400]}"
            )
        print(f"[generate] ok -- {out} ({out.stat().st_size / 1e6:.1f} MB)")
        return out

    def fetch(self, task_id, out_path):
        self._poll(task_id, first_delay=0.0)
        out = self._download(f"/api/jobs/{task_id}/video", out_path)
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError("H3Zero download produced an empty file")
        status, body = self._request("POST", f"/api/jobs/{task_id}/acknowledge")
        if status != 204:
            print(f"[fetch] warning: acknowledgement returned HTTP {status}: {str(body)[:400]}")
        return out

    def _poll(self, task_id, first_delay=None):
        print(f"[generate] task {task_id} -- polling")
        deadline = time.time() + self.timeout
        delay = self.poll_interval if first_delay is None else first_delay
        last = None
        while time.time() < deadline:
            time.sleep(delay)
            delay = self.poll_interval
            status_code, body = self._request("GET", f"/api/jobs/{task_id}")
            self._expect(status_code, body, 200, "poll")
            status = str((body or {}).get("status", "")).lower()
            progress = (body or {}).get("progress") or {}
            phase = progress.get("phase")
            marker = f"{status}:{phase}"
            if marker != last:
                print(f"[generate]   {status or 'unknown'}{f' / {phase}' if phase else ''}")
                last = marker
            if status == "completed":
                return body
            if status in TERMINAL_BAD:
                raise RuntimeError(f"H3Zero task {status}: {(body or {}).get('error') or body}")
        raise RuntimeError(f"H3Zero task {task_id} did not finish within {self.timeout:.0f}s")
