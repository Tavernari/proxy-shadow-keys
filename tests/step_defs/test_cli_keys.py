import pytest
from pytest_bdd import scenarios, given, when, then, parsers
from proxy_shadow_keys import cli
import keyring

# Load scenarios
scenarios("../features/cli_keys.feature")

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

@given('the CLI is available')
def cli_available():
    pass

@given(parsers.parse('a shadow key "{key}" with value "{value}" is stored in the system keyring'))
def store_shadow_key_in_keyring(key, value):
    # Backward compatible store without allowed hosts
    keyring.set_password("proxy-shadow-keys", key, value)
    yield
    # Cleanup after test if needed
    try:
        keyring.delete_password("proxy-shadow-keys", key)
    except keyring.errors.PasswordDeleteError:
        pass

@when(parsers.parse('I run the CLI with "{args_str}"'), target_fixture="cli_result")
def run_cli_with_args(run_cli, args_str):
    args = args_str.split(" ")
    return run_cli(args)

@then(parsers.parse('the key "{key}" with value "{value}" should be stored in the system keyring'))
def verify_key_in_keyring(key, value):
    stored_value = keyring.get_password("proxy-shadow-keys", key)
    # The value might be a json string now if there are allowed hosts
    if stored_value and stored_value.startswith('{'):
        import json
        data = json.loads(stored_value)
        assert data.get("value") == value
    else:
        assert stored_value == value

@then(parsers.parse('the key "{key}" should be stored with value "{value}" and allowed hosts "{hosts}"'))
def verify_key_with_hosts_in_keyring(key, value, hosts):
    stored_value = keyring.get_password("proxy-shadow-keys", key)
    import json
    data = json.loads(stored_value)
    assert data.get("value") == value
    assert data.get("allowed_hosts") == hosts.split(",")

@then(parsers.parse('the key "{key}" should be removed from the system keyring'))
def verify_key_removed_from_keyring(key):
    stored_value = keyring.get_password("proxy-shadow-keys", key)
    assert stored_value is None

@then('it should print a success message')
def verify_success_msg(cli_result):
    exit_code, out, err = cli_result
    assert exit_code == 0
    assert "success" in out.lower() or "done" in out.lower()
