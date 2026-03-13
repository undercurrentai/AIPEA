"""Tests for aipea.config — configuration loading, parsing, and persistence."""

from __future__ import annotations

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
