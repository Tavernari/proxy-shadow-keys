import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from proxy_shadow_keys import cli
from unittest.mock import patch, MagicMock, mock_open
import os
import signal
import time

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
def mock_pid_file(tmp_path):
    pid_file = str(tmp_path / "proxy_shadow_keys.pid")
    with patch("os.path.expanduser", return_value=pid_file) as mock_expanduser:
        yield pid_file

@pytest.fixture
def mock_os_kill():
    with patch("os.kill") as mock_kill:
        yield mock_kill

@pytest.fixture
def mock_time_sleep():
    with patch("time.sleep") as mock_sleep:
        yield mock_sleep

@pytest.fixture
def run_cli(capsys, mock_subprocess, mock_subprocess_popen, mock_networksetup, mock_os_kill, mock_pid_file, mock_time_sleep):
    from click.testing import CliRunner
    runner = CliRunner()
    def _run(args):
        # Using CliRunner for consistent click testing
        with patch("sys.platform", "darwin"):
            try:
                # We need to ensure the parent directory of the pid file exists in the mock
                pid_dir = os.path.dirname(mock_pid_file)
                if not os.path.exists(pid_dir):
                    os.makedirs(pid_dir, exist_ok=True)
                
                # Mock certificate existence
                cert_path = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.pem")
                
                original_exists = os.path.exists
                def side_effect_exists(path):
                    if path == cert_path:
                        return True
                    return original_exists(path)
                
                with patch("os.path.exists", side_effect=side_effect_exists):
                    result = runner.invoke(cli.main, args, catch_exceptions=False)
                    return result.exit_code, result.output, ""
            except SystemExit as e:
                return e.code, "", ""
    return _run

@given('the proxy service is not running')
def proxy_not_running():
    pass

@given('the proxy service is running')
def proxy_running(mock_pid_file, mock_os_kill):
    with open(mock_pid_file, "w") as f:
        f.write("1234")
    # First call is signal.SIGTERM, second is poll (0)
    mock_os_kill.side_effect = [None, ProcessLookupError()]

@when(parsers.parse('I run the CLI with "{args_str}"'), target_fixture="cli_result")
def run_cli_with_args(run_cli, args_str):
    args = args_str.split(" ")
    return run_cli(args)

@then('the mitmproxy service should start in the background')
def verify_proxy_started(mock_subprocess_popen):
    assert mock_subprocess_popen.call_count == 2
    # First call is for mitmdump
    assert "mitmdump" in mock_subprocess_popen.call_args_list[0][0][0]
    # Second call is for watchdog
    assert "watchdog" in mock_subprocess_popen.call_args_list[1][0][0]

@then('the macOS system proxy should be configured to use the proxy service')
def verify_mac_proxy_configured(mock_networksetup):
    # Verify the proxy manager called networksetup to configure proxy
    assert mock_networksetup.call_count > 0

@then('the mitmproxy service should stop')
def verify_proxy_stopped(mock_subprocess, mock_os_kill):
    # Check if pkill was called OR os.kill was called
    pkill_called = any("pkill" in str(call_args) for call_args in mock_subprocess.call_args_list)
    os_kill_called = mock_os_kill.called
    assert pkill_called or os_kill_called

@then('the macOS system proxy should be removed')
def verify_mac_proxy_removed(mock_networksetup):
    assert mock_networksetup.call_count > 0

@then('the mitmproxy certificate should be installed and trusted in the macOS Keychain')
def verify_cert_installed(mock_subprocess):
    # Verify security command was called
    called = any("security" in call_args[0][0] for call_args in mock_subprocess.call_args_list)
    assert called

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

@then('it should save the proxy PID to a tracker file')
def verify_pid_saved(mock_pid_file, cli_result):
    import os
    exit_code, out, err = cli_result
    if exit_code != 0:
        print(f"CLI failed with exit code: {exit_code}\nOutput:\n{out}")
    assert os.path.exists(mock_pid_file)
    with open(mock_pid_file, "r") as f:
        pid = f.read().strip()
    assert pid == "1234" # the mock_subprocess_popen PID

@then('it should terminate the process using the tracked PID')
def verify_pid_terminated(mock_os_kill):
    # We verify that kill was called with SIGTERM
    import signal
    mock_os_kill.assert_any_call(1234, signal.SIGTERM)

@then('it should remove the PID tracker file')
def verify_pid_removed(mock_pid_file):
    import os
    assert not os.path.exists(mock_pid_file)

@given('the proxy service is running with a watchdog')
def proxy_running_with_watchdog():
    # This is a state tracker
    pass

@when('the mitmproxy process is forcefully killed')
def mitmproxy_watchdog_killed(mock_os_kill, mock_networksetup, mock_pid_file, run_cli):
    # Instead of running the daemon in background, we'll run the watchdog command synchronously
    # and mock os.kill to simulate process termination.
    
    # Configure mock_os_kill to throw ProcessLookupError immediately
    mock_os_kill.side_effect = ProcessLookupError()
    
    # Run the hidden watchdog command
    run_cli(["watchdog", "1234", "8080", "--manage-system-proxy"])

@then('the watchdog should automatically remove the system proxy')
def verify_watchdog_proxy_removed(mock_networksetup):
    # Verify the proxy manager called networksetup to disable proxy
    called_off = any("off" in str(call_args) for call_args in mock_networksetup.call_args_list)
    assert called_off

@then('the watchdog process should terminate')
def verify_watchdog_terminated():
    # Watchdog command should return (handled by run_cli above)
    pass
