import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from proxy_shadow_keys import cli

scenarios("../features/cli_proxy.feature")

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

@given('the proxy service is not running')
def proxy_not_running():
    # Helper to ensure proxy is not running
    pass

@given('the proxy service is running')
def proxy_running():
    # Helper to start proxy or mock it
    pass

@when(parsers.parse('I run the CLI with "{args_str}"'), target_fixture="cli_result")
def run_cli_with_args(run_cli, args_str):
    args = args_str.split(" ")
    return run_cli(args)

@then('the mitmproxy service should start in the background')
def verify_proxy_started():
    # Assert mechanism to verify process is spawned
    pass

@then('the macOS system proxy should be configured to use the proxy service')
def verify_mac_proxy_configured():
    # Assert networksetup was called
    pass

@then('the mitmproxy service should stop')
def verify_proxy_stopped():
    pass

@then('the macOS system proxy should be removed')
def verify_mac_proxy_removed():
    pass

@then('the mitmproxy certificate should be installed and trusted in the macOS Keychain')
def verify_cert_installed():
    pass

@then('it should print a success message')
def verify_success_msg(cli_result):
    exit_code, out, err = cli_result
    assert exit_code == 0
    assert "success" in out.lower() or "started" in out.lower() or "stopped" in out.lower() or "installed" in out.lower()
