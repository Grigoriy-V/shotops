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

Three things about the deployment this talks to are worth knowing here:

* Reference conditioning runs on the **Ref2VA** checkpoint, which is what
  MiniMax trained for it.  The upstream H3Zero routes that graph through FL2VA
  instead; ``tools/h3zero-ref2va-vram.patch`` puts it back.  Which checkpoint
  actually ran is in the job's ``result.model``.
* At least one look reference is **required**.  The blockout is grey, and grey
  is the only picture of the scene H3 has without one.
* Results are **not acknowledged**, because acknowledging deletes them.  Modal
  expires them on its own 24-hour schedule; until then a run stays inspectable
  and a lost download can be recovered with ``fetch``.
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
# Which checkpoint conditions on the references. `ref2va` is what MiniMax
# trained for it and the deployment's default; `fl2va` is what upstream H3Zero
# uses and what generation 007 ran on. Both files are already on the model
# volume, so this is a field in the request -- an A/B is two runs, not two
# deployments.
CHECKPOINTS = {"ref2va", "fl2va"}

# The step-distillation LoRAs, and the checkpoint each was distilled from.
# Advisory, not a constraint: any accelerator can be sent with any checkpoint,
# and crossing them deliberately is how you find out what it costs. A crossed
# pairing is reported, never refused. `none` loads no accelerator.
ACCELERATORS = {
    "fl2v_turbo_4": "fl2va",
    "fl2v_turbo_8": "fl2va",
    "ref2v_turbo_4": "ref2va",
}
NO_ACCELERATOR = "none"
# The gateway rejects any canvas that is not one of its own native presets for
# the requested resolution, so these are copied from what `native_canvas` in the
# deployment resolves to, not chosen. 768p is the deployment's recommended tier;
# 480p is this project's default because it is what the shots are authored at.
DIMENSIONS = {
    "480p": {"16:9": (864, 480), "9:16": (480, 864)},
    "768p": {"16:9": (1344, 768), "9:16": (768, 1344)},
}
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


def expected_tags(style_count):
    """The tags the service should assign, given what `generate` sends.

    Tags are positional and numbered independently per kind, so the blockout --
    sent first and the only video -- is always `<Video 1>`, and the look images
    follow in upload order as `<Picture 1>` upward.
    """
    return ["<Video 1>"] + [f"<Picture {number}>" for number in range(1, style_count + 1)]


def verify_reference_tags(body, style_count):
    """Check the tags the service actually assigned against what we meant.

    Worth doing even though the mapping is deterministic on paper. The prompt
    names its references by tag, and a shifted tag is the one failure that costs
    a full generation while looking, in the logs, exactly like a success: every
    file uploaded, every reference accepted, the wrong picture behind each name.
    """
    references = ((body or {}).get("request") or {}).get("references")
    if not isinstance(references, list) or not references:
        # The gateway has echoed tags since the version this was written
        # against. Say so rather than passing silently, but do not fail a
        # generation over a missing echo.
        return None
    assigned = []
    for reference in references:
        for tag in (reference or {}).get("tags") or []:
            assigned.append(str(tag))
    wanted = expected_tags(style_count)
    if assigned != wanted:
        raise RuntimeError(
            "H3Zero assigned reference tags that do not match the upload order: "
            f"got {assigned}, expected {wanted}. The prompt names its references by "
            "tag, so this generation would bind the wrong files."
        )
    return [
        (str((reference or {}).get("id")), ((reference or {}).get("tags") or [None])[0])
        for reference in references
    ]


def _print_model(body):
    """Report the checkpoint that actually ran.

    With the checkpoint selectable, "which model made this" stops being
    something the caller can assume. The worker reads it back out of the graph
    it executed, so this is the observation rather than the request.
    """
    result = (body or {}).get("result") or {}
    model = result.get("model")
    if model:
        print(f"[generate]   ran on {model}")
    lora = result.get("lora_id") or result.get("lora")
    if lora:
        matched = result.get("lora_matches_checkpoint")
        note = "" if matched is not False else " (crossed onto another checkpoint)"
        print(f"[generate]   accelerator {lora}{note}")


def _print_vram(body):
    """Report the worker's peak VRAM, when the deployment is new enough to send it."""
    vram = (((body or {}).get("result") or {}).get("vram")) or {}
    peak = vram.get("peak_used_gib")
    total = vram.get("total_gib")
    if peak is None or total is None:
        return
    share = vram.get("peak_used_fraction")
    tail = f" ({share:.0%})" if isinstance(share, (int, float)) else ""
    print(f"[generate]   vram peak {peak} / {total} GiB{tail} on {vram.get('device') or 'the GPU'}")


def _mime(path):
    value = mimetypes.guess_type(str(path))[0]
    if value not in {"video/mp4", "video/quicktime", "video/webm", "image/png", "image/jpeg", "image/webp"}:
        raise ValueError(f"H3Zero does not accept this reference type: {path}")
    return value


class H3Zero(VideoProvider):
    name = "h3zero/minimax-h3"
    uploader = "direct-multipart"
    resolution = "480p"

    def __init__(self, sampling_profile=None, checkpoint=None, accelerator=None,
                 poll_interval=5.0, timeout=1800.0):
        self.sampling_profile = (
            sampling_profile
            or os.environ.get("AI_RENDER_H3ZERO_PROFILE")
        )
        # Held on the instance so the manifest can record which checkpoint the
        # run asked for, before `generate` is ever called.
        self.checkpoint = checkpoint or os.environ.get("AI_RENDER_H3ZERO_CHECKPOINT")
        self.accelerator = accelerator or os.environ.get("AI_RENDER_H3ZERO_LORA")
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
        if not styles:
            # Without a look reference the only picture H3 has of the scene is
            # the grey blockout, and it will take the grey as art direction.
            # Seedance can be talked out of that; H3 has not been shown to be.
            raise ValueError(
                "H3Zero needs at least one look reference. Add 'style_references' to the "
                "scene, or pass --style, and bind them as <Picture N> in "
                "generation.h3zero.full_prompt."
            )
        if len(styles) > 9:
            raise ValueError("H3Zero accepts at most 9 image references")
        validate_h3_prompt(prompt, len(styles))

        profile = self.sampling_profile or config.get("sampling_profile") or "turbo_4"
        # Constructor value is an explicit CLI/environment override.  The CLI
        # instantiates us from the nested scene value when no override exists.
        if profile not in PROFILES:
            raise ValueError(f"H3 sampling_profile must be one of {sorted(PROFILES)}, got {profile!r}")
        # Environment beats the scene here, the opposite way round from the
        # profile, because this one exists to be flipped for a single
        # comparison run without editing -- and committing -- the shot.
        checkpoint = self.checkpoint or config.get("checkpoint") or "ref2va"
        if checkpoint not in CHECKPOINTS:
            raise ValueError(
                f"H3 checkpoint must be one of {sorted(CHECKPOINTS)}, got {checkpoint!r}"
            )
        accelerator = self.accelerator or config.get("accelerator_lora")
        if accelerator is not None and accelerator not in {*ACCELERATORS, NO_ACCELERATOR}:
            raise ValueError(
                f"H3 accelerator_lora must be one of {sorted(ACCELERATORS)} "
                f"or {NO_ACCELERATOR!r}, got {accelerator!r}"
            )
        resolution = str(generation.get("resolution", self.resolution))
        if resolution not in DIMENSIONS:
            raise ValueError(
                f"H3Zero supports {' and '.join(sorted(DIMENSIONS))}, got {resolution!r}"
            )
        ratio = generation.get("aspect_ratio", "16:9")
        if ratio not in DIMENSIONS[resolution]:
            raise ValueError("H3Zero supports only 16:9 or 9:16")
        duration = int(generation.get("duration", 5))
        # The gateway's own validate_generation rejects anything outside 5..15,
        # so a shorter request is a 422 rather than a short clip. The reference
        # video may be as short as 2s; the output may not.
        if not 5 <= duration <= 15:
            raise ValueError("H3 reference generations must be 5 to 15 seconds")
        if generation.get("generate_audio") is False:
            raise ValueError("H3Zero does not expose an output-audio toggle")
        width, height = DIMENSIONS[resolution][ratio]
        return (
            config, prompt, styles, profile, duration, width, height, resolution,
            checkpoint, accelerator,
        )

    def generate(self, reference_video, generation, out_path, style_images=None, on_task=None):
        (
            config, prompt, styles, profile, duration, width, height, resolution,
            checkpoint, accelerator,
        ) = self._settings(generation, style_images)
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
            "resolution": resolution,
            "duration_seconds": duration,
            "sampling_profile": profile,
            "reference_checkpoint": checkpoint,
            "references": references,
        }
        if accelerator is not None:
            request_config["accelerator_lora"] = accelerator
        crossed = (
            accelerator in ACCELERATORS and ACCELERATORS[accelerator] != checkpoint
        )
        print(
            f"[generate] h3zero/{checkpoint}/{profile} -- {duration}s @ {resolution} "
            f"{generation.get('aspect_ratio', '16:9')} ({width}x{height}), "
            f"1 video + {len(styles)} picture reference(s)"
        )
        if accelerator:
            note = " -- distilled from a different checkpoint" if crossed else ""
            print(f"[generate] accelerator {accelerator}{note}")
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
        for reference_id, tag in verify_reference_tags(body, len(styles)) or []:
            print(f"[generate]   {tag} <- {reference_id}")
        finished = self._poll(task_id)
        _print_model(finished)
        _print_vram(finished)
        out = self._download(f"/api/jobs/{task_id}/video", out_path)
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError("H3Zero download produced an empty file")
        # Deliberately not acknowledged. Acknowledging deletes the job record,
        # the staged references and the MP4 from the Modal volume, which throws
        # away the only server-side account of what was actually sent. They age
        # out on the gateway's own 24-hour schedule; until then the run stays
        # inspectable and `fetch` can recover a lost download.
        print(f"[generate] ok -- {out} ({out.stat().st_size / 1e6:.1f} MB)")
        print(f"[generate] kept on Modal as job {task_id} until its retention expires")
        return out

    def fetch(self, task_id, out_path):
        finished = self._poll(task_id, first_delay=0.0)
        _print_model(finished)
        _print_vram(finished)
        out = self._download(f"/api/jobs/{task_id}/video", out_path)
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError("H3Zero download produced an empty file")
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
