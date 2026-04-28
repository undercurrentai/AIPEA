"""Provider URL + API-key resolution for the redteam package.

Mirrors the env > config > default chain in `src/aipea/search.py:45-124`.
Extends the field_map there with `ANTHROPIC_API_KEY` and `OPENAI_API_KEY`
which the search providers don't use.
"""

from __future__ import annotations

import os

# Env-var → config field name. Matches the precedent set by
# search.py's `_get_api_key()` field_map (`EXA_API_KEY` → `exa_api_key`,
# `FIRECRAWL_API_KEY` → `firecrawl_api_key`).
_API_KEY_FIELD_MAP: dict[str, str] = {
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "OPENAI_API_KEY": "openai_api_key",
}


def resolve_api_key(env_var: str, constructor_value: str | None = None) -> str:
    """Resolve an API key in priority order: constructor → env → config.

    Args:
        env_var: Name of the environment variable to check (e.g.
            ``ANTHROPIC_API_KEY``).
        constructor_value: Explicit value passed by the caller. Wins
            over env + config when not None and not the empty string.

    Returns:
        The resolved key, or empty string if not found anywhere. (Returning
        empty string rather than raising mirrors `search.py:_get_api_key`
        behavior so callers can degrade gracefully.)
    """
    if constructor_value:
        return constructor_value

    env_value = os.environ.get(env_var, "").strip()
    if env_value:
        return env_value

    field = _API_KEY_FIELD_MAP.get(env_var)
    if field is None:
        return ""

    try:
        from aipea.config import load_config  # local import to avoid cycle
    except Exception:
        return ""
    try:
        cfg = load_config()
    except Exception:
        return ""
    return str(getattr(cfg, field, "") or "")


def resolve_provider_url(
    env_var: str,
    config_field: str,
    default: str,
) -> str:
    """Resolve a provider base URL: env > config > default.

    Args:
        env_var: Environment variable name (e.g. ``AIPEA_OLLAMA_HOST``).
        config_field: Field name on the loaded config (e.g.
            ``ollama_host``).
        default: Default URL if neither env nor config sets one.

    Returns:
        The resolved URL string.
    """
    env_value = os.environ.get(env_var, "").strip()
    if env_value:
        return env_value
    try:
        from aipea.config import load_config

        cfg = load_config()
        cfg_value = getattr(cfg, config_field, None)
        if cfg_value:
            return str(cfg_value)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).debug("config lookup failed: %s", exc)
    return default
