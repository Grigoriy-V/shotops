"""Publish the blockout so the video model can fetch it.

Seedance accepts reference *videos* by URL only -- base64 works for images and
audio, but not video. So the blockout has to be reachable from the internet for
the duration of one job.

Two ways to do that, and they trade off against each other.

Supabase Storage keeps the file in the user's own bucket behind a signed URL we
delete the moment the job ends. Nothing lands on a host we do not control, and
nothing outlives the run.

PiAPI's own ephemeral store is the other end of that trade. It is what the
provider's playground uses, and their Seedance docs say plainly: *"Use publicly
accessible URLs (e.g. hosted on a CDN or cloud storage). Signed / expiring URLs
may fail."* Which is a description of the Supabase route. The cost is that the
file sits on a third party for 24 hours with no delete endpoint to call.

Neither is the obvious default, so both are here and `AI_RENDER_UPLOADER`
chooses. Prefer PiAPI's when the provider is PiAPI and the reference is
something you are content to leave on their storage for a day.
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


class PiapiUploader(Uploader):
    """PiAPI's own ephemeral store -- the host their playground publishes to.

    Chosen when the reference has to arrive the way the provider expects it:
    a plain public URL on `storage.theapi.app`, not a signed one their docs warn
    may fail.

    Two things about it are worth knowing before switching:

    **There is no delete.** The file expires after 24 hours and that is the only
    control there is, so `cleanup` here is honest about doing nothing rather
    than pretending. Anything you would not leave on someone else's server for a
    day should go through Supabase instead.

    **It is not on the free plan.** The endpoint answers 403 below Creator, and
    that is a plan problem with no workaround in code.
    """

    name = "piapi"

    ENDPOINT = os.environ.get(
        "PIAPI_UPLOAD_URL", "https://upload.theapi.app/api/ephemeral_resource"
    )
    # Their limits, not ours: the extension list is shorter than CONTENT_TYPES
    # (no .mov, no .webm) and the ceiling is on the file, checked here so a
    # 12 MB blockout fails locally instead of after a base64 round trip.
    ACCEPTED = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
    MAX_BYTES = 10 * 1024 * 1024
    MAX_NAME = 128

    def __init__(self, key=None):
        self.key = key or os.environ.get("PIAPI_KEY", "")
        if not self.key:
            raise RuntimeError(
                "PIAPI_KEY is not set, and the PiAPI uploader authenticates with the "
                "same key as the generation.\nPut it in .env (.env is gitignored)."
            )

    def _check(self, path):
        suffix = path.suffix.lower()
        if suffix not in self.ACCEPTED:
            raise ValueError(
                f"PiAPI's uploader does not take {suffix!r} ({path.name}). "
                f"Accepted: {', '.join(sorted(self.ACCEPTED))}."
            )
        size = path.stat().st_size
        if size > self.MAX_BYTES:
            raise ValueError(
                f"{path.name} is {size / 1e6:.1f} MB, over PiAPI's 10 MB upload limit. "
                "Shorten the blockout, drop its resolution, or use the supabase uploader."
            )
        if len(path.name) > self.MAX_NAME:
            raise ValueError(f"{path.name!r} is over PiAPI's {self.MAX_NAME}-character name limit.")

    def upload(self, path):
        import base64

        import requests

        path = Path(path)
        self._check(path)
        content_type = content_type_for(path)
        print(
            f"[upload] piapi ephemeral -- {path.name} "
            f"({path.stat().st_size / 1e6:.1f} MB, {content_type})"
        )

        response = requests.post(
            self.ENDPOINT,
            json={
                "file_name": path.name,
                "file_data": base64.b64encode(path.read_bytes()).decode("ascii"),
            },
            headers={"x-api-key": self.key, "Content-Type": "application/json"},
            timeout=300,
        )
        if response.status_code >= 400:
            hint = ""
            if response.status_code == 403:
                hint = "\nThis endpoint needs a Creator plan or higher on PiAPI."
            raise RuntimeError(f"piapi upload {response.status_code}: {response.text[:400]}{hint}")

        body = response.json()
        url = (body.get("data") or {}).get("url")
        if not url:
            raise RuntimeError(f"no data.url in upload response: {body!r}")
        print("[upload] public url ready (expires in 24h, no delete endpoint)")

        def cleanup():
            """Deliberately empty. PiAPI expires the object itself and offers no
            way to remove it early; a cleanup that silently did nothing while
            looking like the Supabase one would be the worse lie."""

        return url, cleanup


UPLOADERS = {"supabase": SupabaseUploader, "piapi": PiapiUploader}


def configured_name():
    """Which uploader a run will use. Worth recording in the manifest: where the
    reference was published is a property of the run, and the difference between
    two hosts is exactly the kind of thing a result later has to be explained by."""
    return os.environ.get("AI_RENDER_UPLOADER", "supabase")


def get_uploader(name=None):
    name = name or configured_name()
    if name not in UPLOADERS:
        raise ValueError(f"unknown uploader {name!r} (available: {', '.join(sorted(UPLOADERS))})")
    return UPLOADERS[name]()
