"""Report which credentials are configured, without ever printing their values.

    python tools/check_env.py
"""

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
]

loaded = env.load()


def is_set(name):
    value = loaded.get(name, "")
    # The example file ships placeholders; those are not real values.
    return bool(value) and "<" not in value


# Which storage credentials matter depends on the uploader in force: the piapi
# store authenticates with the provider key, so demanding Supabase there would
# report a problem that is not one.
uploader = upload.configured_name()
print(f"Uploader: {uploader}  (AI_RENDER_UPLOADER)\n")

missing = []
print("Required:" if uploader == "supabase" else "Supabase (unused by this uploader):")
for name, description in SUPABASE:
    ok = is_set(name)
    if not ok and uploader == "supabase":
        missing.append(name)
    label = "set    " if ok else ("MISSING" if uploader == "supabase" else "-      ")
    print(f"  {label}  {name:22} {description}")

print("\nProviders (at least one):")
for name, description in PROVIDERS:
    print(f"  {'set    ' if is_set(name) else '-      '}  {name:22} {description}")

print()
if not any(is_set(name) for name, _ in PROVIDERS):
    missing.append(" or ".join(name for name, _ in PROVIDERS))
if missing:
    print(f"Fill these in {env.ENV_FILE}: {', '.join(missing)}")
    sys.exit(1)
print("ready")
