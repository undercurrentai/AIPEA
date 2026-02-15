# validate_scaffold_adoption.py — Check for unreplaced scaffold placeholders.
# Stdlib-only. Exit 0 if clean or no scaffold dirs, exit 1 if violations found.
#
# Intended for consuming repos AFTER copying the scaffold package.
# Scans ai/, docs/, schemas/, .github/ for common placeholder patterns
# that should have been replaced with real data.

import os
import re
import sys

# ---------------------------------------------------------------------------
# Placeholder patterns — 6 categories
# ---------------------------------------------------------------------------
PATTERNS = {
    "backtick_angle": re.compile(r"`<[^>]+>`"),
    "date_placeholder": re.compile(r"\bYYYY-MM(?:-DD)?\b"),
    "todo_marker": re.compile(r"\bTODO:"),
    "example_domain": re.compile(r"example\.com|@example\."),
    "example_id": re.compile(r"\bexample-[a-z]+"),
    "instruction_block": re.compile(r">\s*\*\*Instructions\*\*:"),
}

SCAN_DIRS = ("ai", "docs", "schemas", ".github")
SCAN_EXTENSIONS = {".yaml", ".yml", ".md", ".json"}
MAX_PER_CATEGORY = 5
TRUNCATE_LEN = 80

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_yaml_comment(line: str) -> bool:
    """Return True if the line is a YAML comment (stripped starts with #)."""
    return line.lstrip().startswith("#")


def _is_issue_form_placeholder(line: str) -> bool:
    """Return True if the line is a GitHub issue form 'placeholder:' field."""
    stripped = line.lstrip()
    return stripped.startswith("placeholder:")


def _should_skip_line(filepath: str, line: str) -> bool:
    """Context-aware false-positive filter."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in (".yaml", ".yml"):
        if _is_yaml_comment(line):
            return True
        if _is_issue_form_placeholder(line):
            return True
    return False


def scan_file(filepath: str) -> dict:
    """Scan a single file and return {category: [(line_num, snippet), ...]}."""
    hits = {}
    try:
        with open(filepath, encoding="utf-8", errors="replace") as fh:
            for line_num, line in enumerate(fh, start=1):
                if _should_skip_line(filepath, line):
                    continue
                for category, pattern in PATTERNS.items():
                    if pattern.search(line):
                        hits.setdefault(category, []).append(
                            (line_num, line.rstrip()[:TRUNCATE_LEN])
                        )
    except OSError:
        pass
    return hits


def collect_files(base: str) -> list:
    """Walk SCAN_DIRS under base, returning files with matching extensions."""
    files = []
    for scan_dir in SCAN_DIRS:
        root_path = os.path.join(base, scan_dir)
        if not os.path.isdir(root_path):
            continue
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Skip .git directories
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for fname in filenames:
                if os.path.splitext(fname)[1].lower() in SCAN_EXTENSIONS:
                    files.append(os.path.join(dirpath, fname))
    return files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    base = os.getcwd()

    # Check if any scaffold dirs exist
    present = [d for d in SCAN_DIRS if os.path.isdir(os.path.join(base, d))]
    if not present:
        print("SKIP: No scaffold directories found (ai/, docs/, schemas/, .github/).")
        return 0

    files = collect_files(base)
    if not files:
        print("SKIP: No scannable files found in scaffold directories.")
        return 0

    # Aggregate violations
    all_violations = {}  # {category: [(filepath, line_num, snippet), ...]}
    for filepath in files:
        rel = os.path.relpath(filepath, base)
        hits = scan_file(filepath)
        for category, entries in hits.items():
            for line_num, snippet in entries:
                all_violations.setdefault(category, []).append(
                    (rel, line_num, snippet)
                )

    if not all_violations:
        print("OK: No placeholder patterns detected in scaffold files.")
        return 0

    # Report violations grouped by category
    total = sum(len(v) for v in all_violations.values())
    print(f"FAIL: {total} placeholder violation(s) across {len(all_violations)} category(ies).\n")

    for category, entries in sorted(all_violations.items()):
        shown = entries[:MAX_PER_CATEGORY]
        remaining = len(entries) - len(shown)
        print(f"  [{category}] ({len(entries)} match(es))")
        for rel, line_num, snippet in shown:
            print(f"    {rel}:{line_num}: {snippet}")
        if remaining > 0:
            print(f"    ... and {remaining} more")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
