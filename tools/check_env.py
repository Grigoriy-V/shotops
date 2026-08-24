"""Report which credentials are configured, without ever printing their values.

    python tools/check_env.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_render import env  # noqa: E402

REQUIRED = [
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


print("Required:")
missing = []
for name, description in REQUIRED:
    if not is_set(name):
        missing.append(name)
    print(f"  {'set    ' if is_set(name) else 'MISSING'}  {name:22} {description}")

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
