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
        ollama_host: Ollama server URL for offline models.
        db_path: Path to offline knowledge SQLite database.
        storage_tier: Storage tier name (ultra_compact, compact, standard, extended).
        default_compliance: Default compliance mode (general, hipaa, tactical, fedramp).
    """

    exa_api_key: str = ""
    firecrawl_api_key: str = ""
    http_timeout: float = _DEFAULT_HTTP_TIMEOUT
    ollama_host: str = "http://localhost:11434"
    db_path: str = "aipea_knowledge.db"
    storage_tier: str = "standard"
    default_compliance: str = "general"
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
                value = (
                    value.replace("\\\\", "\x00")
                    .replace('\\"', '"')
                    .replace("\\n", "\n")
                    .replace("\\r", "\r")
                    .replace("\x00", "\\")
                )
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


def _resolve_string(
    env_key: str,
    toml_key: str,
    default: str,
    dotenv_vals: dict[str, str],
    toml_vals: dict[str, str],
    sources: dict[str, str],
    dotenv_file: Path,
    toml_file: Path,
    *,
    valid_values: set[str] | None = None,
) -> str:
    """Resolve a string config value through the priority chain.

    Priority: env > .env > toml > default.
    If ``valid_values`` is set, values not in the set are ignored.
    """
    env_val = os.environ.get(env_key)
    if env_val is not None and (valid_values is None or env_val.lower() in valid_values):
        sources[toml_key] = "env"
        return env_val.lower() if valid_values else env_val
    if env_key in dotenv_vals:
        raw = dotenv_vals[env_key]
        if valid_values is None or raw.lower() in valid_values:
            sources[toml_key] = f"dotenv ({dotenv_file})"
            return raw.lower() if valid_values else raw
    if toml_key in toml_vals:
        raw = toml_vals[toml_key]
        if valid_values is None or raw.lower() in valid_values:
            sources[toml_key] = f"toml ({toml_file})"
            return raw.lower() if valid_values else raw
    sources[toml_key] = "default"
    return default


def _parse_timeout(raw: str) -> float:
    """Parse a timeout string, returning the default if invalid."""
    try:
        val = float(raw)
        return val if 0 < val < float("inf") else _DEFAULT_HTTP_TIMEOUT
    except (ValueError, TypeError):
        return _DEFAULT_HTTP_TIMEOUT


def _resolve_timeout(
    dotenv_vals: dict[str, str],
    toml_vals: dict[str, str],
    sources: dict[str, str],
    dotenv_file: Path,
    toml_file: Path,
) -> float:
    """Resolve http_timeout through the priority chain."""
    env_val = os.environ.get("AIPEA_HTTP_TIMEOUT")
    if env_val is not None:
        sources["http_timeout"] = "env"
        return _parse_timeout(env_val)
    if "AIPEA_HTTP_TIMEOUT" in dotenv_vals:
        sources["http_timeout"] = f"dotenv ({dotenv_file})"
        return _parse_timeout(dotenv_vals["AIPEA_HTTP_TIMEOUT"])
    if "http_timeout" in toml_vals:
        sources["http_timeout"] = f"toml ({toml_file})"
        return _parse_timeout(toml_vals["http_timeout"])
    sources["http_timeout"] = "default"
    return _DEFAULT_HTTP_TIMEOUT


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
        1. Environment variables
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

    # --- string fields (env > .env > toml > default) ---
    exa_key = _resolve_string(
        "EXA_API_KEY",
        "exa_api_key",
        "",
        dotenv_vals,
        toml_vals,
        sources,
        dotenv_file,
        toml_file,
    )
    firecrawl_key = _resolve_string(
        "FIRECRAWL_API_KEY",
        "firecrawl_api_key",
        "",
        dotenv_vals,
        toml_vals,
        sources,
        dotenv_file,
        toml_file,
    )
    ollama_host = _resolve_string(
        "AIPEA_OLLAMA_HOST",
        "ollama_host",
        "http://localhost:11434",
        dotenv_vals,
        toml_vals,
        sources,
        dotenv_file,
        toml_file,
    )
    db_path = _resolve_string(
        "AIPEA_DB_PATH",
        "db_path",
        "aipea_knowledge.db",
        dotenv_vals,
        toml_vals,
        sources,
        dotenv_file,
        toml_file,
    )
    storage_tier = _resolve_string(
        "AIPEA_STORAGE_TIER",
        "storage_tier",
        "standard",
        dotenv_vals,
        toml_vals,
        sources,
        dotenv_file,
        toml_file,
        valid_values={"ultra_compact", "compact", "standard", "extended"},
    )
    default_compliance = _resolve_string(
        "AIPEA_DEFAULT_COMPLIANCE",
        "default_compliance",
        "general",
        dotenv_vals,
        toml_vals,
        sources,
        dotenv_file,
        toml_file,
        valid_values={"general", "hipaa", "tactical", "fedramp"},
    )

    # --- http_timeout (special: needs float parsing + validation) ---
    http_timeout = _resolve_timeout(
        dotenv_vals,
        toml_vals,
        sources,
        dotenv_file,
        toml_file,
    )

    return AIPEAConfig(
        exa_api_key=exa_key,
        firecrawl_api_key=firecrawl_key,
        http_timeout=http_timeout,
        ollama_host=ollama_host,
        db_path=db_path,
        storage_tier=storage_tier,
        default_compliance=default_compliance,
        _sources=sources,
    )


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _escape_config_value(value: str) -> str:
    """Escape a value for safe inclusion in double-quoted .env or TOML strings."""
    result = (
        value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    )

    def _is_control(c: str) -> bool:
        o = ord(c)
        return o <= 0x08 or o in (0x0B, 0x0C) or 0x0E <= o <= 0x1F or o == 0x7F

    return "".join(f"\\u{ord(c):04x}" if _is_control(c) else c for c in result)


def save_dotenv(path: Path, config: AIPEAConfig) -> None:
    """Write configuration to a ``.env`` file with restricted permissions.

    Preserves any non-AIPEA keys already present in the file.

    Args:
        path: Target file path.
        config: Configuration to persist.
    """
    aipea_keys = {
        "EXA_API_KEY",
        "FIRECRAWL_API_KEY",
        "AIPEA_HTTP_TIMEOUT",
        "AIPEA_OLLAMA_HOST",
        "AIPEA_DB_PATH",
        "AIPEA_STORAGE_TIER",
        "AIPEA_DEFAULT_COMPLIANCE",
    }
    existing = _parse_dotenv(path)

    lines = [
        "# AIPEA Configuration",
        "# Generated by `aipea configure`",
        "",
    ]
    # Preserve non-AIPEA keys
    for key, value in existing.items():
        if key not in aipea_keys:
            lines.append(f'{key}="{_escape_config_value(value)}"')

    if config.exa_api_key:
        escaped = _escape_config_value(config.exa_api_key)
        lines.append(f'EXA_API_KEY="{escaped}"')
    if config.firecrawl_api_key:
        escaped = _escape_config_value(config.firecrawl_api_key)
        lines.append(f'FIRECRAWL_API_KEY="{escaped}"')
    if config.http_timeout != _DEFAULT_HTTP_TIMEOUT:
        lines.append(f"AIPEA_HTTP_TIMEOUT={config.http_timeout}")
    if config.ollama_host != "http://localhost:11434":
        escaped = _escape_config_value(config.ollama_host)
        lines.append(f'AIPEA_OLLAMA_HOST="{escaped}"')
    if config.db_path != "aipea_knowledge.db":
        escaped = _escape_config_value(config.db_path)
        lines.append(f'AIPEA_DB_PATH="{escaped}"')
    if config.storage_tier != "standard":
        lines.append(f"AIPEA_STORAGE_TIER={config.storage_tier}")
    if config.default_compliance != "general":
        lines.append(f"AIPEA_DEFAULT_COMPLIANCE={config.default_compliance}")
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
        escaped = _escape_config_value(config.exa_api_key)
        lines.append(f'exa_api_key = "{escaped}"')
    if config.firecrawl_api_key:
        escaped = _escape_config_value(config.firecrawl_api_key)
        lines.append(f'firecrawl_api_key = "{escaped}"')
    if config.http_timeout != _DEFAULT_HTTP_TIMEOUT:
        lines.append(f"http_timeout = {config.http_timeout}")
    if config.ollama_host != "http://localhost:11434":
        escaped = _escape_config_value(config.ollama_host)
        lines.append(f'ollama_host = "{escaped}"')
    if config.db_path != "aipea_knowledge.db":
        escaped = _escape_config_value(config.db_path)
        lines.append(f'db_path = "{escaped}"')
    if config.storage_tier != "standard":
        lines.append(f'storage_tier = "{config.storage_tier}"')
    if config.default_compliance != "general":
        lines.append(f'default_compliance = "{config.default_compliance}"')
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
