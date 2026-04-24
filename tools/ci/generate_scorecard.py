#!/usr/bin/env python3
# generate_scorecard.py — Engineering scorecard aggregator.
# Stdlib-only. Always exits 0 (informational tool, not a gate).
#
# Aggregates: CI linter results, line coverage, mutation score,
# SBOM presence, dependency freshness, DORA metrics stub.
#
# Usage:
#   python tools/ci/generate_scorecard.py          # Markdown to stdout
#   python tools/ci/generate_scorecard.py --json    # JSON to stdout

import json, pathlib, subprocess, sys

TIMEOUT = 30  # seconds per subprocess

# --- Tier detection -----------------------------------------------------------

TIER_THRESHOLDS = {
    "BASELINE":  {"coverage": 70, "mutation": 50},
    "ENHANCED":  {"coverage": 80, "mutation": 60},
    "ELITE":     {"coverage": 90, "mutation": 75},
}


def _detect_tier():
    """Read tier from pyproject.toml [tool.standards] tier = 'X'."""
    pp = pathlib.Path("pyproject.toml")
    if not pp.exists():
        return "BASELINE"
    try:
        in_section = False
        for line in pp.read_text().splitlines():
            stripped = line.strip()
            if stripped == "[tool.standards]":
                in_section = True
                continue
            if in_section:
                if stripped.startswith("["):
                    break
                if stripped.startswith("tier"):
                    # tier = "ENHANCED"  or  tier = 'ELITE'
                    parts = stripped.split("=", 1)
                    if len(parts) == 2:
                        val = parts[1].strip().strip("\"'").upper()
                        if val in TIER_THRESHOLDS:
                            return val
    except OSError:
        pass
    return "BASELINE"


# --- CI Linter runner ---------------------------------------------------------

LINTERS = [
    ("ai_rmf_validate_artifacts.py", "AI RMF Artifacts"),
    ("ai_act_lint.py",               "AI Act Technical File"),
    ("verify_fips.py",               "FIPS 140-3"),
    ("validate_log_schema.py",       "Log Schema"),
    ("validate_agent_messages.py",   "Agent Messages"),
    ("validate_scaffold_adoption.py","Scaffold Adoption"),
]


def _run_linters():
    """Run each CI linter and return list of (name, status, detail)."""
    results = []
    tools_dir = pathlib.Path("tools/ci")
    for script, name in LINTERS:
        script_path = tools_dir / script
        if not script_path.exists():
            results.append((name, "SKIP", "script not found"))
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, text=True, timeout=TIMEOUT,
            )
            if proc.returncode == 0:
                # Detect SKIP vs OK from output
                out = proc.stdout.strip()
                if out.startswith("SKIP"):
                    results.append((name, "SKIP", out))
                else:
                    results.append((name, "OK", out))
            else:
                detail = proc.stdout.strip() or proc.stderr.strip()
                results.append((name, "FAIL", detail[:200]))
        except subprocess.TimeoutExpired:
            results.append((name, "ERROR", f"timeout ({TIMEOUT}s)"))
        except OSError as e:
            results.append((name, "ERROR", str(e)[:200]))
    return results


# --- Coverage -----------------------------------------------------------------

def _get_coverage():
    """Try to read coverage from coverage.json, else run `coverage json`."""
    cov_file = pathlib.Path("coverage.json")
    data = None

    if cov_file.exists():
        try:
            data = json.loads(cov_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    if data is None:
        try:
            subprocess.run(
                ["coverage", "json", "-q"],
                capture_output=True, timeout=TIMEOUT,
            )
            if cov_file.exists():
                data = json.loads(cov_file.read_text())
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            pass

    if isinstance(data, dict):
        totals = data.get("totals", {})
        pct = totals.get("percent_covered")
        if isinstance(pct, (int, float)) and not isinstance(pct, bool):
            return round(pct, 1)
    return None


# --- Mutation -----------------------------------------------------------------

def _get_mutation():
    """Parse mutation score from mutmut results if cache exists."""
    if not pathlib.Path(".mutmut-cache").exists():
        return None
    try:
        proc = subprocess.run(
            ["mutmut", "results"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        # Look for "Killed N out of M mutants" or percentage patterns
        for line in proc.stdout.splitlines():
            line = line.strip()
            # mutmut show summary: "X/Y  (Z%)"
            if "%" in line:
                for part in line.split():
                    if part.endswith("%") or part.endswith("%)"):
                        num = part.rstrip("%)").lstrip("(")
                        try:
                            return round(float(num), 1)
                        except ValueError:
                            pass
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


# --- SBOM ---------------------------------------------------------------------

def _get_sbom():
    """Check for SBOM file presence."""
    for name in ("sbom.spdx.json", "sbom.cdx.json"):
        if pathlib.Path(name).exists():
            return name
    return None


# --- Dependency freshness -----------------------------------------------------

def _get_dep_freshness():
    """Count outdated dependencies via pip or npm."""
    results = {}

    # pip
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        if proc.returncode == 0:
            outdated = json.loads(proc.stdout)
            if isinstance(outdated, list):
                results["pip"] = len(outdated)
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
        pass

    # npm
    if pathlib.Path("package.json").exists():
        try:
            proc = subprocess.run(
                ["npm", "outdated", "--json"],
                capture_output=True, text=True, timeout=TIMEOUT,
            )
            # npm outdated exits 1 when outdated packages exist
            try:
                outdated = json.loads(proc.stdout)
                if isinstance(outdated, dict):
                    results["npm"] = len(outdated)
            except json.JSONDecodeError:
                pass
        except (subprocess.TimeoutExpired, OSError):
            pass

    return results if results else None


# --- Output formatters --------------------------------------------------------

def _format_status(status):
    """Format status for markdown."""
    if status == "OK":
        return "PASS"
    return status


def _format_markdown(tier, thresholds, linters, coverage, mutation, sbom, deps):
    lines = []
    lines.append("# Engineering Scorecard")
    lines.append("")
    lines.append(f"**Tier**: {tier} | **Thresholds**: coverage >= {thresholds['coverage']}%, mutation >= {thresholds['mutation']}%")
    lines.append("")

    # CI Linters
    lines.append("## CI Linters")
    lines.append("")
    lines.append("| Linter | Status | Detail |")
    lines.append("|--------|--------|--------|")
    for name, status, detail in linters:
        short = detail[:80].replace("|", "/") if detail else ""
        lines.append(f"| {name} | {_format_status(status)} | {short} |")
    ok_count = sum(1 for _, s, _ in linters if s == "OK")
    skip_count = sum(1 for _, s, _ in linters if s == "SKIP")
    fail_count = sum(1 for _, s, _ in linters if s not in ("OK", "SKIP"))
    lines.append("")
    lines.append(f"**Summary**: {ok_count} passed, {skip_count} skipped, {fail_count} failed")
    lines.append("")

    # Coverage
    lines.append("## Coverage")
    lines.append("")
    if coverage is not None:
        met = "PASS" if coverage >= thresholds["coverage"] else "BELOW THRESHOLD"
        lines.append(f"Line coverage: **{coverage}%** ({met})")
    else:
        lines.append("Line coverage: *not available*")
    lines.append("")

    # Mutation
    lines.append("## Mutation Testing")
    lines.append("")
    if mutation is not None:
        met = "PASS" if mutation >= thresholds["mutation"] else "BELOW THRESHOLD"
        lines.append(f"Mutation score: **{mutation}%** ({met})")
    else:
        lines.append("Mutation score: *not available*")
    lines.append("")

    # Supply Chain
    lines.append("## Supply Chain")
    lines.append("")
    if sbom:
        lines.append(f"SBOM: **{sbom}** (present)")
    else:
        lines.append("SBOM: *missing*")
    lines.append("")

    # Dep Freshness
    lines.append("## Dependency Freshness")
    lines.append("")
    if deps:
        for mgr, count in deps.items():
            lines.append(f"- {mgr}: {count} outdated package{'s' if count != 1 else ''}")
    else:
        lines.append("Dependency freshness: *not available*")
    lines.append("")

    # DORA
    lines.append("## DORA Metrics")
    lines.append("")
    lines.append("*See DORA dashboard — tracked, not gated (S14).*")
    lines.append("")

    return "\n".join(lines)


def _format_json(tier, thresholds, linters, coverage, mutation, sbom, deps):
    return json.dumps({
        "tier": tier,
        "thresholds": thresholds,
        "linters": [
            {"name": n, "status": s, "detail": d} for n, s, d in linters
        ],
        "coverage_pct": coverage,
        "mutation_pct": mutation,
        "sbom": sbom,
        "dependencies_outdated": deps,
        "dora": "See DORA dashboard",
    }, indent=2)


# --- Main ---------------------------------------------------------------------

def main():
    use_json = "--json" in sys.argv

    tier = _detect_tier()
    thresholds = TIER_THRESHOLDS[tier]
    linters = _run_linters()
    coverage = _get_coverage()
    mutation = _get_mutation()
    sbom = _get_sbom()
    deps = _get_dep_freshness()

    if use_json:
        print(_format_json(tier, thresholds, linters, coverage, mutation, sbom, deps))
    else:
        print(_format_markdown(tier, thresholds, linters, coverage, mutation, sbom, deps))

    sys.exit(0)


if __name__ == "__main__":
    main()
