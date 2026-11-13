from click.testing import CliRunner
from src.cli import cli


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "discover" in result.output
    assert "template" in result.output
    assert "fill" in result.output
    assert "retrieve" in result.output
