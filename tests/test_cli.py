"""Tests for the CLI module."""

from click.testing import CliRunner

from gmail_spam_cleaner.cli import cli


def test_cli_help():
    """CLI --help should work and show commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
    assert "clean" in result.output
    assert "export" in result.output
    assert "auth" in result.output
    assert "cache" in result.output


def test_cli_version():
    """CLI --version should show version."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_scan_no_credentials(tmp_path, monkeypatch):
    """Scan without credentials should show clear error."""
    import gmail_spam_cleaner.auth as auth_module

    monkeypatch.setattr(auth_module, "CREDENTIALS_PATH", tmp_path / "nonexistent.json")
    monkeypatch.setattr(auth_module, "TOKEN_PATH", tmp_path / "token.json")
    monkeypatch.setattr(auth_module, "CONFIG_DIR", tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["scan"])
    assert result.exit_code != 0
    assert "Credentials file not found" in result.output or "Error" in result.output


def test_cache_info_empty(tmp_path, monkeypatch):
    """Cache info on empty cache should not crash."""
    import gmail_spam_cleaner.constants as constants

    monkeypatch.setattr(constants, "CACHE_DB_PATH", tmp_path / "cache.db")

    runner = CliRunner()
    result = runner.invoke(cli, ["cache", "info"])
    assert result.exit_code == 0


def test_cache_clear(tmp_path, monkeypatch):
    """Cache clear should work."""
    import gmail_spam_cleaner.constants as constants

    monkeypatch.setattr(constants, "CACHE_DB_PATH", tmp_path / "cache.db")

    runner = CliRunner()
    result = runner.invoke(cli, ["cache", "clear"])
    assert result.exit_code == 0
    assert "cleared" in result.output.lower()


def test_export_no_cache(tmp_path, monkeypatch):
    """Export without cache should show error."""
    import gmail_spam_cleaner.constants as constants

    monkeypatch.setattr(constants, "CACHE_DB_PATH", tmp_path / "cache.db")

    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--format", "csv", "-o", str(tmp_path / "out.csv")])
    assert result.exit_code != 0
    assert "No cached scan found" in result.output
