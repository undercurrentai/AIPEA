"""Tests for aipea.config — configuration loading, parsing, and persistence."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from aipea.config import (
    AIPEAConfig,
    _parse_dotenv,
    _parse_toml_config,
    get_config_locations,
    load_config,
    save_dotenv,
    save_toml_config,
)

# ============================================================================
# AIPEAConfig dataclass
# ============================================================================


class TestAIPEAConfig:
    def test_defaults(self) -> None:
        cfg = AIPEAConfig()
        assert cfg.exa_api_key == ""
        assert cfg.firecrawl_api_key == ""
        assert cfg.http_timeout == 30.0
        assert cfg.ollama_host == "http://localhost:11434"
        assert cfg.db_path == "aipea_knowledge.db"
        assert cfg.storage_tier == "standard"
        assert cfg.default_compliance == "general"

    def test_has_exa(self) -> None:
        assert not AIPEAConfig().has_exa()
        assert AIPEAConfig(exa_api_key="abc").has_exa()

    def test_has_firecrawl(self) -> None:
        assert not AIPEAConfig().has_firecrawl()
        assert AIPEAConfig(firecrawl_api_key="abc").has_firecrawl()

    def test_redact_key_empty(self) -> None:
        assert AIPEAConfig.redact_key("") == "(not set)"

    def test_redact_key_short(self) -> None:
        assert AIPEAConfig.redact_key("short") == "****"

    def test_redact_key_long(self) -> None:
        assert AIPEAConfig.redact_key("abcdef123456") == "abcd...3456"

    def test_redact_key_exact_boundary(self) -> None:
        # 11 chars → short (< 12)
        assert AIPEAConfig.redact_key("12345678901") == "****"
        # 12 chars → redacted
        assert AIPEAConfig.redact_key("123456789012") == "1234...9012"


# ============================================================================
# .env parsing
# ============================================================================


class TestParseDotenv:
    def test_basic_key_value(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("EXA_API_KEY=mykey123\n")
        result = _parse_dotenv(env)
        assert result == {"EXA_API_KEY": "mykey123"}

    def test_double_quoted(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text('FIRECRAWL_API_KEY="fc_key_value"\n')
        result = _parse_dotenv(env)
        assert result == {"FIRECRAWL_API_KEY": "fc_key_value"}

    def test_single_quoted(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("EXA_API_KEY='exa_value'\n")
        result = _parse_dotenv(env)
        assert result == {"EXA_API_KEY": "exa_value"}

    def test_export_prefix(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("export EXA_API_KEY=exported_value\n")
        result = _parse_dotenv(env)
        assert result == {"EXA_API_KEY": "exported_value"}

    def test_comments_and_blanks(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("# This is a comment\n\nEXA_API_KEY=key\n# Another comment\n")
        result = _parse_dotenv(env)
        assert result == {"EXA_API_KEY": "key"}

    def test_inline_comment(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("AIPEA_HTTP_TIMEOUT=60 # seconds\n")
        result = _parse_dotenv(env)
        assert result == {"AIPEA_HTTP_TIMEOUT": "60"}

    def test_inline_comment_not_stripped_from_quoted(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text('EXA_API_KEY="key with # hash"\n')
        result = _parse_dotenv(env)
        assert result == {"EXA_API_KEY": "key with # hash"}

    def test_missing_file(self, tmp_path: Path) -> None:
        result = _parse_dotenv(tmp_path / "nonexistent")
        assert result == {}

    def test_no_equals(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("INVALID_LINE\nEXA_API_KEY=ok\n")
        result = _parse_dotenv(env)
        assert result == {"EXA_API_KEY": "ok"}

    def test_multiple_keys(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("EXA_API_KEY=exa\nFIRECRAWL_API_KEY=fc\nAIPEA_HTTP_TIMEOUT=45\n")
        result = _parse_dotenv(env)
        assert result == {
            "EXA_API_KEY": "exa",
            "FIRECRAWL_API_KEY": "fc",
            "AIPEA_HTTP_TIMEOUT": "45",
        }

    def test_empty_value(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("EXA_API_KEY=\n")
        result = _parse_dotenv(env)
        assert result == {"EXA_API_KEY": ""}

    def test_value_with_equals(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("EXA_API_KEY=abc=def\n")
        result = _parse_dotenv(env)
        assert result == {"EXA_API_KEY": "abc=def"}


# ============================================================================
# TOML parsing
# ============================================================================


class TestParseToml:
    def test_basic_toml(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.toml"
        cfg.write_text('[aipea]\nexa_api_key = "toml_key"\nhttp_timeout = 45\n')
        result = _parse_toml_config(cfg)
        assert result["exa_api_key"] == "toml_key"
        assert result["http_timeout"] == "45"

    def test_missing_file(self, tmp_path: Path) -> None:
        result = _parse_toml_config(tmp_path / "missing.toml")
        assert result == {}

    def test_corrupt_toml(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.toml"
        cfg.write_text("this is not [valid toml {{{\n")
        result = _parse_toml_config(cfg)
        assert result == {}

    def test_missing_aipea_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.toml"
        cfg.write_text('[other]\nkey = "value"\n')
        result = _parse_toml_config(cfg)
        assert result == {}

    def test_all_keys(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.toml"
        cfg.write_text(
            '[aipea]\nexa_api_key = "exa"\nfirecrawl_api_key = "fc"\nhttp_timeout = 60\n'
        )
        result = _parse_toml_config(cfg)
        assert result == {
            "exa_api_key": "exa",
            "firecrawl_api_key": "fc",
            "http_timeout": "60",
        }


# ============================================================================
# Priority chain (load_config)
# ============================================================================


class TestLoadConfig:
    def test_defaults_when_no_sources(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for var in (
            "EXA_API_KEY",
            "FIRECRAWL_API_KEY",
            "AIPEA_HTTP_TIMEOUT",
            "AIPEA_OLLAMA_HOST",
            "AIPEA_DB_PATH",
            "AIPEA_STORAGE_TIER",
            "AIPEA_DEFAULT_COMPLIANCE",
        ):
            monkeypatch.delenv(var, raising=False)
        cfg = load_config(
            dotenv_path=tmp_path / "no.env",
            toml_path=tmp_path / "no.toml",
        )
        assert cfg.exa_api_key == ""
        assert cfg.firecrawl_api_key == ""
        assert cfg.http_timeout == 30.0
        assert cfg.ollama_host == "http://localhost:11434"
        assert cfg.db_path == "aipea_knowledge.db"
        assert cfg.storage_tier == "standard"
        assert cfg.default_compliance == "general"

    def test_toml_provides_values(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        toml = tmp_path / "config.toml"
        toml.write_text('[aipea]\nexa_api_key = "from_toml"\nhttp_timeout = 99\n')

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=toml)
        assert cfg.exa_api_key == "from_toml"
        assert cfg.http_timeout == 99.0
        assert "toml" in cfg._sources["exa_api_key"]

    def test_dotenv_overrides_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        toml = tmp_path / "config.toml"
        toml.write_text('[aipea]\nexa_api_key = "from_toml"\n')

        env = tmp_path / ".env"
        env.write_text("EXA_API_KEY=from_dotenv\n")

        cfg = load_config(dotenv_path=env, toml_path=toml)
        assert cfg.exa_api_key == "from_dotenv"
        assert "dotenv" in cfg._sources["exa_api_key"]

    def test_env_overrides_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EXA_API_KEY", "from_env")
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        env = tmp_path / ".env"
        env.write_text("EXA_API_KEY=from_dotenv\n")

        cfg = load_config(dotenv_path=env, toml_path=tmp_path / "no.toml")
        assert cfg.exa_api_key == "from_env"
        assert cfg._sources["exa_api_key"] == "env"

    def test_env_timeout_validation(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIPEA_HTTP_TIMEOUT", "not_a_number")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.http_timeout == 30.0  # fallback to default

    def test_env_timeout_zero(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIPEA_HTTP_TIMEOUT", "0")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.http_timeout == 30.0  # 0 is invalid

    def test_env_timeout_negative(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIPEA_HTTP_TIMEOUT", "-5")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.http_timeout == 30.0

    def test_env_timeout_inf(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIPEA_HTTP_TIMEOUT", "inf")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.http_timeout == 30.0

    def test_dotenv_timeout_invalid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        env = tmp_path / ".env"
        env.write_text("AIPEA_HTTP_TIMEOUT=bad\n")

        cfg = load_config(dotenv_path=env, toml_path=tmp_path / "no.toml")
        assert cfg.http_timeout == 30.0

    def test_toml_timeout_invalid(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        toml = tmp_path / "config.toml"
        toml.write_text('[aipea]\nhttp_timeout = "bad_value"\n')

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=toml)
        assert cfg.http_timeout == 30.0

    def test_ollama_host_from_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIPEA_OLLAMA_HOST", "http://remote:11434")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.ollama_host == "http://remote:11434"
        assert cfg._sources["ollama_host"] == "env"

    def test_ollama_host_default(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AIPEA_OLLAMA_HOST", raising=False)
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.ollama_host == "http://localhost:11434"

    def test_db_path_from_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIPEA_DB_PATH", "/data/custom.db")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.delenv("AIPEA_OLLAMA_HOST", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.db_path == "/data/custom.db"
        assert cfg._sources["db_path"] == "env"

    def test_storage_tier_from_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIPEA_STORAGE_TIER", "compact")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.delenv("AIPEA_OLLAMA_HOST", raising=False)
        monkeypatch.delenv("AIPEA_DB_PATH", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.storage_tier == "compact"

    def test_storage_tier_invalid_falls_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AIPEA_STORAGE_TIER", "invalid_tier")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.delenv("AIPEA_OLLAMA_HOST", raising=False)
        monkeypatch.delenv("AIPEA_DB_PATH", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.storage_tier == "standard"  # falls back to default

    def test_default_compliance_from_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AIPEA_DEFAULT_COMPLIANCE", "hipaa")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.delenv("AIPEA_OLLAMA_HOST", raising=False)
        monkeypatch.delenv("AIPEA_DB_PATH", raising=False)
        monkeypatch.delenv("AIPEA_STORAGE_TIER", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.default_compliance == "hipaa"

    def test_default_compliance_invalid_falls_back(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AIPEA_DEFAULT_COMPLIANCE", "bogus")
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.delenv("AIPEA_OLLAMA_HOST", raising=False)
        monkeypatch.delenv("AIPEA_DB_PATH", raising=False)
        monkeypatch.delenv("AIPEA_STORAGE_TIER", raising=False)

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=tmp_path / "no.toml")
        assert cfg.default_compliance == "general"  # falls back to default

    def test_new_vars_from_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.delenv("AIPEA_OLLAMA_HOST", raising=False)
        monkeypatch.delenv("AIPEA_DB_PATH", raising=False)
        monkeypatch.delenv("AIPEA_STORAGE_TIER", raising=False)
        monkeypatch.delenv("AIPEA_DEFAULT_COMPLIANCE", raising=False)

        env = tmp_path / ".env"
        env.write_text(
            "AIPEA_OLLAMA_HOST=http://dotenv:11434\n"
            "AIPEA_DB_PATH=/dotenv/kb.db\n"
            "AIPEA_STORAGE_TIER=extended\n"
            "AIPEA_DEFAULT_COMPLIANCE=tactical\n"
        )

        cfg = load_config(dotenv_path=env, toml_path=tmp_path / "no.toml")
        assert cfg.ollama_host == "http://dotenv:11434"
        assert cfg.db_path == "/dotenv/kb.db"
        assert cfg.storage_tier == "extended"
        assert cfg.default_compliance == "tactical"

    def test_new_vars_from_toml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.delenv("AIPEA_OLLAMA_HOST", raising=False)
        monkeypatch.delenv("AIPEA_DB_PATH", raising=False)
        monkeypatch.delenv("AIPEA_STORAGE_TIER", raising=False)
        monkeypatch.delenv("AIPEA_DEFAULT_COMPLIANCE", raising=False)

        toml = tmp_path / "config.toml"
        toml.write_text(
            "[aipea]\n"
            'ollama_host = "http://toml:11434"\n'
            'db_path = "/toml/kb.db"\n'
            'storage_tier = "compact"\n'
            'default_compliance = "fedramp"\n'
        )

        cfg = load_config(dotenv_path=tmp_path / "no.env", toml_path=toml)
        assert cfg.ollama_host == "http://toml:11434"
        assert cfg.db_path == "/toml/kb.db"
        assert cfg.storage_tier == "compact"
        assert cfg.default_compliance == "fedramp"

    def test_full_priority_chain(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """env > dotenv > toml > default — test all layers active."""
        monkeypatch.setenv("EXA_API_KEY", "env_exa")
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        toml = tmp_path / "config.toml"
        toml.write_text(
            '[aipea]\nexa_api_key = "toml_exa"\nfirecrawl_api_key = "toml_fc"\nhttp_timeout = 99\n'
        )

        env = tmp_path / ".env"
        env.write_text("FIRECRAWL_API_KEY=dotenv_fc\nAIPEA_HTTP_TIMEOUT=60\n")

        cfg = load_config(dotenv_path=env, toml_path=toml)
        assert cfg.exa_api_key == "env_exa"  # env wins
        assert cfg.firecrawl_api_key == "dotenv_fc"  # dotenv wins over toml
        assert cfg.http_timeout == 60.0  # dotenv wins over toml


# ============================================================================
# File writing
# ============================================================================


class TestSaveDotenv:
    def test_writes_file(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        cfg = AIPEAConfig(exa_api_key="exa123", firecrawl_api_key="fc456", http_timeout=60.0)
        save_dotenv(target, cfg)

        content = target.read_text()
        assert 'EXA_API_KEY="exa123"' in content
        assert 'FIRECRAWL_API_KEY="fc456"' in content
        assert "AIPEA_HTTP_TIMEOUT=60.0" in content

    def test_permissions(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        cfg = AIPEAConfig(exa_api_key="key")
        save_dotenv(target, cfg)

        mode = target.stat().st_mode
        assert mode & stat.S_IRUSR  # owner read
        assert mode & stat.S_IWUSR  # owner write
        assert not (mode & stat.S_IRGRP)  # no group read
        assert not (mode & stat.S_IROTH)  # no other read

    def test_omits_defaults(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        cfg = AIPEAConfig()  # all defaults
        save_dotenv(target, cfg)

        content = target.read_text()
        assert "EXA_API_KEY" not in content
        assert "FIRECRAWL_API_KEY" not in content
        assert "AIPEA_HTTP_TIMEOUT" not in content

    def test_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        target = tmp_path / ".env"
        original = AIPEAConfig(exa_api_key="round_trip", http_timeout=45.0)
        save_dotenv(target, original)

        loaded = load_config(dotenv_path=target, toml_path=tmp_path / "no.toml")
        assert loaded.exa_api_key == "round_trip"
        assert loaded.http_timeout == 45.0

    def test_escapes_quotes_in_keys(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Keys containing double-quotes are escaped so the .env file is valid."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        target = tmp_path / ".env"
        key_with_quote = 'key_with"quote'
        save_dotenv(target, AIPEAConfig(exa_api_key=key_with_quote))

        loaded = load_config(dotenv_path=target, toml_path=tmp_path / "no.toml")
        assert loaded.exa_api_key == key_with_quote

    def test_escapes_backslash_in_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Keys containing backslashes are escaped so the .env file is valid."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        target = tmp_path / ".env"
        key_with_backslash = "key_with\\backslash"
        save_dotenv(target, AIPEAConfig(exa_api_key=key_with_backslash))

        content = target.read_text()
        # The raw file should have escaped backslash
        assert "key_with\\\\backslash" in content

    def test_escapes_newline_in_keys(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Keys containing newlines are escaped for valid .env file (bug #40)."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        target = tmp_path / ".env"
        key_with_newline = "abc\ndef"
        save_dotenv(target, AIPEAConfig(exa_api_key=key_with_newline))

        content = target.read_text()
        # Raw file should have escaped newline (literal \n, not actual newline)
        assert "abc\\ndef" in content
        # Should NOT contain a literal newline inside the value
        for line in content.splitlines():
            if line.startswith("EXA_API_KEY="):
                assert "\n" not in line.split("=", 1)[1]

    def test_newline_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Newline in key survives save/load round-trip (bug #40)."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        target = tmp_path / ".env"
        key_with_newline = "abc\ndef"
        save_dotenv(target, AIPEAConfig(exa_api_key=key_with_newline))

        monkeypatch.chdir(tmp_path)
        loaded = load_config()
        assert loaded.exa_api_key == key_with_newline


class TestSaveToml:
    def test_writes_file(self, tmp_path: Path) -> None:
        target = tmp_path / "config.toml"
        cfg = AIPEAConfig(exa_api_key="exa_toml", http_timeout=50.0)
        save_toml_config(target, cfg)

        content = target.read_text()
        assert "[aipea]" in content
        assert 'exa_api_key = "exa_toml"' in content
        assert "http_timeout = 50.0" in content

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "subdir" / "config.toml"
        cfg = AIPEAConfig(exa_api_key="test")
        save_toml_config(target, cfg)
        assert target.exists()

    def test_permissions(self, tmp_path: Path) -> None:
        target = tmp_path / "config.toml"
        cfg = AIPEAConfig(exa_api_key="key")
        save_toml_config(target, cfg)

        mode = target.stat().st_mode
        assert mode & stat.S_IRUSR
        assert mode & stat.S_IWUSR
        assert not (mode & stat.S_IRGRP)

    def test_roundtrip(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        target = tmp_path / "config.toml"
        original = AIPEAConfig(
            exa_api_key="rt_exa",
            firecrawl_api_key="rt_fc",
            http_timeout=77.0,
        )
        save_toml_config(target, original)

        loaded = load_config(dotenv_path=tmp_path / "no.env", toml_path=target)
        assert loaded.exa_api_key == "rt_exa"
        assert loaded.firecrawl_api_key == "rt_fc"
        assert loaded.http_timeout == 77.0

    def test_escapes_quotes_in_keys(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Keys containing double-quotes produce valid TOML that round-trips."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        target = tmp_path / "config.toml"
        key_with_quote = 'key_with"quote'
        save_toml_config(target, AIPEAConfig(exa_api_key=key_with_quote))

        loaded = load_config(dotenv_path=tmp_path / "no.env", toml_path=target)
        assert loaded.exa_api_key == key_with_quote

    def test_escapes_backslash_in_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Keys containing backslashes produce valid TOML that round-trips."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        target = tmp_path / "config.toml"
        key_with_backslash = "key_with\\backslash"
        save_toml_config(target, AIPEAConfig(exa_api_key=key_with_backslash))

        loaded = load_config(dotenv_path=tmp_path / "no.env", toml_path=target)
        assert loaded.exa_api_key == key_with_backslash


# ============================================================================
# Config locations
# ============================================================================


# ============================================================================
# BUG-HUNT REGRESSION: save_dotenv preserves non-AIPEA keys
# ============================================================================


class TestSaveDotenvPreservesKeys:
    """Regression tests for save_dotenv not destroying non-AIPEA environment vars."""

    def test_preserves_existing_non_aipea_keys(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text('DATABASE_URL="postgres://localhost/mydb"\nSECRET_KEY="abc123"\n')

        config = AIPEAConfig(exa_api_key="test-exa-key")
        save_dotenv(env_file, config)

        content = env_file.read_text()
        assert "DATABASE_URL" in content
        assert "SECRET_KEY" in content
        assert "EXA_API_KEY" in content

    def test_empty_file_still_works(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        config = AIPEAConfig(exa_api_key="test-key")
        save_dotenv(env_file, config)

        content = env_file.read_text()
        assert "EXA_API_KEY" in content

    def test_updates_aipea_keys_in_place(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text('EXA_API_KEY="old-key"\nMY_VAR="keep"\n')

        config = AIPEAConfig(exa_api_key="new-key")
        save_dotenv(env_file, config)

        content = env_file.read_text()
        assert "MY_VAR" in content
        assert "new-key" in content
        assert "old-key" not in content


# ============================================================================
# Config locations
# ============================================================================


class TestGetConfigLocations:
    def test_returns_both_locations(self) -> None:
        locations = get_config_locations()
        assert "dotenv" in locations
        assert "global_toml" in locations
        assert "path" in locations["dotenv"]
        assert "exists" in locations["dotenv"]


# ============================================================================
# save_dotenv / save_toml_config: new v1.3.0 fields
# ============================================================================


class TestSaveNewConfigFields:
    """Ensure new v1.3.0 config fields are persisted by save_dotenv and save_toml_config."""

    @pytest.mark.unit
    def test_dotenv_writes_new_fields(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        cfg = AIPEAConfig(
            ollama_host="http://remote:11434",
            db_path="/data/kb.db",
            storage_tier="extended",
            default_compliance="hipaa",
        )
        save_dotenv(target, cfg)

        content = target.read_text()
        assert 'AIPEA_OLLAMA_HOST="http://remote:11434"' in content
        assert 'AIPEA_DB_PATH="/data/kb.db"' in content
        assert "AIPEA_STORAGE_TIER=extended" in content
        assert "AIPEA_DEFAULT_COMPLIANCE=hipaa" in content

    @pytest.mark.unit
    def test_dotenv_omits_default_new_fields(self, tmp_path: Path) -> None:
        target = tmp_path / ".env"
        cfg = AIPEAConfig()  # all defaults
        save_dotenv(target, cfg)

        content = target.read_text()
        assert "AIPEA_OLLAMA_HOST" not in content
        assert "AIPEA_DB_PATH" not in content
        assert "AIPEA_STORAGE_TIER" not in content
        assert "AIPEA_DEFAULT_COMPLIANCE" not in content

    @pytest.mark.unit
    def test_toml_writes_new_fields(self, tmp_path: Path) -> None:
        target = tmp_path / "config.toml"
        cfg = AIPEAConfig(
            ollama_host="http://remote:11434",
            db_path="/data/kb.db",
            storage_tier="compact",
            default_compliance="tactical",
        )
        save_toml_config(target, cfg)

        content = target.read_text()
        assert 'ollama_host = "http://remote:11434"' in content
        assert 'db_path = "/data/kb.db"' in content
        assert 'storage_tier = "compact"' in content
        assert 'default_compliance = "tactical"' in content

    @pytest.mark.unit
    def test_toml_omits_default_new_fields(self, tmp_path: Path) -> None:
        target = tmp_path / "config.toml"
        cfg = AIPEAConfig()  # all defaults
        save_toml_config(target, cfg)

        content = target.read_text()
        assert "ollama_host" not in content
        assert "db_path" not in content
        assert "storage_tier" not in content
        assert "default_compliance" not in content

    @pytest.mark.unit
    def test_dotenv_roundtrip_new_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for var in (
            "EXA_API_KEY",
            "FIRECRAWL_API_KEY",
            "AIPEA_HTTP_TIMEOUT",
            "AIPEA_OLLAMA_HOST",
            "AIPEA_DB_PATH",
            "AIPEA_STORAGE_TIER",
            "AIPEA_DEFAULT_COMPLIANCE",
        ):
            monkeypatch.delenv(var, raising=False)

        target = tmp_path / ".env"
        original = AIPEAConfig(
            ollama_host="http://gpu:11434",
            db_path="/data/test.db",
            storage_tier="compact",
            default_compliance="hipaa",
        )
        save_dotenv(target, original)

        loaded = load_config(dotenv_path=target, toml_path=tmp_path / "no.toml")
        assert loaded.ollama_host == "http://gpu:11434"
        assert loaded.db_path == "/data/test.db"
        assert loaded.storage_tier == "compact"
        assert loaded.default_compliance == "hipaa"

    @pytest.mark.unit
    def test_toml_roundtrip_new_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for var in (
            "EXA_API_KEY",
            "FIRECRAWL_API_KEY",
            "AIPEA_HTTP_TIMEOUT",
            "AIPEA_OLLAMA_HOST",
            "AIPEA_DB_PATH",
            "AIPEA_STORAGE_TIER",
            "AIPEA_DEFAULT_COMPLIANCE",
        ):
            monkeypatch.delenv(var, raising=False)

        target = tmp_path / "config.toml"
        original = AIPEAConfig(
            ollama_host="http://gpu:11434",
            db_path="/data/test.db",
            storage_tier="extended",
            default_compliance="tactical",
        )
        save_toml_config(target, original)

        loaded = load_config(dotenv_path=tmp_path / "no.env", toml_path=target)
        assert loaded.ollama_host == "http://gpu:11434"
        assert loaded.db_path == "/data/test.db"
        assert loaded.storage_tier == "extended"
        assert loaded.default_compliance == "tactical"


# =============================================================================
# REGRESSION TESTS (bug-hunt wave 14)
# =============================================================================


class TestEscapeConfigValueControlChars:
    """Regression: _escape_config_value did not escape TOML-illegal control chars."""

    @pytest.mark.unit
    def test_null_byte_escaped(self) -> None:
        from aipea.config import _escape_config_value

        result = _escape_config_value("abc\x00def")
        assert "\x00" not in result
        assert "\\u0000" in result

    @pytest.mark.unit
    def test_backspace_escaped(self) -> None:
        from aipea.config import _escape_config_value

        result = _escape_config_value("abc\x08def")
        assert "\x08" not in result
        assert "\\u0008" in result

    @pytest.mark.unit
    def test_form_feed_escaped(self) -> None:
        from aipea.config import _escape_config_value

        result = _escape_config_value("abc\x0cdef")
        assert "\x0c" not in result
        assert "\\u000c" in result

    @pytest.mark.unit
    def test_normal_chars_unaffected(self) -> None:
        from aipea.config import _escape_config_value

        result = _escape_config_value("normal ASCII key 12345")
        assert result == "normal ASCII key 12345"

    @pytest.mark.unit
    def test_tab_preserved(self) -> None:
        from aipea.config import _escape_config_value

        result = _escape_config_value("has\ttab")
        # Tab (U+0009) is allowed in TOML basic strings
        assert "\t" in result


# ============================================================================
# API URL config chain (#73)
# ============================================================================


class TestApiUrlConfig:
    """Regression tests: API URLs must resolve through the config chain."""

    @pytest.mark.unit
    def test_default_exa_api_url(self) -> None:
        from aipea.config import AIPEAConfig

        cfg = AIPEAConfig()
        assert cfg.exa_api_url == "https://api.exa.ai/search"

    @pytest.mark.unit
    def test_default_firecrawl_api_url(self) -> None:
        from aipea.config import AIPEAConfig

        cfg = AIPEAConfig()
        assert cfg.firecrawl_api_url == "https://api.firecrawl.dev/v1/search"

    @pytest.mark.unit
    def test_env_override_exa_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from aipea.config import load_config

        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.setenv("AIPEA_EXA_API_URL", "https://custom.exa.test/search")
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert cfg.exa_api_url == "https://custom.exa.test/search"

    @pytest.mark.unit
    def test_env_override_firecrawl_url(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from aipea.config import load_config

        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.setenv("AIPEA_FIRECRAWL_API_URL", "https://custom.fc.test/v1/search")
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert cfg.firecrawl_api_url == "https://custom.fc.test/v1/search"

    @pytest.mark.unit
    def test_dotenv_override_exa_url(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from aipea.config import load_config

        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_EXA_API_URL", raising=False)
        dotenv = tmp_path / ".env"
        dotenv.write_text('AIPEA_EXA_API_URL="https://dotenv.exa.test/search"\n')
        cfg = load_config(dotenv_path=dotenv)
        assert cfg.exa_api_url == "https://dotenv.exa.test/search"

    @pytest.mark.unit
    def test_save_dotenv_round_trip_url(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from aipea.config import AIPEAConfig, load_config, save_dotenv

        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_EXA_API_URL", raising=False)
        monkeypatch.delenv("AIPEA_FIRECRAWL_API_URL", raising=False)

        cfg = AIPEAConfig(
            exa_api_url="https://custom.exa.test/search",
            firecrawl_api_url="https://custom.fc.test/v1/search",
        )
        dotenv = tmp_path / ".env"
        save_dotenv(dotenv, cfg)
        loaded = load_config(dotenv_path=dotenv)
        assert loaded.exa_api_url == "https://custom.exa.test/search"
        assert loaded.firecrawl_api_url == "https://custom.fc.test/v1/search"

    @pytest.mark.unit
    def test_save_toml_round_trip_url(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from aipea.config import AIPEAConfig, load_config, save_toml_config

        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_EXA_API_URL", raising=False)
        monkeypatch.delenv("AIPEA_FIRECRAWL_API_URL", raising=False)

        cfg = AIPEAConfig(
            exa_api_url="https://custom.exa.test/search",
            firecrawl_api_url="https://custom.fc.test/v1/search",
        )
        toml_path = tmp_path / "config.toml"
        save_toml_config(toml_path, cfg)
        loaded = load_config(toml_path=toml_path, dotenv_path=tmp_path / "nonexistent.env")
        assert loaded.exa_api_url == "https://custom.exa.test/search"
        assert loaded.firecrawl_api_url == "https://custom.fc.test/v1/search"


# ============================================================================
# Regression: dotenv parser edge cases with quoted values
# ============================================================================


class TestDotenvQuoteEdgeCases:
    """Regression tests for dotenv parser handling of quoted values."""

    def test_simple_double_quoted(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="simple_value"\n')
        result = _parse_dotenv(env_file)
        assert result["KEY"] == "simple_value"

    def test_simple_single_quoted(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY='simple_value'\n")
        result = _parse_dotenv(env_file)
        assert result["KEY"] == "simple_value"

    def test_value_with_embedded_matching_quote_at_end(self, tmp_path: Path) -> None:
        """Value like 'val1' 'val2' should extract only val1 (first quoted segment)."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY='val1' 'val2'\n")
        result = _parse_dotenv(env_file)
        assert result["KEY"] == "val1"

    def test_escaped_quote_in_double_quoted(self, tmp_path: Path) -> None:
        """Escaped quotes inside double-quoted values should be preserved."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="he said \\"hello\\""\n')
        result = _parse_dotenv(env_file)
        assert result["KEY"] == 'he said "hello"'

    def test_no_closing_quote_treated_as_unquoted(self, tmp_path: Path) -> None:
        """Missing closing quote should treat value as unquoted."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY='no_closing_quote\n")
        result = _parse_dotenv(env_file)
        assert result["KEY"] == "'no_closing_quote"

    def test_no_closing_double_quote_no_unescape(self, tmp_path: Path) -> None:
        """Missing closing double-quote should NOT unescape \\n sequences."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="path\\nvalue\n')
        result = _parse_dotenv(env_file)
        # Should be the raw string with leading quote, NOT a newline-expanded value
        assert result["KEY"] == '"path\\nvalue'
        assert "\n" not in result["KEY"]  # no newline expansion


# ============================================================================
# REGRESSION TESTS — Wave 18 #94
# ============================================================================


class TestWave18UnicodeEscapeDecode:
    """Regression: _parse_dotenv must decode \\uXXXX escapes emitted by
    _escape_config_value, so control characters in API keys round-trip
    correctly between save_dotenv / load_config. (Bug #94)
    """

    def test_parse_decodes_unicode_escape(self, tmp_path: Path) -> None:
        """\\u0001 in a double-quoted value decodes to U+0001."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="value\\u0001x"\n')
        result = _parse_dotenv(env_file)
        assert result["KEY"] == "value\x01x"

    def test_parse_decodes_multiple_unicode_escapes(self, tmp_path: Path) -> None:
        """Multiple \\uXXXX sequences all decode."""
        env_file = tmp_path / ".env"
        env_file.write_text('KEY="a\\u0001b\\u001fc\\u007fd"\n')
        result = _parse_dotenv(env_file)
        assert result["KEY"] == "a\x01b\x1fc\x7fd"

    def test_literal_backslash_u_not_decoded(self, tmp_path: Path) -> None:
        """A literal backslash followed by u0041 (escaped \\\\u0041) must NOT become 'A'.

        The \\\\ protection sentinel ensures literal backslashes survive the
        unicode-escape pass unchanged.
        """
        env_file = tmp_path / ".env"
        # In the file: KEY="\\u0041" — that's an escaped backslash + literal "u0041"
        env_file.write_text('KEY="\\\\u0041"\n')
        result = _parse_dotenv(env_file)
        assert result["KEY"] == "\\u0041"  # literal backslash + "u0041"

    def test_round_trip_control_characters(self, tmp_path: Path) -> None:
        """save_dotenv + _parse_dotenv round-trips control characters."""
        env_file = tmp_path / ".env"
        original_key = "key\x01with\x1fcontrol\x7fchars"
        cfg = AIPEAConfig(exa_api_key=original_key)
        save_dotenv(env_file, cfg)
        parsed = _parse_dotenv(env_file)
        assert parsed["EXA_API_KEY"] == original_key

    def test_round_trip_toml_control_characters(self, tmp_path: Path) -> None:
        """save_toml_config + _parse_toml_config round-trips control characters."""
        toml_file = tmp_path / "config.toml"
        original_key = "firecrawl\x01key\x1fwith\x7fcontrol"
        cfg = AIPEAConfig(firecrawl_api_key=original_key)
        save_toml_config(toml_file, cfg)
        parsed = _parse_toml_config(toml_file)
        assert parsed["firecrawl_api_key"] == original_key


# ============================================================================
# REGRESSION TESTS — Wave 18 #91
# ============================================================================


class TestWave18AtomicWrite:
    """Regression: save_dotenv and save_toml_config must write secret files
    with ``0o600`` permissions from the first byte (no umask race). (Bug #91)
    """

    def test_dotenv_has_0o600_permissions_on_unix(self, tmp_path: Path) -> None:
        """After save_dotenv, the .env file must have mode 0o600 on POSIX."""
        import os as _os
        import sys

        if sys.platform == "win32":
            pytest.skip("POSIX permissions do not apply to Windows")
        env_file = tmp_path / ".env"
        cfg = AIPEAConfig(exa_api_key="test-key")
        save_dotenv(env_file, cfg)
        mode = _os.stat(env_file).st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    def test_toml_has_0o600_permissions_on_unix(self, tmp_path: Path) -> None:
        """After save_toml_config, the TOML file must have mode 0o600 on POSIX."""
        import os as _os
        import sys

        if sys.platform == "win32":
            pytest.skip("POSIX permissions do not apply to Windows")
        toml_file = tmp_path / "config.toml"
        cfg = AIPEAConfig(firecrawl_api_key="test-key")
        save_toml_config(toml_file, cfg)
        mode = _os.stat(toml_file).st_mode & 0o777
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"

    def test_dotenv_content_written_correctly(self, tmp_path: Path) -> None:
        """Atomic write produces identical content to the old write_text path."""
        env_file = tmp_path / ".env"
        cfg = AIPEAConfig(exa_api_key="exa-123", firecrawl_api_key="fc-456")
        save_dotenv(env_file, cfg)
        content = env_file.read_text(encoding="utf-8")
        assert 'EXA_API_KEY="exa-123"' in content
        assert 'FIRECRAWL_API_KEY="fc-456"' in content

    def test_no_temp_file_leaked_on_success(self, tmp_path: Path) -> None:
        """A successful save must leave no .env.*.tmp files behind."""
        env_file = tmp_path / ".env"
        cfg = AIPEAConfig(exa_api_key="abc")
        save_dotenv(env_file, cfg)
        leftover = list(tmp_path.glob(".env.*.tmp"))
        assert leftover == []

    def test_temp_file_cleaned_up_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If os.replace fails, the temp file must be unlinked and no target created."""
        env_file = tmp_path / ".env"
        cfg = AIPEAConfig(exa_api_key="abc")

        original_replace = os.replace

        def boom(src: object, dst: object) -> None:
            raise OSError("simulated failure")

        monkeypatch.setattr("aipea.config.os.replace", boom)
        with pytest.raises(OSError, match="simulated failure"):
            save_dotenv(env_file, cfg)
        # Temp file cleaned up
        leftover = list(tmp_path.glob(".env.*.tmp"))
        assert leftover == []
        # Target not created
        assert not env_file.exists()
        # Sanity: original os.replace still importable
        _ = original_replace


class TestWave19ParseDotenvBom:
    """Regression for bug #104: `_parse_dotenv` used `encoding="utf-8"` and
    then relied on `line.strip()` to clean each line. Neither step removes
    the UTF-8 BOM (U+FEFF) that Windows editors like Notepad often emit,
    so the first key in a BOM-prefixed `.env` was parsed as `\\ufeffKEY`
    instead of `KEY`. Fix: use the `utf-8-sig` codec which transparently
    strips a leading BOM and behaves identically to `utf-8` otherwise."""

    def test_bom_prefixed_env_parses_cleanly(self, tmp_path: Path) -> None:
        """A .env with a leading UTF-8 BOM must parse without the BOM in keys."""
        env_file = tmp_path / ".env"
        # Write content with explicit BOM
        env_file.write_bytes(b"\xef\xbb\xbfEXA_API_KEY=sk-test-123\n")
        parsed = _parse_dotenv(env_file)
        assert "EXA_API_KEY" in parsed
        assert "\ufeffEXA_API_KEY" not in parsed
        assert parsed["EXA_API_KEY"] == "sk-test-123"

    def test_non_bom_env_still_parses(self, tmp_path: Path) -> None:
        """Regular UTF-8 (no BOM) must still work."""
        env_file = tmp_path / ".env"
        env_file.write_text("EXA_API_KEY=sk-no-bom\n", encoding="utf-8")
        parsed = _parse_dotenv(env_file)
        assert parsed["EXA_API_KEY"] == "sk-no-bom"

    def test_bom_round_trip_through_save_dotenv(self, tmp_path: Path) -> None:
        """A BOM-prefixed .env written back via save_dotenv must emerge clean
        and the key must not be duplicated under the BOM-decorated name."""
        env_file = tmp_path / ".env"
        env_file.write_bytes(
            b"\xef\xbb\xbfEXA_API_KEY=old-value\nDATABASE_URL=postgres://host/db\n"
        )
        cfg = AIPEAConfig(exa_api_key="new-value")
        save_dotenv(env_file, cfg)
        rewritten = _parse_dotenv(env_file)
        # EXA_API_KEY updated to new value, not duplicated under BOM key.
        assert rewritten["EXA_API_KEY"] == "new-value"
        assert "\ufeffEXA_API_KEY" not in rewritten
        # Preserved non-AIPEA key.
        assert rewritten["DATABASE_URL"] == "postgres://host/db"


class TestWave19SaveDotenvStrictRead:
    """Regression for bug #99: `_parse_dotenv` caught `OSError` and
    returned `{}`, making "missing file" and "permission denied"
    indistinguishable to `save_dotenv`. A user whose `.env` had been
    locked down (e.g. `chmod 200` or root-owned in a user-writable dir)
    would run `aipea configure` and silently lose every non-AIPEA line in
    the file — `os.replace` only needs parent-directory write permission,
    so the destructive rewrite always succeeded. Fix: `save_dotenv` passes
    `strict=True` to `_parse_dotenv`, causing a `PermissionError` /
    `OSError` on an existing-but-unreadable file to propagate rather than
    silently erasing the user's non-AIPEA keys."""

    def test_save_dotenv_raises_on_unreadable_existing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unreadable existing .env must raise, not silently destroy keys."""
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgres://host/db\n", encoding="utf-8")

        # Monkey-patch Path.read_text to simulate PermissionError only for
        # our target file. Direct interception is deterministic regardless
        # of runner euid and cross-platform filesystem semantics.
        real_read_text = Path.read_text

        def fake_read_text(self: Path, *args: object, **kwargs: object) -> str:
            if self == env_file:
                raise PermissionError(f"simulated: cannot read {self}")
            return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", fake_read_text)

        cfg = AIPEAConfig(exa_api_key="new-key")
        with pytest.raises(PermissionError, match="simulated"):
            save_dotenv(env_file, cfg)

        # Restore before reading to verify target is untouched.
        monkeypatch.setattr(Path, "read_text", real_read_text)
        # Original content must survive — no silent destruction.
        surviving = env_file.read_text(encoding="utf-8")
        assert "DATABASE_URL=postgres://host/db" in surviving

    def test_save_dotenv_succeeds_on_missing_file(self, tmp_path: Path) -> None:
        """If the .env doesn't exist, save_dotenv must still create it."""
        env_file = tmp_path / ".env"
        assert not env_file.exists()
        cfg = AIPEAConfig(exa_api_key="fresh-key")
        save_dotenv(env_file, cfg)
        assert env_file.exists()
        parsed = _parse_dotenv(env_file)
        assert parsed["EXA_API_KEY"] == "fresh-key"

    def test_parse_dotenv_strict_true_propagates_permission_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """strict=True must raise on PermissionError; default False swallows."""
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\n", encoding="utf-8")
        real_read_text = Path.read_text

        def fake_read_text(self: Path, *args: object, **kwargs: object) -> str:
            if self == env_file:
                raise PermissionError("no read")
            return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", fake_read_text)

        # Default: silent empty dict
        assert _parse_dotenv(env_file) == {}
        # Strict: raises
        with pytest.raises(PermissionError):
            _parse_dotenv(env_file, strict=True)

    def test_parse_dotenv_strict_true_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """strict=True on a missing file still returns {} (FileNotFoundError path)."""
        env_file = tmp_path / "does-not-exist.env"
        assert _parse_dotenv(env_file, strict=True) == {}


class TestUltrathinkTomlConfigBom:
    """Ultrathink-audit extension of wave-19 bug #104.

    The wave-19 fix made `_parse_dotenv` BOM-safe via `encoding="utf-8-sig"`.
    During ultrathink audit we discovered `_parse_toml_config` had the same
    class of bug: `tomllib.load` rejects a leading BOM with
    `TOMLDecodeError: Invalid statement (at line 1, column 1)` because the
    TOML spec disallows it. A Notepad-created `~/.aipea/config.toml` would
    silently fail to load, with all config values defaulting. Fix: strip
    a leading BOM before handing bytes to `tomllib.loads`."""

    def test_bom_prefixed_toml_parses_cleanly(self, tmp_path: Path) -> None:
        """A TOML config with a leading UTF-8 BOM must parse."""
        cfg = tmp_path / "config.toml"
        cfg.write_bytes(b'\xef\xbb\xbf[aipea]\nexa_api_key = "bom-key"\n')
        result = _parse_toml_config(cfg)
        assert result == {"exa_api_key": "bom-key"}

    def test_non_bom_toml_still_parses(self, tmp_path: Path) -> None:
        """Regular UTF-8 TOML (no BOM) must continue to parse."""
        cfg = tmp_path / "config.toml"
        cfg.write_text('[aipea]\nexa_api_key = "no-bom-key"\n', encoding="utf-8")
        result = _parse_toml_config(cfg)
        assert result == {"exa_api_key": "no-bom-key"}

    def test_corrupt_toml_returns_empty(self, tmp_path: Path) -> None:
        """Garbage non-UTF-8 bytes must not crash the parser."""
        cfg = tmp_path / "config.toml"
        cfg.write_bytes(b"\xff\xfe\x00\x01 not a valid toml document")
        # Should return {} via the except clause, not raise.
        result = _parse_toml_config(cfg)
        assert result == {}
