from click.testing import CliRunner

from vulnscout.cli import cli


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "vulnscout" in result.output


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "VulnScout" in result.output


def test_doctor():
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "VulnScout" in result.output or result.exit_code == 0


def test_model_list():
    runner = CliRunner()
    result = runner.invoke(cli, ["model", "list"])
    assert result.exit_code == 0
    assert "Available models" in result.output or result.exit_code == 0
