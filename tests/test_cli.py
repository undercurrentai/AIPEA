"""Tests for aipea.cli — CLI commands (info, check, doctor, configure)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

import aipea
from aipea.cli import app

runner = CliRunner()


# ============================================================================
# aipea info
# ============================================================================


class TestInfoCommand:
    def test_shows_version(self) -> None:
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert aipea.__version__ in result.output

    def test_shows_python_version(self) -> None:
        result = runner.invoke(app, ["info"])
        assert "Python" in result.output or "3.1" in result.output

    def test_shows_exports(self) -> None:
        result = runner.invoke(app, ["info"])
        assert "Exports" in result.output


# ============================================================================
# aipea check
# ============================================================================


class TestCheckCommand:
    def test_check_runs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        result = runner.invoke(app, ["check"])
        assert "Configuration Check" in result.output

    def test_check_exit_1_when_no_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)  # no .env here
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 1
        assert "not set" in result.output

    def test_check_exit_0_when_keys_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EXA_API_KEY", "test_exa_key_123456")
        monkeypatch.setenv("FIRECRAWL_API_KEY", "test_fc_key_123456")
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0

    def test_check_connectivity_skipped_without_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["check", "--connectivity"])
        assert "skipped" in result.output

    def test_check_connectivity_with_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("EXA_API_KEY", "test_key_1234567890")
        monkeypatch.setenv("FIRECRAWL_API_KEY", "test_key_1234567890")

        with patch("aipea.cli.httpx.post") as mock_post:
            mock_post.return_value.status_code = 200
            result = runner.invoke(app, ["check", "--connectivity"])
            assert "OK" in result.output or result.exit_code == 0


# ============================================================================
# aipea doctor
# ============================================================================


class TestDoctorCommand:
    def test_doctor_runs(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "AIPEA Doctor" in result.output

    def test_doctor_shows_python_check(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Python" in result.output
        assert "PASS" in result.output

    def test_doctor_shows_package_version(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert aipea.__version__ in result.output

    def test_doctor_shows_dependencies(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "httpx" in result.output
        assert "typer" in result.output

    def test_doctor_shows_summary(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Summary" in result.output

    def test_doctor_shows_security(self) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Security" in result.output


# ============================================================================
# aipea configure
# ============================================================================


class TestConfigureCommand:
    def test_configure_saves_dotenv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)

        # Simulate user input: exa key, fc key, timeout (all Enter to skip)
        result = runner.invoke(
            app,
            ["configure", "--no-validate"],
            input="test_exa_key_123456\ntest_fc_key_123456\n\n",
        )
        assert result.exit_code == 0
        assert "Saved to" in result.output

        env_file = tmp_path / ".env"
        assert env_file.exists()
        content = env_file.read_text()
        assert "test_exa_key_123456" in content
        assert "test_fc_key_123456" in content

    def test_configure_global(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)

        toml_target = tmp_path / ".aipea" / "config.toml"

        with patch("aipea.cli._GLOBAL_CONFIG_FILE", toml_target):
            result = runner.invoke(
                app,
                ["configure", "--global", "--no-validate"],
                input="global_exa_1234567\n\n\n",
            )
            assert result.exit_code == 0
            assert toml_target.exists()
            content = toml_target.read_text()
            assert "global_exa_1234567" in content

    def test_configure_keeps_existing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pressing Enter for all prompts keeps existing values."""
        monkeypatch.setenv("EXA_API_KEY", "existing_key_123456")
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["configure", "--no-validate"],
            input="\n\n\n",  # Enter for all prompts
        )
        assert result.exit_code == 0
        # Summary should show the existing key (redacted)
        assert "exis...3456" in result.output

    def test_configure_invalid_timeout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["configure", "--no-validate"],
            input="\n\nnot_a_number\n",
        )
        assert result.exit_code == 0
        assert "Invalid timeout" in result.output

    def test_configure_warns_no_gitignore(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)
        # No .gitignore in tmp_path
        result = runner.invoke(
            app,
            ["configure", "--no-validate"],
            input="\n\n\n",
        )
        assert "gitignore" in result.output.lower() or "Warning" in result.output


# ============================================================================
# No-args shows help
# ============================================================================


class TestConfigureUX:
    """Tests for configure UX improvements (provider descriptions + next steps)."""

    def test_configure_shows_provider_descriptions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configure output contains provider descriptions with signup URLs."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["configure", "--no-validate"],
            input="\n\n\n",
        )
        assert "exa.ai" in result.output
        assert "firecrawl.dev" in result.output

    def test_configure_shows_next_steps(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configure output contains Next Steps panel."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(
            app,
            ["configure", "--no-validate"],
            input="\n\n\n",
        )
        assert "Next Steps" in result.output
        assert "aipea doctor" in result.output
        assert "aipea seed-kb" in result.output


# ============================================================================
# aipea doctor — Recommendations
# ============================================================================


class TestDoctorRecommendations:
    """Tests for doctor recommendations section."""

    def test_doctor_shows_recommendations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Doctor output contains Recommendations when items are missing."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["doctor"])
        assert "Recommendations" in result.output

    def test_doctor_ollama_install_hint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Doctor with no Ollama shows platform-specific install command."""
        with patch("shutil.which", return_value=None):
            result = runner.invoke(app, ["doctor"])
        # Should show an install hint (brew or curl or ollama.ai)
        assert "ollama" in result.output.lower()


# ============================================================================
# No-args shows help
# ============================================================================


class TestNoArgs:
    def test_no_args_shows_help(self) -> None:
        result = runner.invoke(app, [])
        # Typer's no_args_is_help returns 0 on some platforms, 2 on others
        assert result.exit_code in (0, 2)
        assert "AIPEA" in result.output or "Usage" in result.output
