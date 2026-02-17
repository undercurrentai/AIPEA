"""AIPEA Configuration System — stdlib-only config loading and persistence.

Provides a unified configuration layer that merges multiple sources
in priority order:

    Constructor args > Environment vars > .env (cwd) > ~/.aipea/config.toml > Defaults

All parsing uses stdlib only (``tomllib`` for TOML, manual KEY=VALUE for .env).
No external dependencies are introduced.
"""

from __future__ import annotations

import logging
import os
import stat
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_HTTP_TIMEOUT = 30.0
_GLOBAL_CONFIG_DIR = Path.home() / ".aipea"
_GLOBAL_CONFIG_FILE = _GLOBAL_CONFIG_DIR / "config.toml"


# ---------------------------------------------------------------------------
# AIPEAConfig dataclass
# ---------------------------------------------------------------------------


@dataclass
class AIPEAConfig:
    """Resolved AIPEA configuration.

    Attributes:
        exa_api_key: Exa search provider API key.
        firecrawl_api_key: Firecrawl provider API key.
        http_timeout: HTTP timeout for search providers (seconds).
    """

    exa_api_key: str = ""
    firecrawl_api_key: str = ""
    http_timeout: float = _DEFAULT_HTTP_TIMEOUT
    _sources: dict[str, str] = field(default_factory=dict, repr=False)

    # -- helpers --

    def has_exa(self) -> bool:
        """Return True if an Exa API key is configured."""
        return bool(self.exa_api_key)

    def has_firecrawl(self) -> bool:
        """Return True if a Firecrawl API key is configured."""
        return bool(self.firecrawl_api_key)

    @staticmethod
    def redact_key(key: str) -> str:
        """Redact an API key for display, showing first 4 and last 4 chars."""
        if not key or len(key) < 12:
            return "****" if key else "(not set)"
        return f"{key[:4]}...{key[-4:]}"


# ---------------------------------------------------------------------------
# .env parser (stdlib only)
# ---------------------------------------------------------------------------


def _parse_dotenv(path: Path) -> dict[str, str]:
    """Parse a ``.env`` file into a dict of key-value pairs.

    Supports:
    - ``KEY=VALUE`` (unquoted, single-quoted, double-quoted)
    - ``export KEY=VALUE``
    - Blank lines and ``#`` comments
    - Inline comments after unquoted values
    """
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip optional ``export `` prefix
        if line.startswith("export "):
            line = line[7:].strip()

        if "=" not in line:
            continue

        key, _, raw_value = line.partition("=")
        key = key.strip()
        raw_value = raw_value.strip()

        # Handle quoted values
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in ("'", '"'):
            quote_char = raw_value[0]
            value = raw_value[1:-1]
            # Unescape double-quoted values (single-quoted are literal)
            if quote_char == '"':
                value = value.replace("\\\\", "\x00").replace('\\"', '"').replace("\x00", "\\")
        else:
            # Strip inline comment for unquoted values
            comment_idx = raw_value.find(" #")
            if comment_idx != -1:
                raw_value = raw_value[:comment_idx].strip()
            value = raw_value

        if key:
            values[key] = value

    return values


# ---------------------------------------------------------------------------
# TOML parser (stdlib tomllib)
# ---------------------------------------------------------------------------


def _parse_toml_config(path: Path) -> dict[str, str]:
    """Parse ``~/.aipea/config.toml`` and return the ``[aipea]`` section."""
    values: dict[str, str] = {}
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
        section = data.get("aipea", {})
        if isinstance(section, dict):
            for k, v in section.items():
                values[k] = str(v)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        logger.debug("Could not parse TOML config %s: %s", path, exc)
    return values


# ---------------------------------------------------------------------------
# Unified loader
# ---------------------------------------------------------------------------


def load_config(
    *,
    dotenv_path: Path | None = None,
    toml_path: Path | None = None,
) -> AIPEAConfig:
    """Load AIPEA configuration by merging all sources.

    Priority (highest wins):
        1. Environment variables (``EXA_API_KEY``, ``FIRECRAWL_API_KEY``, ``AIPEA_HTTP_TIMEOUT``)
        2. Project-local ``.env`` file (``dotenv_path`` or ``cwd/.env``)
        3. Global ``~/.aipea/config.toml``
        4. Built-in defaults

    Args:
        dotenv_path: Override path to ``.env`` (default: ``cwd/.env``).
        toml_path: Override path to global TOML config (default: ``~/.aipea/config.toml``).

    Returns:
        Fully-resolved :class:`AIPEAConfig`.
    """
    sources: dict[str, str] = {}

    # Layer 4: defaults (implicit in dataclass)

    # Layer 3: global TOML
    toml_file = toml_path or _GLOBAL_CONFIG_FILE
    toml_vals = _parse_toml_config(toml_file)

    # Layer 2: project-local .env
    dotenv_file = dotenv_path or Path.cwd() / ".env"
    dotenv_vals = _parse_dotenv(dotenv_file)

    # Resolve each field: env > .env > toml > default
    exa_key = ""
    firecrawl_key = ""
    http_timeout = _DEFAULT_HTTP_TIMEOUT

    # --- exa_api_key ---
    env_exa = os.environ.get("EXA_API_KEY")
    if env_exa is not None:
        exa_key = env_exa
        sources["exa_api_key"] = "env"
    elif "EXA_API_KEY" in dotenv_vals:
        exa_key = dotenv_vals["EXA_API_KEY"]
        sources["exa_api_key"] = f"dotenv ({dotenv_file})"
    elif "exa_api_key" in toml_vals:
        exa_key = toml_vals["exa_api_key"]
        sources["exa_api_key"] = f"toml ({toml_file})"
    else:
        sources["exa_api_key"] = "default"

    # --- firecrawl_api_key ---
    env_fc = os.environ.get("FIRECRAWL_API_KEY")
    if env_fc is not None:
        firecrawl_key = env_fc
        sources["firecrawl_api_key"] = "env"
    elif "FIRECRAWL_API_KEY" in dotenv_vals:
        firecrawl_key = dotenv_vals["FIRECRAWL_API_KEY"]
        sources["firecrawl_api_key"] = f"dotenv ({dotenv_file})"
    elif "firecrawl_api_key" in toml_vals:
        firecrawl_key = toml_vals["firecrawl_api_key"]
        sources["firecrawl_api_key"] = f"toml ({toml_file})"
    else:
        sources["firecrawl_api_key"] = "default"

    # --- http_timeout ---
    env_timeout = os.environ.get("AIPEA_HTTP_TIMEOUT")
    if env_timeout is not None:
        sources["http_timeout"] = "env"
        try:
            val = float(env_timeout)
            http_timeout = val if 0 < val < float("inf") else _DEFAULT_HTTP_TIMEOUT
        except (ValueError, TypeError):
            http_timeout = _DEFAULT_HTTP_TIMEOUT
    elif "AIPEA_HTTP_TIMEOUT" in dotenv_vals:
        sources["http_timeout"] = f"dotenv ({dotenv_file})"
        try:
            val = float(dotenv_vals["AIPEA_HTTP_TIMEOUT"])
            http_timeout = val if 0 < val < float("inf") else _DEFAULT_HTTP_TIMEOUT
        except (ValueError, TypeError):
            http_timeout = _DEFAULT_HTTP_TIMEOUT
    elif "http_timeout" in toml_vals:
        sources["http_timeout"] = f"toml ({toml_file})"
        try:
            val = float(toml_vals["http_timeout"])
            http_timeout = val if 0 < val < float("inf") else _DEFAULT_HTTP_TIMEOUT
        except (ValueError, TypeError):
            http_timeout = _DEFAULT_HTTP_TIMEOUT
    else:
        sources["http_timeout"] = "default"

    return AIPEAConfig(
        exa_api_key=exa_key,
        firecrawl_api_key=firecrawl_key,
        http_timeout=http_timeout,
        _sources=sources,
    )


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def save_dotenv(path: Path, config: AIPEAConfig) -> None:
    """Write configuration to a ``.env`` file with restricted permissions.

    Args:
        path: Target file path.
        config: Configuration to persist.
    """
    lines = [
        "# AIPEA Configuration",
        "# Generated by `aipea configure`",
        "",
    ]
    if config.exa_api_key:
        escaped = config.exa_api_key.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'EXA_API_KEY="{escaped}"')
    if config.firecrawl_api_key:
        escaped = config.firecrawl_api_key.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'FIRECRAWL_API_KEY="{escaped}"')
    if config.http_timeout != _DEFAULT_HTTP_TIMEOUT:
        lines.append(f"AIPEA_HTTP_TIMEOUT={config.http_timeout}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except OSError:
        logger.warning("Could not set file permissions on %s — file may be world-readable", path)


def save_toml_config(path: Path, config: AIPEAConfig) -> None:
    """Write configuration to a TOML file with restricted permissions.

    Creates ``~/.aipea/`` directory if it does not exist.

    Args:
        path: Target file path (typically ``~/.aipea/config.toml``).
        config: Configuration to persist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# AIPEA Global Configuration",
        "# Generated by `aipea configure --global`",
        "",
        "[aipea]",
    ]
    if config.exa_api_key:
        escaped = config.exa_api_key.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'exa_api_key = "{escaped}"')
    if config.firecrawl_api_key:
        escaped = config.firecrawl_api_key.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'firecrawl_api_key = "{escaped}"')
    if config.http_timeout != _DEFAULT_HTTP_TIMEOUT:
        lines.append(f"http_timeout = {config.http_timeout}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except OSError:
        logger.warning("Could not set file permissions on %s — file may be world-readable", path)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def get_config_locations() -> dict[str, dict[str, object]]:
    """Return a dict describing known config file locations and their status.

    Returns:
        Mapping from location label to ``{"path": Path, "exists": bool}``.
    """
    dotenv_path = Path.cwd() / ".env"
    return {
        "dotenv": {"path": dotenv_path, "exists": dotenv_path.exists()},
        "global_toml": {"path": _GLOBAL_CONFIG_FILE, "exists": _GLOBAL_CONFIG_FILE.exists()},
    }
