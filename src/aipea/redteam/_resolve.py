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
            over env + config when non-empty after whitespace strip.
            (Whitespace-pasted keys are a common real-world mistake;
            stripping both env and constructor keeps the two paths
            symmetric so the auth header doesn't silently get a leading
            space that the upstream API rejects with 401.)

    Returns:
        The resolved key, or empty string if not found anywhere.

        Empty string return — rather than raising — is a deliberate
        graceful-degradation choice for the redteam package so an
        absent or broken config layer doesn't propagate import-time
        errors to consumers that may not have an `aipea.config`. This
        differs from `src/aipea/search.py:_get_api_key` (which lets
        config-import / config-load exceptions bubble); see the
        ``except`` blocks below for the explicit deviation.
    """
    if constructor_value:
        stripped = constructor_value.strip()
        if stripped:
            return stripped

    env_value = os.environ.get(env_var, "").strip()
    if env_value:
        return env_value

    field = _API_KEY_FIELD_MAP.get(env_var)
    if field is None:
        return ""

    # Deviation from search.py:_get_api_key — defensive swallow of the
    # config-layer optional dep. Logged at DEBUG so the failure is visible
    # via `aipea --log-level debug` without forcing a stack trace on every
    # caller that doesn't have aipea.config installed.
    import logging as _logging

    log = _logging.getLogger(__name__)
    try:
        from aipea.config import load_config  # local import to avoid cycle
    except Exception as exc:
        log.debug("aipea.config import failed; treating %s as unset: %s", env_var, exc)
        return ""
    try:
        cfg = load_config()
    except Exception as exc:
        log.debug("aipea.config load failed; treating %s as unset: %s", env_var, exc)
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

    Note:
        Deliberate divergence from `src/aipea/search.py:_resolve_provider_url`,
        which uses `os.environ.get(env_var)` (any non-None value wins,
        including empty string). This helper strips + treats empty/
        whitespace as not-set, falling through to config/default. The
        whitespace-tolerant behavior prevents an empty-string env var
        from silently breaking downstream URL construction.
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
