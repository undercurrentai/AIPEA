"""AIPEA CLI — onboarding and configuration commands.

Requires the ``[cli]`` extra: ``pip install aipea[cli]`` (adds Typer + Rich).

Commands:
    aipea configure [--global/-g]  — Interactive setup wizard
    aipea check [--connectivity]   — Verify configuration status
    aipea doctor                   — Full diagnostic report
    aipea info                     — Quick library/config summary
"""

# pyright: reportPossiblyUnboundVariable=false
from __future__ import annotations

import sys

try:
    import typer
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    _HAS_TYPER = True
except ImportError:  # pragma: no cover
    _HAS_TYPER = False

if not _HAS_TYPER:  # pragma: no cover

    def _missing_typer_error() -> None:
        sys.stderr.write(
            "Error: AIPEA CLI requires the [cli] extra.\nInstall with: pip install aipea[cli]\n"
        )
        raise SystemExit(1)

    # Provide a minimal callable so `python -m aipea` shows a helpful message
    def app() -> None:
        _missing_typer_error()

else:
    import logging
    import platform
    from pathlib import Path

    import httpx

    import aipea
    from aipea.config import (
        _GLOBAL_CONFIG_FILE,
        AIPEAConfig,
        get_config_locations,
        load_config,
        save_dotenv,
        save_toml_config,
    )

    console = Console()
    app = typer.Typer(
        name="aipea",
        help="AIPEA — AI Prompt Engineer Agent CLI",
        no_args_is_help=True,
    )

    # ================================================================
    # aipea info
    # ================================================================

    @app.command()
    def info() -> None:
        """Show library version, config status, and detected providers."""
        cfg = load_config()

        table = Table(title="AIPEA Info", show_header=False, border_style="blue")
        table.add_column("Key", style="bold")
        table.add_column("Value")

        table.add_row("Version", aipea.__version__)
        table.add_row("Python", platform.python_version())
        table.add_row("Exa API Key", AIPEAConfig.redact_key(cfg.exa_api_key))
        table.add_row("Firecrawl API Key", AIPEAConfig.redact_key(cfg.firecrawl_api_key))
        table.add_row("HTTP Timeout", f"{cfg.http_timeout}s")
        table.add_row("Exports", str(len(aipea.__all__)))

        # Config sources
        for field_name, source in cfg._sources.items():
            table.add_row(f"  {field_name} source", source)

        console.print(table)

    # ================================================================
    # aipea check
    # ================================================================

    @app.command()
    def check(
        connectivity: bool = typer.Option(
            False, "--connectivity/--no-connectivity", help="Test API connectivity"
        ),
    ) -> None:
        """Verify configuration status and optionally test API connectivity."""
        cfg = load_config()
        errors: list[str] = []
        warnings: list[str] = []

        table = Table(title="Configuration Check", border_style="blue")
        table.add_column("Setting", style="bold")
        table.add_column("Status")
        table.add_column("Value")
        table.add_column("Source")

        # Exa
        exa_status = "set" if cfg.has_exa() else "not set"
        exa_style = "green" if cfg.has_exa() else "yellow"
        table.add_row(
            "EXA_API_KEY",
            f"[{exa_style}]{exa_status}[/{exa_style}]",
            AIPEAConfig.redact_key(cfg.exa_api_key),
            cfg._sources.get("exa_api_key", "unknown"),
        )
        if not cfg.has_exa():
            warnings.append("Exa API key not configured — Exa search will be disabled")

        # Firecrawl
        fc_status = "set" if cfg.has_firecrawl() else "not set"
        fc_style = "green" if cfg.has_firecrawl() else "yellow"
        table.add_row(
            "FIRECRAWL_API_KEY",
            f"[{fc_style}]{fc_status}[/{fc_style}]",
            AIPEAConfig.redact_key(cfg.firecrawl_api_key),
            cfg._sources.get("firecrawl_api_key", "unknown"),
        )
        if not cfg.has_firecrawl():
            warnings.append("Firecrawl API key not configured — Firecrawl search will be disabled")

        # Timeout
        table.add_row(
            "AIPEA_HTTP_TIMEOUT",
            "[green]set[/green]",
            f"{cfg.http_timeout}s",
            cfg._sources.get("http_timeout", "unknown"),
        )

        console.print(table)

        # Connectivity tests
        if connectivity:
            console.print("\n[bold]Connectivity Tests[/bold]")
            if cfg.has_exa():
                if not _test_exa_connectivity(cfg.exa_api_key, cfg.exa_api_url):
                    errors.append("Exa API connectivity test failed")
            else:
                console.print("  Exa: [dim]skipped (no key)[/dim]")

            if cfg.has_firecrawl():
                if not _test_firecrawl_connectivity(cfg.firecrawl_api_key, cfg.firecrawl_api_url):
                    errors.append("Firecrawl API connectivity test failed")
            else:
                console.print("  Firecrawl: [dim]skipped (no key)[/dim]")

        if warnings:
            console.print()
            for warning in warnings:
                console.print(f"  [yellow]![/yellow] {warning}")

        if errors:
            console.print()
            for error in errors:
                console.print(f"  [red]![/red] {error}")
            raise typer.Exit(1)

    def _test_exa_connectivity(api_key: str, api_url: str, *, silent: bool = False) -> bool:
        """Ping Exa API to verify the key works.

        ``api_url`` is passed in by the caller (typically from the resolved
        :class:`AIPEAConfig`) so custom endpoints persisted in .env or
        global TOML are honored. (#92)
        """
        try:
            resp = httpx.post(
                api_url,
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
                json={"query": "test", "numResults": 1},
                timeout=10.0,
            )
            if resp.status_code == 200:
                if not silent:
                    console.print("  Exa: [green]OK[/green]")
                return True
            if not silent:
                console.print(f"  Exa: [red]HTTP {resp.status_code}[/red]")
            return False
        except httpx.HTTPError as exc:
            # httpx.HTTPError is the base for TimeoutException, RequestError,
            # HTTPStatusError, and other httpx-originated failures. Narrower
            # than Exception; still catches every network-level failure mode.
            logging.debug("Exa connectivity error", exc_info=True)
            if not silent:
                console.print(f"  Exa: [red]Error — {exc}[/red]")
            return False

    def _test_firecrawl_connectivity(api_key: str, api_url: str, *, silent: bool = False) -> bool:
        """Ping Firecrawl API to verify the key works.

        ``api_url`` is passed in by the caller so custom endpoints
        persisted in .env or global TOML are honored. (#92)
        """
        try:
            resp = httpx.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"query": "test", "limit": 1},
                timeout=10.0,
            )
            if resp.status_code == 200:
                if not silent:
                    console.print("  Firecrawl: [green]OK[/green]")
                return True
            if not silent:
                console.print(f"  Firecrawl: [red]HTTP {resp.status_code}[/red]")
            return False
        except httpx.HTTPError as exc:
            # See Exa connectivity check above — same rationale.
            logging.debug("Firecrawl connectivity error", exc_info=True)
            if not silent:
                console.print(f"  Firecrawl: [red]Error — {exc}[/red]")
            return False

    def _ollama_install_hint() -> str:
        """Return a platform-specific Ollama install command."""
        system = platform.system()
        if system == "Darwin":
            return "brew install ollama"
        if system == "Linux":
            return "curl -fsSL https://ollama.ai/install.sh | sh"
        return "https://ollama.ai"

    # ================================================================
    # aipea doctor
    # ================================================================

    class _DoctorChecks:
        """Accumulates pass/warn/fail counts for doctor command."""

        def __init__(self) -> None:
            self.passed = 0
            self.warned = 0
            self.failed = 0

        def ok(self, label: str, detail: str = "") -> None:
            self.passed += 1
            msg = f"  [green]PASS[/green] {label}"
            if detail:
                msg += f" — {detail}"
            console.print(msg)

        def warn(self, label: str, detail: str = "") -> None:
            self.warned += 1
            msg = f"  [yellow]WARN[/yellow] {label}"
            if detail:
                msg += f" — {detail}"
            console.print(msg)

        def fail(self, label: str, detail: str = "") -> None:
            self.failed += 1
            msg = f"  [red]FAIL[/red] {label}"
            if detail:
                msg += f" — {detail}"
            console.print(msg)

    def _doctor_deps(chk: _DoctorChecks) -> None:
        """Check dependency availability."""
        try:
            import httpx as _httpx

            chk.ok("httpx", _httpx.__version__)
        except ImportError:
            chk.fail("httpx", "not installed")

        chk.ok("typer", "available (CLI mode)")

        try:
            from importlib.metadata import PackageNotFoundError
            from importlib.metadata import version as _pkg_version

            chk.ok("rich", _pkg_version("rich"))
        except PackageNotFoundError:
            chk.warn("rich", "not installed or version unknown")

    def _doctor_config_files(chk: _DoctorChecks) -> None:
        """Check config file locations."""
        locations = get_config_locations()
        for label, key in [(".env", "dotenv"), ("global config", "global_toml")]:
            info = locations[key]
            if info["exists"]:
                chk.ok(label, str(info["path"]))
            else:
                chk.warn(label, f"not found at {info['path']}")

    def _doctor_api_keys(chk: _DoctorChecks, cfg: AIPEAConfig) -> None:
        """Check API key configuration."""
        for name, has_fn, key_val, src_key in [
            ("Exa API key", cfg.has_exa, cfg.exa_api_key, "exa_api_key"),
            ("Firecrawl API key", cfg.has_firecrawl, cfg.firecrawl_api_key, "firecrawl_api_key"),
        ]:
            if has_fn():
                redacted = AIPEAConfig.redact_key(key_val)
                source = cfg._sources.get(src_key, "?")
                chk.ok(name, f"{redacted} (from {source})")
            else:
                chk.warn(name, f"not configured — {name.split()[0]} search disabled")
        chk.ok("HTTP timeout", f"{cfg.http_timeout}s")

    def _doctor_security(chk: _DoctorChecks) -> None:
        """Check security posture."""
        import stat as stat_mod

        gitignore_path = Path.cwd() / ".gitignore"
        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                # Defensive: .gitignore may be non-UTF-8 or unreadable. (#89)
                chk.warn(".gitignore", f"unable to read: {e}")
                content = None
            if content is not None:
                gitignore_entries = [
                    ln.strip()
                    for ln in content.splitlines()
                    if ln.strip() and not ln.strip().startswith("#")
                ]
                if any(entry in (".env", "/.env") for entry in gitignore_entries):
                    chk.ok(".gitignore", ".env is listed")
                else:
                    chk.warn(".gitignore", ".env is NOT listed — secrets may be committed!")
        else:
            chk.warn(".gitignore", "file not found")

        dotenv_file = Path.cwd() / ".env"
        if dotenv_file.exists():
            mode = dotenv_file.stat().st_mode
            group_other_bits = (
                stat_mod.S_IRGRP
                | stat_mod.S_IWGRP
                | stat_mod.S_IXGRP
                | stat_mod.S_IROTH
                | stat_mod.S_IWOTH
                | stat_mod.S_IXOTH
            )
            if not (mode & group_other_bits):
                chk.ok(".env permissions", "owner-only access (0o600)")
            else:
                chk.warn(
                    ".env permissions",
                    f"non-owner permissions detected (mode={oct(mode & 0o777)})",
                )
        else:
            chk.ok(".env permissions", "n/a (no .env file)")

    def _doctor_ollama(chk: _DoctorChecks) -> None:
        """Check Ollama availability and models."""
        import shutil
        import subprocess as _sp

        if shutil.which("ollama") is None:
            chk.warn(
                "Ollama",
                f"not installed — offline LLM enhancement unavailable. "
                f"Install with: {_ollama_install_hint()}",
            )
            return

        chk.ok("Ollama binary", str(shutil.which("ollama")))

        try:
            result = _sp.run(
                ["ollama", "list"],  # noqa: S607  # verified via shutil.which above
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                chk.warn("Ollama service", "not running — start with 'ollama serve'")
                return

            lines = result.stdout.strip().split("\n")
            model_count = max(0, len(lines) - 1)  # minus header line
            if model_count > 0:
                model_names = [line.split()[0] for line in lines[1:] if line.strip()]
                chk.ok("Ollama models", f"{model_count} available: {', '.join(model_names)}")
            else:
                chk.warn("Ollama models", "none downloaded — run 'ollama pull gemma3:1b'")
        except _sp.TimeoutExpired:
            chk.warn("Ollama service", "timed out (may not be running)")
        except Exception as exc:
            logging.debug("Ollama doctor error", exc_info=True)
            chk.warn("Ollama", str(exc))

    def _doctor_connectivity(chk: _DoctorChecks, cfg: AIPEAConfig) -> None:
        """Check API connectivity using consistent PASS/WARN/FAIL format."""
        if cfg.has_exa():
            if _test_exa_connectivity(cfg.exa_api_key, cfg.exa_api_url, silent=True):
                chk.ok("Exa connectivity")
            else:
                chk.fail("Exa connectivity", "API request failed")
        else:
            chk.warn("Exa connectivity", "skipped (no key)")

        if cfg.has_firecrawl():
            if _test_firecrawl_connectivity(
                cfg.firecrawl_api_key, cfg.firecrawl_api_url, silent=True
            ):
                chk.ok("Firecrawl connectivity")
            else:
                chk.fail("Firecrawl connectivity", "API request failed")
        else:
            chk.warn("Firecrawl connectivity", "skipped (no key)")

    def _doctor_knowledge_base(chk: _DoctorChecks) -> None:
        """Check offline knowledge base status."""
        _db = Path(load_config().db_path)
        db_path = _db if _db.is_absolute() else Path.cwd() / _db
        if not db_path.exists():
            chk.warn(
                "Knowledge base",
                f"not found at {db_path} — run 'aipea seed-kb' to create",
            )
            return

        try:
            import sqlite3

            from aipea.errors import KnowledgeStoreError
            from aipea.knowledge import OfflineKnowledgeBase, StorageTier

            with OfflineKnowledgeBase(str(db_path), StorageTier.STANDARD) as kb:
                count = kb._get_node_count_sync()
                domains = kb._get_domains_summary_sync()

            if count > 0:
                domain_str = ", ".join(f"{d}={c}" for d, c in sorted(domains.items()))
                chk.ok("Knowledge base", f"{count} entries ({domain_str})")
            else:
                chk.warn("Knowledge base", "exists but empty — run 'aipea seed-kb'")
        except (sqlite3.Error, OSError, KnowledgeStoreError) as exc:
            # sqlite3.Error covers corruption, locked DB, and query failures.
            # OSError covers missing file, permission denied, and FS errors.
            # KnowledgeStoreError is AIPEA's own wrapper (errors.py) for any
            # failure the knowledge module itself chooses to raise.
            logging.debug("Knowledge base doctor error", exc_info=True)
            chk.warn("Knowledge base", f"error reading: {exc}")

    @app.command()
    def doctor() -> None:
        """Run a full diagnostic check of the AIPEA installation."""
        chk = _DoctorChecks()
        console.print(Panel("[bold]AIPEA Doctor[/bold]", border_style="blue"))

        # 1. Python (requires-python >= 3.11 enforced by packaging)
        console.print("\n[bold]1. Python Environment[/bold]")
        chk.ok("Python version", platform.python_version())

        # 2. Package
        console.print("\n[bold]2. Package[/bold]")
        chk.ok("AIPEA version", aipea.__version__)

        # 3. Dependencies
        console.print("\n[bold]3. Dependencies[/bold]")
        _doctor_deps(chk)

        # 4. Config files
        console.print("\n[bold]4. Configuration Files[/bold]")
        _doctor_config_files(chk)

        # 5. API keys
        console.print("\n[bold]5. API Keys[/bold]")
        cfg = load_config()
        _doctor_api_keys(chk, cfg)

        # 6. Security
        console.print("\n[bold]6. Security[/bold]")
        _doctor_security(chk)

        # 7. Connectivity
        console.print("\n[bold]7. Connectivity[/bold]")
        _doctor_connectivity(chk, cfg)

        # 8. Ollama (offline LLM)
        console.print("\n[bold]8. Ollama (Offline LLM)[/bold]")
        _doctor_ollama(chk)

        # 9. Offline Knowledge Base
        console.print("\n[bold]9. Offline Knowledge Base[/bold]")
        _doctor_knowledge_base(chk)

        # Summary
        total = chk.passed + chk.warned + chk.failed
        if chk.failed > 0:
            style, label = "red", "ISSUES FOUND"
        elif chk.warned > 0:
            style, label = "yellow", "MOSTLY OK"
        else:
            style, label = "green", "ALL GOOD"

        console.print()
        console.print(
            Panel(
                f"[{style}]{label}[/{style}]: "
                f"{chk.passed} passed, {chk.warned} warnings, {chk.failed} failed "
                f"(of {total} checks)",
                title="Summary",
                border_style=style,
            )
        )

        # Recommendations (based on findings)
        import shutil

        recommendations: list[str] = []
        if not cfg.has_exa() and not cfg.has_firecrawl():
            recommendations.append(
                "Configure API keys for web search: [bold]aipea configure[/bold]"
            )
        if shutil.which("ollama") is None:
            recommendations.append(
                f"Install Ollama for offline LLM enhancement: [bold]{_ollama_install_hint()}[/bold]"
            )
        _db_rec = Path(cfg.db_path)
        if not _db_rec.is_absolute():
            _db_rec = Path.cwd() / _db_rec
        if not _db_rec.exists():
            recommendations.append("Populate offline knowledge base: [bold]aipea seed-kb[/bold]")

        if recommendations:
            console.print()
            console.print(
                Panel(
                    "\n".join(f"  {r}" for r in recommendations),
                    title="Recommendations",
                    border_style="cyan",
                )
            )

    def _warn_if_env_not_in_gitignore() -> None:
        """Check .gitignore for .env entry and warn if missing.

        Extracted from ``configure`` to keep its McCabe complexity under the
        project's 15-ceiling and to defensively handle non-UTF-8 or unreadable
        ``.gitignore`` files. (#89)
        """
        gitignore = Path.cwd() / ".gitignore"
        if not gitignore.exists():
            console.print(
                "[yellow]Warning: No .gitignore found — "
                "create one and add .env to prevent committing secrets![/yellow]"
            )
            return
        try:
            content = gitignore.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            console.print(f"[yellow]Warning: unable to read .gitignore ({e})[/yellow]")
            return
        gi_entries = [
            ln.strip()
            for ln in content.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if not any(entry in (".env", "/.env") for entry in gi_entries):
            console.print(
                "[yellow]Warning: .env is not in .gitignore — "
                "add it to prevent committing secrets![/yellow]"
            )

    # ================================================================
    # aipea configure
    # ================================================================

    @app.command()
    def configure(
        global_config: bool = typer.Option(
            False, "--global", "-g", help="Save to ~/.aipea/config.toml instead of .env"
        ),
        validate: bool = typer.Option(
            True, "--validate/--no-validate", help="Validate API keys after saving"
        ),
    ) -> None:
        """Interactive configuration wizard."""
        console.print(Panel("[bold]AIPEA Configuration[/bold]", border_style="blue"))

        cfg = load_config()

        # Prompt for each key
        console.print("\nEnter values (press Enter to keep existing):\n")

        console.print("  [bold]Exa[/bold] — AI-powered web search for real-time context enrichment")
        console.print("  Get a free API key at: [link=https://exa.ai]https://exa.ai[/link]")
        console.print("  [dim](Press Enter to skip — AIPEA works without it)[/dim]")
        exa_display = AIPEAConfig.redact_key(cfg.exa_api_key) if cfg.has_exa() else "(not set)"
        exa_input = typer.prompt(
            f"  Exa API Key [{exa_display}]",
            default="",
            show_default=False,
        )
        if exa_input:
            cfg.exa_api_key = exa_input

        console.print()
        console.print(
            "  [bold]Firecrawl[/bold] — Web scraping and search for structured content retrieval"
        )
        console.print(
            "  Get a free API key at: [link=https://firecrawl.dev]https://firecrawl.dev[/link]"
        )
        console.print("  [dim](Press Enter to skip — AIPEA works without it)[/dim]")
        fc_display = (
            AIPEAConfig.redact_key(cfg.firecrawl_api_key) if cfg.has_firecrawl() else "(not set)"
        )
        fc_input = typer.prompt(
            f"  Firecrawl API Key [{fc_display}]",
            default="",
            show_default=False,
        )
        if fc_input:
            cfg.firecrawl_api_key = fc_input

        timeout_input = typer.prompt(
            f"  HTTP Timeout [{cfg.http_timeout}s]",
            default="",
            show_default=False,
        )
        if timeout_input:
            try:
                val = float(timeout_input)
                if 0 < val < float("inf"):
                    cfg.http_timeout = val
                else:
                    console.print("  [yellow]Invalid timeout, keeping current value[/yellow]")
            except ValueError:
                console.print("  [yellow]Invalid timeout, keeping current value[/yellow]")

        # Save
        if global_config:
            target = _GLOBAL_CONFIG_FILE
            save_toml_config(target, cfg)
            console.print(f"\n[green]Saved to {target}[/green]")
        else:
            target = Path.cwd() / ".env"
            save_dotenv(target, cfg)
            console.print(f"\n[green]Saved to {target}[/green]")

            _warn_if_env_not_in_gitignore()

        # Validate keys
        if validate:
            console.print("\n[bold]Validating...[/bold]")
            if cfg.has_exa():
                _test_exa_connectivity(cfg.exa_api_key, cfg.exa_api_url)
            if cfg.has_firecrawl():
                _test_firecrawl_connectivity(cfg.firecrawl_api_key, cfg.firecrawl_api_url)

        # Summary
        console.print()
        table = Table(title="Configuration Summary", show_header=False, border_style="green")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Exa API Key", AIPEAConfig.redact_key(cfg.exa_api_key))
        table.add_row("Firecrawl API Key", AIPEAConfig.redact_key(cfg.firecrawl_api_key))
        table.add_row("HTTP Timeout", f"{cfg.http_timeout}s")
        table.add_row("Saved to", str(target))
        console.print(table)

        # Next steps
        import shutil

        next_steps: list[str] = []
        if not cfg.has_exa() and not cfg.has_firecrawl():
            next_steps.append("AIPEA will use offline/template mode (no API keys configured)")
        if shutil.which("ollama") is None:
            next_steps.append(
                f"Optional: Install Ollama for richer offline enhancement — "
                f"{_ollama_install_hint()}"
            )
        next_steps.append("Run 'aipea seed-kb' to populate the offline knowledge base")
        next_steps.append("Run 'aipea doctor' to verify your full setup")

        console.print()
        console.print(
            Panel(
                "\n".join(f"  {step}" for step in next_steps),
                title="Next Steps",
                border_style="blue",
            )
        )

    # ================================================================
    # aipea seed-kb
    # ================================================================

    @app.command("seed-kb")
    def seed_kb(
        db_path: str = typer.Option(
            "", "--db", "-d", help="Path to SQLite knowledge base file (default: from config)"
        ),
    ) -> None:
        """Populate the offline knowledge base with curated seed knowledge."""
        import asyncio

        from aipea.knowledge import (
            OfflineKnowledgeBase,
            StorageTier,
            seed_knowledge_base,
        )

        if not db_path:
            db_path = load_config().db_path

        console.print(Panel("[bold]AIPEA Knowledge Base Seeding[/bold]", border_style="blue"))

        kb = OfflineKnowledgeBase(db_path=db_path, tier=StorageTier.STANDARD)
        try:
            count = asyncio.run(seed_knowledge_base(kb))
            stats = asyncio.run(kb.get_domains_summary())

            table = Table(title="Seed Results", border_style="green")
            table.add_column("Domain", style="bold")
            table.add_column("Count", justify="right")
            for domain_name, domain_count in sorted(stats.items()):
                table.add_row(domain_name, str(domain_count))
            table.add_row("[bold]Total[/bold]", f"[bold]{count}[/bold]")
            console.print(table)

            console.print(f"\n[green]Seeded {count} entries to {db_path}[/green]")
        finally:
            kb.close()
