"""Report which credentials are configured, without ever printing their values.

    python tools/check_env.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_render import env, upload  # noqa: E402

SUPABASE = [
    ("SUPABASE_URL", "Supabase project URL"),
    ("SUPABASE_SERVICE_KEY", "Supabase service_role key -- storage write access"),
    ("SUPABASE_BUCKET", "Storage bucket name (default: ai-render)"),
]

# Exactly one provider key is enough to run; the rest are optional alternatives.
PROVIDERS = [
    ("PIAPI_KEY", "PiAPI -- default provider, honours the blockout"),
    ("COMETAPI_KEY", "CometAPI -- alternative, ignores video references"),
    ("AI_RENDER_H3ZERO_URL", "H3Zero -- self-hosted Modal endpoint"),
]

loaded = env.load()


def is_set(name):
    value = os.environ.get(name, "")
    # The example file ships placeholders; those are not real values.
    return bool(value) and "<" not in value


# Which storage credentials matter depends on the uploader in force: the piapi
# store authenticates with the provider key, so demanding Supabase there would
# report a problem that is not one.
uploader = upload.configured_name()
h3_ready = is_set("AI_RENDER_H3ZERO_URL")
needs_uploader = uploader == "supabase" and not h3_ready
print(f"Uploader: {uploader}  (AI_RENDER_UPLOADER)\n")

missing = []
print("Required:" if needs_uploader else "Supabase (not required for the configured H3/direct uploader):")
for name, description in SUPABASE:
    ok = is_set(name)
    if not ok and needs_uploader:
        missing.append(name)
    label = "set    " if ok else ("MISSING" if needs_uploader else "-      ")
    print(f"  {label}  {name:22} {description}")

print("\nProviders (at least one):")
for name, description in PROVIDERS:
    print(f"  {'set    ' if is_set(name) else '-      '}  {name:22} {description}")

if h3_ready:
    h3_auth = os.environ.get("AI_RENDER_H3ZERO_AUTH", "modal-proxy").lower()
    print(f"\nH3Zero auth: {h3_auth}")
    if h3_auth == "modal-proxy":
        for name in ("AI_RENDER_H3ZERO_MODAL_KEY", "AI_RENDER_H3ZERO_MODAL_SECRET"):
            ok = is_set(name)
            print(f"  {'set    ' if ok else 'MISSING'}  {name}")
            if not ok:
                missing.append(name)
    elif h3_auth == "bearer" and not is_set("AI_RENDER_H3ZERO_TOKEN"):
        print("  MISSING  AI_RENDER_H3ZERO_TOKEN")
        missing.append("AI_RENDER_H3ZERO_TOKEN")

print()
if not any(is_set(name) for name, _ in PROVIDERS):
    missing.append(" or ".join(name for name, _ in PROVIDERS))
if missing:
    print(f"Fill these in {env.ENV_FILE}: {', '.join(missing)}")
    sys.exit(1)
print("ready")
