# enforce_perf_gate.py — Compare perf results against baseline (bidirectional metrics).
# Stdlib-only. Exit 0 on pass/skip, exit 1 on failure.

import json, sys, pathlib

baseline_path = pathlib.Path("perf_baseline.json")
results_path = pathlib.Path("perf_results.json")

if not baseline_path.exists():
    print("SKIP: No perf_baseline.json found; set baseline first."); sys.exit(0)

if not results_path.exists():
    print("FAIL: perf_baseline.json exists but no perf_results.json — run benchmarks first.")
    sys.exit(1)

try:
    baseline = json.loads(baseline_path.read_text())
except (json.JSONDecodeError, OSError) as e:
    print(f"FAIL: Cannot parse perf_baseline.json: {e}")
    sys.exit(1)

try:
    results = json.loads(results_path.read_text())
except (json.JSONDecodeError, OSError) as e:
    print(f"FAIL: Cannot parse perf_results.json: {e}")
    sys.exit(1)

if not isinstance(baseline, dict):
    print(f"FAIL: perf_baseline.json must be a JSON object, got {type(baseline).__name__}")
    sys.exit(1)

if not isinstance(results, dict):
    print(f"FAIL: perf_results.json must be a JSON object, got {type(results).__name__}")
    sys.exit(1)

metrics = baseline.get("metrics")
if not metrics or not isinstance(metrics, dict):
    print("FAIL: perf_baseline.json must contain a non-empty 'metrics' object")
    sys.exit(1)

violations = 0
try:
    tolerance = float(baseline.get("tolerance_pct", 10)) / 100.0
except (ValueError, TypeError) as e:
    print(f"FAIL: Invalid tolerance_pct in perf_baseline.json: {e}")
    sys.exit(1)

for metric, config in metrics.items():
    actual = results.get(metric)
    if actual is None:
        print(f"FAIL: Metric '{metric}' missing from perf_results.json")
        violations += 1
        continue

    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        print(f"FAIL: Metric '{metric}' has non-numeric value: {actual!r}")
        violations += 1
        continue

    # Support both bare number (backward compat) and dict format
    if isinstance(config, dict):
        if "threshold" not in config:
            print(f"FAIL: Metric '{metric}' config missing 'threshold' key")
            violations += 1
            continue
        threshold = config["threshold"]
        # Default direction is "lower_is_better" (e.g., latency, error rate)
        direction = config.get("direction", "lower_is_better")
    else:
        threshold = config
        # Bare number defaults to lower_is_better
        direction = "lower_is_better"

    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        print(f"FAIL: Metric '{metric}' has non-numeric threshold: {threshold!r}")
        violations += 1
        continue

    if direction == "lower_is_better":
        limit = threshold * (1.0 + tolerance)
        if actual > limit:
            print(f"FAIL: {metric} = {actual} exceeds baseline {threshold} by >{tolerance*100:.0f}%")
            violations += 1
    elif direction == "higher_is_better":
        limit = threshold * (1.0 - tolerance)
        if actual < limit:
            print(f"FAIL: {metric} = {actual} below baseline {threshold} by >{tolerance*100:.0f}%")
            violations += 1
    else:
        print(f"FAIL: Unknown direction '{direction}' for metric '{metric}'")
        violations += 1

if violations:
    sys.exit(1)
print("OK: Performance gate passed.")
