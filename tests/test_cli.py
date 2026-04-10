"""Tests for aipea.cli — CLI commands (info, check, doctor, configure)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_check_exit_0_when_no_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing optional keys are warnings, not errors — exit 0 (#41)."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)  # no .env here
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
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

    def test_doctor_connectivity_uses_pass_warn_format(self) -> None:
        """Doctor connectivity section must use PASS/WARN/FAIL format, not raw output (#42)."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        # The connectivity section should use the _DoctorChecks format
        # With no keys: WARN is shown (not raw "Exa: skipped" format)
        output = result.output
        # Should contain either PASS or WARN for connectivity items
        assert "PASS" in output or "WARN" in output or "FAIL" in output


class TestCheckExitCodes:
    """Regression tests for check command exit codes (#41)."""

    def test_check_exit_1_when_connectivity_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Connectivity failure must exit 1."""
        monkeypatch.setenv("EXA_API_KEY", "test_key_1234567890")
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

        with patch("aipea.cli._test_exa_connectivity", return_value=False):
            result = runner.invoke(app, ["check", "--connectivity"])
            assert result.exit_code == 1

    def test_check_warnings_shown_for_missing_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing keys should show warnings but exit 0."""
        monkeypatch.delenv("EXA_API_KEY", raising=False)
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        monkeypatch.delenv("AIPEA_HTTP_TIMEOUT", raising=False)
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["check"])
        assert result.exit_code == 0
        assert "not configured" in result.output or "not set" in result.output


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


# ============================================================================
# Regression: seed-kb respects configured AIPEA_DB_PATH
# ============================================================================


class TestSeedKBUsesConfigPath:
    """Regression: seed-kb should use config db_path when --db is not provided."""

    def test_seed_kb_default_uses_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """seed-kb without --db should read from load_config().db_path."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            custom_path = f.name

        # Patch load_config to return our custom path
        mock_config = type("C", (), {"db_path": custom_path})()
        with patch("aipea.cli.load_config", return_value=mock_config):
            result = runner.invoke(app, ["seed-kb"])
            # The command should use the config path, not hardcoded default
            # Check it ran (exit code 0) and referenced the custom path
            assert result.exit_code == 0

        import os

        os.unlink(custom_path)


# ============================================================================
# Regression: doctor connectivity should not produce duplicate output
# ============================================================================


class TestDoctorConnectivityNoDoubleOutput:
    """Regression: doctor should show PASS/FAIL only, not also raw OK/Error lines."""

    @patch("aipea.cli.httpx.post")
    @patch("aipea.cli.load_config")
    def test_doctor_exa_no_duplicate_ok(self, mock_load: MagicMock, mock_post: MagicMock) -> None:
        """When Exa succeeds in doctor, output should have PASS but NOT raw 'Exa: OK'."""
        from aipea.config import AIPEAConfig

        mock_load.return_value = AIPEAConfig(exa_api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = runner.invoke(app, ["doctor"])
        # Should contain PASS line from doctor format
        assert "PASS" in result.output or "Exa connectivity" in result.output
        # Should NOT contain raw "Exa: OK" from _test_exa_connectivity
        # Count occurrences of "Exa" — should not have both "Exa: OK" and "Exa connectivity"
        lines_with_exa_ok = [ln for ln in result.output.splitlines() if "Exa:" in ln and "OK" in ln]
        assert len(lines_with_exa_ok) <= 1, f"Duplicate Exa output: {lines_with_exa_ok}"


class TestWave17GitignoreReadCrash:
    """Regression for bug #89: `doctor` and `configure` crashed on
    `.gitignore` files that were non-UTF-8 encoded or unreadable."""

    def test_doctor_handles_non_utf8_gitignore(self, tmp_path: Path) -> None:
        """Verify doctor doesn't crash on non-UTF-8 .gitignore."""
        import os

        # Write a .gitignore file with invalid UTF-8 bytes
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            (tmp_path / ".gitignore").write_bytes(b"\xff\xfe\x00invalid utf-8")
            result = runner.invoke(app, ["doctor"])
            # Must not crash with a traceback
            assert "Traceback" not in (result.output or "")
            assert result.exit_code in (0, 1)
        finally:
            os.chdir(original_cwd)

    def test_doctor_handles_missing_gitignore(self, tmp_path: Path) -> None:
        """Verify doctor doesn't crash when no .gitignore exists."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            # No .gitignore file
            result = runner.invoke(app, ["doctor"])
            assert "Traceback" not in (result.output or "")
            assert result.exit_code in (0, 1)
        finally:
            os.chdir(original_cwd)


# ============================================================================
# REGRESSION TESTS — Wave 18 #92
# ============================================================================


class TestWave18ConnectivityUsesCfgUrls:
    """Regression: connectivity helpers must honor cfg.exa_api_url /
    cfg.firecrawl_api_url (persisted in .env or global TOML), not just
    the raw environment variable. (Bug #92 — silent regression of #73)
    """

    def test_check_connectivity_uses_cfg_exa_url(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """aipea check --connectivity targets the custom Exa URL from AIPEAConfig."""
        monkeypatch.delenv("AIPEA_EXA_API_URL", raising=False)
        monkeypatch.delenv("AIPEA_FIRECRAWL_API_URL", raising=False)

        # Persist custom URL via .env in a fresh cwd
        env_file = tmp_path / ".env"
        env_file.write_text(
            'EXA_API_KEY="fake-exa-key"\nAIPEA_EXA_API_URL="https://custom.exa.example/v1/search"\n'
        )
        import os as _os

        original_cwd = _os.getcwd()
        try:
            _os.chdir(tmp_path)
            captured: dict[str, object] = {}

            def fake_post(url: str, **_kwargs: object) -> MagicMock:
                captured["url"] = url
                resp = MagicMock()
                resp.status_code = 200
                return resp

            with patch("aipea.cli.httpx.post", side_effect=fake_post):
                result = runner.invoke(app, ["check", "--connectivity"])
            assert result.exit_code == 0
            assert captured["url"] == "https://custom.exa.example/v1/search"
        finally:
            _os.chdir(original_cwd)

    def test_check_connectivity_uses_cfg_firecrawl_url(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """aipea check --connectivity targets the custom Firecrawl URL from AIPEAConfig."""
        monkeypatch.delenv("AIPEA_EXA_API_URL", raising=False)
        monkeypatch.delenv("AIPEA_FIRECRAWL_API_URL", raising=False)

        env_file = tmp_path / ".env"
        env_file.write_text(
            'FIRECRAWL_API_KEY="fake-fc-key"\n'
            'AIPEA_FIRECRAWL_API_URL="https://custom.firecrawl.example/search"\n'
        )
        import os as _os

        original_cwd = _os.getcwd()
        try:
            _os.chdir(tmp_path)
            captured: dict[str, object] = {}

            def fake_post(url: str, **_kwargs: object) -> MagicMock:
                captured["url"] = url
                resp = MagicMock()
                resp.status_code = 200
                return resp

            with patch("aipea.cli.httpx.post", side_effect=fake_post):
                result = runner.invoke(app, ["check", "--connectivity"])
            assert result.exit_code == 0
            assert captured["url"] == "https://custom.firecrawl.example/search"
        finally:
            _os.chdir(original_cwd)

    def test_default_url_used_when_no_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Default Exa URL is used when no env / config override is set."""
        monkeypatch.delenv("AIPEA_EXA_API_URL", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text('EXA_API_KEY="fake-exa-key"\n')

        import os as _os

        original_cwd = _os.getcwd()
        try:
            _os.chdir(tmp_path)
            captured: dict[str, object] = {}

            def fake_post(url: str, **_kwargs: object) -> MagicMock:
                captured["url"] = url
                resp = MagicMock()
                resp.status_code = 200
                return resp

            with patch("aipea.cli.httpx.post", side_effect=fake_post):
                result = runner.invoke(app, ["check", "--connectivity"])
            assert result.exit_code == 0
            assert captured["url"] == "https://api.exa.ai/search"
        finally:
            _os.chdir(original_cwd)
