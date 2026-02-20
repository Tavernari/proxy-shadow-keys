import pytest
from pytest_bdd import scenarios, when, then
from proxy_shadow_keys import cli, __version__

# Load all scenarios from the feature file
scenarios("../features/cli.feature")

@pytest.fixture
def run_cli(capsys):
    def _run(args):
        try:
            exit_code = cli.main(args)
        except SystemExit as e:
            exit_code = e.code
        
        captured = capsys.readouterr()
        return exit_code, captured.out, captured.err
    return _run

@when('I run the CLI with "--version"', target_fixture="cli_result")
def run_cli_version(run_cli):
    return run_cli(["--version"])

@when('I run the CLI without arguments', target_fixture="cli_result")
def run_cli_no_args(run_cli):
    return run_cli([])

@then('it should print the current version')
def verify_version_output(cli_result):
    _, out, _ = cli_result
    assert __version__ in out

@then('it should print the welcome message')
def verify_welcome_output(cli_result):
    _, out, _ = cli_result
    assert "Welcome to proxy-shadow-keys CLI!" in out

@then('exit with code 0')
def verify_exit_code(cli_result):
    exit_code, _, _ = cli_result
    assert exit_code == 0
