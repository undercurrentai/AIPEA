# validate_agent_messages.py — Validate *.agent.json transcripts in runs/ directory.
# Stdlib-only. Exit 0 on pass/skip, exit 1 on failure.

import sys, pathlib, json

# BASELINE fields (5). S8.3 [ENHANCED] adds payload_hash — not checked here to avoid
# breaking BASELINE adopters who don't yet hash payloads.
required = {"agent_id", "conversation_id", "seed_id", "ts_utc", "intent"}
violations = 0
runs_dir = pathlib.Path("runs")

if not runs_dir.exists():
    print("SKIP: No runs/ directory."); sys.exit(0)

for p in runs_dir.rglob("*.agent.json"):
    try:
        data = json.loads(p.read_text())
        if not isinstance(data, dict):
            print(f"FAIL: {p} is not a JSON object")
            violations += 1
            continue
        if not required.issubset(data.keys()):
            print(f"FAIL: Missing fields in {p}")
            violations += 1
    except json.JSONDecodeError as e:
        print(f"FAIL: Bad JSON in {p}: {e}")
        violations += 1
    except OSError as e:
        print(f"FAIL: Cannot read {p}: {e}")
        violations += 1

if violations:
    sys.exit(1)
print("OK: Agent transcripts valid.")
