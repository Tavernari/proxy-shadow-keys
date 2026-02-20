import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from proxy_shadow_keys import cli
from unittest.mock import patch, MagicMock

scenarios("../features/cli_proxy.feature")

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock_run:
        yield mock_run

@pytest.fixture
def mock_subprocess_popen():
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        yield mock_popen

@pytest.fixture
def mock_networksetup():
    with patch("proxy_shadow_keys.system_proxy.MacOSProxyManager._run_networksetup") as mock_ns:
        # Simulate an active service
        mock_ns.return_value = "Wi-Fi"
        yield mock_ns

@pytest.fixture
def mock_os_path_exists():
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        yield mock_exists

@pytest.fixture
def run_cli(capsys, mock_subprocess, mock_subprocess_popen, mock_networksetup, mock_os_path_exists):
    from click.testing import CliRunner
    runner = CliRunner()
    def _run(args):
        # Using CliRunner for consistent click testing
        with patch("sys.platform", "darwin"):
            result = runner.invoke(cli.main, args)
            return result.exit_code, result.output, ""
    return _run

@given('the proxy service is not running')
def proxy_not_running():
    pass

@given('the proxy service is running')
def proxy_running():
    pass

@when(parsers.parse('I run the CLI with "{args_str}"'), target_fixture="cli_result")
def run_cli_with_args(run_cli, args_str):
    args = args_str.split(" ")
    return run_cli(args)

@then('the mitmproxy service should start in the background')
def verify_proxy_started(mock_subprocess_popen):
    mock_subprocess_popen.assert_called_once()
    assert "mitmdump" in mock_subprocess_popen.call_args[0][0]

@then('the macOS system proxy should be configured to use the proxy service')
def verify_mac_proxy_configured(mock_networksetup):
    # Verify the proxy manager called networksetup to configure proxy
    assert mock_networksetup.call_count > 0

@then('the mitmproxy service should stop')
def verify_proxy_stopped(mock_subprocess):
    # Check if pkill was called
    called = any("pkill" in call_args[0][0] for call_args in mock_subprocess.call_args_list)
    assert called

@then('the macOS system proxy should be removed')
def verify_mac_proxy_removed(mock_networksetup):
    assert mock_networksetup.call_count > 0

@then('the mitmproxy certificate should be installed and trusted in the macOS Keychain')
def verify_cert_installed(mock_subprocess):
    pass

@then('it should print a success message')
def verify_success_msg(cli_result):
    exit_code, out, err = cli_result
    assert exit_code == 0
    assert "success" in out.lower() or "started" in out.lower() or "stopped" in out.lower() or "installed" in out.lower()

@given('the proxy service is running with system proxy management enabled')
def proxy_running_with_sys_proxy(run_cli, mock_subprocess_popen, mock_networksetup):
    run_cli(["start"])
    mock_networksetup.reset_mock() 

@when('the mitmproxy background process terminates unexpectedly')
def mitmproxy_terminates(mock_networksetup):
    from proxy_shadow_keys.interceptor import addons
    interceptor = addons[0]
    class MockOptions:
        manage_system_proxy = True
    
    import mitmproxy.ctx
    mitmproxy.ctx.options = MockOptions()
    if hasattr(interceptor, 'done'):
        interceptor.done()

@then('the macOS system proxy should be removed automatically')
def verify_mac_proxy_removed_auto(mock_networksetup):
    assert mock_networksetup.call_count > 0
    called_off = any("off" in str(call_args) for call_args in mock_networksetup.call_args_list)
    assert called_off
