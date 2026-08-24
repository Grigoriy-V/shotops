"""Publish the blockout so the video model can fetch it.

Seedance accepts reference *videos* by URL only -- base64 works for images and
audio, but not video. So the blockout has to be reachable from the internet for
the duration of one job.

Supabase Storage with a signed URL is the right shape for that: the object lives
in the user's own bucket, the URL is unguessable, it expires, and we delete the
object once the job is done. Nothing lands on a public paste host.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

SIGNED_URL_TTL = int(os.environ.get("AI_RENDER_URL_TTL", "3600"))

# The consumer sniffs Content-Type, not the file extension. Uploading a PNG as
# video/mp4 gets the reference rejected with "not a supported image", after the
# task has already been created -- so this is worth getting right rather than
# assuming everything we publish is a blockout.
CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def content_type_for(path):
    suffix = Path(path).suffix.lower()
    if suffix not in CONTENT_TYPES:
        raise ValueError(
            f"don't know a content type for {suffix!r} ({path}). "
            f"Known: {', '.join(sorted(CONTENT_TYPES))}"
        )
    return CONTENT_TYPES[suffix]


class Uploader:
    def upload(self, path: Path) -> tuple[str, callable]:
        """Return (public_url, cleanup) -- call cleanup() when the job is done."""
        raise NotImplementedError


class SupabaseUploader(Uploader):
    name = "supabase"

    def __init__(self, url=None, key=None, bucket=None, ttl=SIGNED_URL_TTL):
        self.url = (url or os.environ.get("SUPABASE_URL", "")).rstrip("/")
        self.key = key or os.environ.get("SUPABASE_SERVICE_KEY", "")
        self.bucket = bucket or os.environ.get("SUPABASE_BUCKET", "ai-render")
        self.ttl = ttl
        missing = [
            name
            for name, value in (("SUPABASE_URL", self.url), ("SUPABASE_SERVICE_KEY", self.key))
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"{' and '.join(missing)} not set. Add them to .env -- the blockout has to be "
                "fetchable by URL, because Seedance does not accept video references inline."
            )

    def _session(self):
        import requests

        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {self.key}", "apikey": self.key})
        return session

    def upload(self, path):
        path = Path(path)
        session = self._session()
        content_type = content_type_for(path)
        # A random prefix keeps concurrent runs of the same scene from colliding.
        kind = "images" if content_type.startswith("image/") else "blockouts"
        key = f"{kind}/{uuid.uuid4().hex[:12]}/{path.name}"
        base = f"{self.url}/storage/v1"

        print(
            f"[upload] supabase://{self.bucket}/{key} "
            f"({path.stat().st_size / 1e6:.1f} MB, {content_type})"
        )
        with open(path, "rb") as handle:
            response = session.post(
                f"{base}/object/{self.bucket}/{key}",
                data=handle,
                headers={"Content-Type": content_type, "x-upsert": "true"},
                timeout=300,
            )
        if response.status_code >= 400:
            hint = ""
            if response.status_code in (400, 404) and "Bucket not found" in response.text:
                hint = f"\nCreate a bucket named {self.bucket!r} in Supabase Storage, or set SUPABASE_BUCKET."
            elif response.status_code in (401, 403):
                hint = "\nSUPABASE_SERVICE_KEY needs storage write access -- the service_role key works."
            raise RuntimeError(f"supabase upload {response.status_code}: {response.text[:400]}{hint}")

        signed = session.post(
            f"{base}/object/sign/{self.bucket}/{key}",
            json={"expiresIn": self.ttl},
            timeout=60,
        )
        if signed.status_code >= 400:
            raise RuntimeError(f"supabase sign {signed.status_code}: {signed.text[:400]}")
        path_part = signed.json().get("signedURL") or signed.json().get("signedUrl")
        if not path_part:
            raise RuntimeError(f"no signedURL in response: {signed.json()!r}")

        url = f"{base}{path_part}" if path_part.startswith("/") else f"{base}/{path_part}"
        print(f"[upload] signed url ready (expires in {self.ttl}s)")

        def cleanup():
            try:
                session.delete(f"{base}/object/{self.bucket}/{key}", timeout=60)
                print(f"[upload] removed {key}")
            except Exception as exc:  # cleanup must never mask a real result
                print(f"[upload] warning: could not remove {key}: {exc}")

        return url, cleanup


def get_uploader(name=None):
    name = name or os.environ.get("AI_RENDER_UPLOADER", "supabase")
    if name == "supabase":
        return SupabaseUploader()
    raise ValueError(f"unknown uploader {name!r} (available: supabase)")
