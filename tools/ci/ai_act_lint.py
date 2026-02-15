# ai_act_lint.py — Verify EU AI Act technical file structure (Annex IV).
# Stdlib-only. Exit 0 on pass, exit 1 on failure.

import sys, pathlib

base = pathlib.Path("ai/technical_file")

required_files = ["instructions-for-use.md"]
required_dirs = ["testing", "conformity", "logs"]

miss = []

for f in required_files:
    p = base / f
    if not p.is_file():
        miss.append(f"{f} (expected file)")

for d in required_dirs:
    p = base / d
    if not p.is_dir():
        miss.append(f"{d}/ (expected directory)")
    elif not any(f for f in p.iterdir() if not f.name.startswith(".")):
        miss.append(f"{d}/ (directory exists but contains no content files)")

if miss:
    print("FAIL: EU AI Act technical file incomplete:", ", ".join(miss))
    sys.exit(1)
print("OK: EU AI Act technical file structure valid.")
