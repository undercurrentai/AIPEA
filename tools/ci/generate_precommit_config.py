#!/usr/bin/env python3
# generate_precommit_config.py — Generate .pre-commit-config.yaml from standards.
# Stdlib-only. Exit 0 on success, exit 1 on invalid arguments.
#
# Usage:
#   python tools/ci/generate_precommit_config.py --languages python --tier BASELINE
#   python tools/ci/generate_precommit_config.py --languages python,typescript --tier ENHANCED --ai-system
#   python tools/ci/generate_precommit_config.py --languages python,rust,cpp --ai-system --iac --openapi
#   python tools/ci/generate_precommit_config.py --languages python --output .pre-commit-config.yaml

import argparse, pathlib, sys

# --- Hook registry (embedded from Engineering Standards Appendix A) -----------

VALID_LANGUAGES = {"python", "typescript", "javascript", "cpp", "rust", "sql", "protobuf"}
VALID_TIERS = {"BASELINE", "ENHANCED", "ELITE"}


def _yaml_value(val):
    """Quote a YAML string value if it contains special characters."""
    if not isinstance(val, str):
        return str(val)
    # Backslash-containing values (regex patterns) must use single quotes
    # to avoid YAML double-quote escape interpretation (e.g., \. becomes error)
    if "\\" in val:
        return "'" + val.replace("'", "''") + "'"
    special = set(":{}[]&*?|>!%#@`,")
    if any(c in val for c in special) or val.lower() in (
        "true", "false", "null", "yes", "no", "on", "off",
    ):
        return '"' + val.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return val


def _render_hook(hook_id, name=None, args=None, files=None, additional_deps=None,
                 language=None, pass_filenames=None, stages=None, entry=None):
    """Render a single hook block."""
    lines = [f"      - id: {hook_id}"]
    if name:
        lines.append(f"        name: {_yaml_value(name)}")
    if entry:
        lines.append(f"        entry: {_yaml_value(entry)}")
    if language:
        lines.append(f"        language: {language}")
    if args:
        rendered = ", ".join(f'"{a}"' for a in args)
        lines.append(f"        args: [{rendered}]")
    if files:
        lines.append(f"        files: {_yaml_value(files)}")
    if additional_deps:
        lines.append("        additional_dependencies: [")
        for i, dep in enumerate(additional_deps):
            comma = "," if i < len(additional_deps) - 1 else ""
            lines.append(f'          "{dep}"{comma}')
        lines.append("        ]")
    if pass_filenames is not None:
        lines.append(f"        pass_filenames: {'true' if pass_filenames else 'false'}")
    if stages:
        rendered = ", ".join(stages)
        lines.append(f"        stages: [{rendered}]")
    return "\n".join(lines)


def _render_repo(repo, rev, hooks):
    """Render a repo block with one or more hooks."""
    lines = [f"  - repo: {repo}", f"    rev: {rev}", "    hooks:"]
    for h in hooks:
        lines.append(h)
    return "\n".join(lines)


def _render_local_repo(hooks):
    """Render the local repo block."""
    lines = ["  - repo: local", "    hooks:"]
    for h in hooks:
        lines.append(h)
    return "\n".join(lines)


# --- Hook definitions ---------------------------------------------------------

def _common_hooks():
    """Pre-commit-hooks and gitleaks (always included)."""
    return [
        _render_repo(
            "https://github.com/pre-commit/pre-commit-hooks", "v6.0.0",
            [_render_hook("check-yaml"),
             _render_hook("end-of-file-fixer"),
             _render_hook("trailing-whitespace"),
             _render_hook("check-added-large-files")],
        ),
    ]


def _gitleaks_hook():
    """Gitleaks as a local hook."""
    return _render_hook(
        "gitleaks-secrets",
        name="gitleaks (secrets scan)",
        entry="gitleaks protect --staged --redact",
        language="system",
        stages=["pre-commit"],
    )


def _python_hooks(tier):
    """Python: ruff, bandit, mypy, semgrep."""
    repos = []

    # ruff
    repos.append(_render_repo(
        "https://github.com/astral-sh/ruff-pre-commit", "v0.15.0",
        [_render_hook("ruff", args=["--fix"]),
         _render_hook("ruff-format")],
    ))

    # bandit
    repos.append(_render_repo(
        "https://github.com/PyCQA/bandit", "1.9.3",
        [_render_hook("bandit", args=["-ll", "-q"])],
    ))

    # mypy — strict only at ENHANCED/ELITE
    mypy_args = ["--strict"] if tier in ("ENHANCED", "ELITE") else []
    repos.append(_render_repo(
        "https://github.com/pre-commit/mirrors-mypy", "v1.19.1",
        [_render_hook("mypy",
                      additional_deps=["types-requests", "pydantic>=2"],
                      args=mypy_args if mypy_args else None)],
    ))

    # semgrep
    repos.append(_render_repo(
        "https://github.com/semgrep/semgrep", "v1.150.0",
        [_render_hook("semgrep", args=["--error", "--config", "p/ci"])],
    ))

    return repos


def _typescript_hooks():
    """TypeScript: prettier + eslint with TS deps."""
    return [
        _render_repo(
            "https://github.com/pre-commit/mirrors-prettier", "v4.0.0-alpha.8",
            [_render_hook("prettier")],
        ),
        _render_repo(
            "https://github.com/pre-commit/mirrors-eslint", "v9.20.0",
            [_render_hook("eslint",
                          files=r"\.(ts|tsx|js|jsx)$",
                          additional_deps=[
                              "eslint", "typescript",
                              "@typescript-eslint/parser",
                              "@typescript-eslint/eslint-plugin",
                          ])],
        ),
    ]


def _javascript_hooks():
    """JavaScript: prettier + eslint without TS deps."""
    return [
        _render_repo(
            "https://github.com/pre-commit/mirrors-prettier", "v4.0.0-alpha.8",
            [_render_hook("prettier")],
        ),
        _render_repo(
            "https://github.com/pre-commit/mirrors-eslint", "v9.20.0",
            [_render_hook("eslint",
                          files=r"\.(js|jsx)$",
                          additional_deps=["eslint"])],
        ),
    ]


def _cpp_hooks():
    """C++: clang-format + cpplint."""
    return [
        _render_repo(
            "https://github.com/pre-commit/mirrors-clang-format", "v19.1.0",
            [_render_hook("clang-format", files=r"\.(c|cc|cpp|hh|hpp|h)$")],
        ),
        _render_repo(
            "https://github.com/cpplint/cpplint", "2.0.0",
            [_render_hook("cpplint", args=["--filter=-legal/copyright"])],
        ),
    ]


def _rust_hooks():
    """Rust: fmt + clippy."""
    return [
        _render_repo(
            "https://github.com/doublify/pre-commit-rust", "v1.0",
            [_render_hook("fmt"),
             _render_hook("clippy", args=["--", "-D", "warnings"])],
        ),
    ]


def _sql_hooks():
    """SQL: sqlfluff lint + fix."""
    return [
        _render_repo(
            "https://github.com/sqlfluff/sqlfluff", "4.0.0",
            [_render_hook("sqlfluff-lint"),
             _render_hook("sqlfluff-fix")],
        ),
    ]


def _protobuf_hooks():
    """Protobuf: buf format + lint."""
    return [
        _render_repo(
            "https://github.com/bufbuild/buf", "v1.50.0",
            [_render_hook("buf-format"),
             _render_hook("buf-lint")],
        ),
    ]


# Optional local hooks

def _ai_system_hooks():
    """AI governance local hooks."""
    return [
        _render_hook(
            "ai-rmf-artifacts",
            name="AI RMF / AIMS artifacts present",
            entry="python tools/ci/ai_rmf_validate_artifacts.py",
            language="system",
            pass_filenames=False,
        ),
        _render_hook(
            "ai-act-lint",
            name="EU AI Act technical file sanity",
            entry="python tools/ci/ai_act_lint.py",
            language="system",
            pass_filenames=False,
        ),
    ]


def _iac_hooks():
    """Infrastructure-as-code: checkov + conftest."""
    return [
        _render_hook(
            "checkov-iac",
            name="checkov (IaC scan)",
            entry="checkov -q -d .",
            language="system",
            files=r"\.(tf|tfvars|hcl|json|ya?ml)$",
            pass_filenames=False,
        ),
        _render_hook(
            "conftest-policies",
            name="conftest (OPA policy tests)",
            entry="conftest test --policy policy --no-color .",
            language="system",
            files=r"\.(tf|json|ya?ml|rego)$",
            pass_filenames=False,
        ),
    ]


def _openapi_hooks():
    """OpenAPI breaking change check."""
    return [
        _render_hook(
            "oasdiff-breaking",
            name="oasdiff (OpenAPI breaking change check)",
            entry="oasdiff -fail-on breaking openapi/current.yaml openapi/next.yaml",
            language="system",
            files=r"^openapi/.*\.(yaml|yml)$",
            pass_filenames=False,
        ),
    ]


# --- Assembly -----------------------------------------------------------------

LANGUAGE_HOOKS = {
    "python": _python_hooks,       # takes tier arg
    "typescript": _typescript_hooks,
    "javascript": _javascript_hooks,
    "cpp": _cpp_hooks,
    "rust": _rust_hooks,
    "sql": _sql_hooks,
    "protobuf": _protobuf_hooks,
}


def generate(languages, tier, ai_system=False, iac=False, openapi=False):
    """Generate .pre-commit-config.yaml content."""
    sections = []
    local_hooks = []

    # Header
    sections.append("# .pre-commit-config.yaml")
    sections.append(f"# Generated by generate_precommit_config.py (tier: {tier})")
    sections.append(f"# Languages: {', '.join(sorted(languages))}")
    sections.append("")
    sections.append("repos:")

    # Common hooks (always)
    for block in _common_hooks():
        sections.append(block)
        sections.append("")

    # Language-specific hooks
    seen_prettier = False
    for lang in sorted(languages):
        hook_fn = LANGUAGE_HOOKS[lang]
        if lang == "python":
            repos = hook_fn(tier)
        else:
            repos = hook_fn()

        for repo_block in repos:
            # Deduplicate prettier if both typescript and javascript
            if "mirrors-prettier" in repo_block:
                if seen_prettier:
                    continue
                seen_prettier = True
            sections.append(repo_block)
            sections.append("")

    # Optional local hooks
    if ai_system:
        local_hooks.extend(_ai_system_hooks())
    if iac:
        local_hooks.extend(_iac_hooks())
    if openapi:
        local_hooks.extend(_openapi_hooks())

    # Gitleaks always included as local hook
    local_hooks.append(_gitleaks_hook())

    if local_hooks:
        sections.append(_render_local_repo(local_hooks))
        sections.append("")

    return "\n".join(sections)


# --- CLI ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate .pre-commit-config.yaml from Engineering Standards (Appendix A).",
    )
    parser.add_argument(
        "--languages", required=True,
        help=f"Comma-separated list from: {', '.join(sorted(VALID_LANGUAGES))}",
    )
    parser.add_argument(
        "--tier", default="BASELINE",
        help="Compliance tier: BASELINE (default), ENHANCED, or ELITE",
    )
    parser.add_argument("--ai-system", action="store_true", help="Include AI governance hooks")
    parser.add_argument("--iac", action="store_true", help="Include checkov + conftest hooks")
    parser.add_argument("--openapi", action="store_true", help="Include oasdiff hook")
    parser.add_argument("--output", help="Write to file (default: stdout)")

    args = parser.parse_args()

    # Validate tier
    tier = args.tier.upper()
    if tier not in VALID_TIERS:
        print(f"ERROR: Invalid tier '{args.tier}'. Must be one of: {', '.join(sorted(VALID_TIERS))}", file=sys.stderr)
        sys.exit(1)

    # Validate languages
    languages = set()
    for lang in args.languages.split(","):
        lang = lang.strip().lower()
        if not lang:
            continue
        if lang not in VALID_LANGUAGES:
            print(f"ERROR: Invalid language '{lang}'. Must be one of: {', '.join(sorted(VALID_LANGUAGES))}", file=sys.stderr)
            sys.exit(1)
        languages.add(lang)

    if not languages:
        print("ERROR: At least one language is required.", file=sys.stderr)
        sys.exit(1)

    content = generate(languages, tier, args.ai_system, args.iac, args.openapi)

    if args.output:
        pathlib.Path(args.output).write_text(content)
        print(f"Wrote {args.output}")
    else:
        print(content)

    sys.exit(0)


if __name__ == "__main__":
    main()
