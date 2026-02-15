# ai_rmf_validate_artifacts.py — Verify AI governance artifacts in ai/ directory.
# Stdlib-only. Exit 0 on pass, exit 1 on failure.

import sys, pathlib

r = pathlib.Path("ai")

# Required artifacts and their expected content markers (case-insensitive)
artifacts = {
    "system-register.yaml": ["systems:"],
    "risk-register.yaml": ["risks:"],
    "model-card.yaml": ["model:"],
    "data-card.yaml": ["datasets:"],
    "oversight-plan.md": ["oversight"],
    "postmarket-monitoring.md": ["monitoring"],
    "AIMS-POLICY.md": ["policy"],
    "technical_file/README.md": ["technical"],
}

missing = []
empty_or_invalid = []

for rel_path, markers in artifacts.items():
    fp = r / rel_path
    if not fp.exists():
        missing.append(rel_path)
        continue
    try:
        content = fp.read_text().lower()
    except (OSError, UnicodeDecodeError) as e:
        empty_or_invalid.append(f"{rel_path} (cannot read: {e})")
        continue
    if not content.strip():
        empty_or_invalid.append(f"{rel_path} (empty file)")
        continue
    if not any(m in content for m in markers):
        empty_or_invalid.append(f"{rel_path} (no content marker found)")

if missing:
    print("FAIL: Missing AI governance artifacts:", ", ".join(missing))
if empty_or_invalid:
    print("FAIL: Invalid AI governance artifacts:", ", ".join(empty_or_invalid))
if missing or empty_or_invalid:
    sys.exit(1)
print("OK: AI RMF/AIMS artifacts present and valid.")
