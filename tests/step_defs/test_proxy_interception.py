import pytest
from pytest_bdd import scenarios, given, when, then, parsers
import requests
import keyring

scenarios("../features/proxy_interception.feature")

# Note: In a real test environment, this would hit the actual proxy via mitmproxy dump or similar.
# For now, we stub the scenario structure.

@given('the mitmproxy service is running')
def mitmproxy_running():
    pass

@given(parsers.parse('a shadow key "{key}" with value "{value}" is stored in the system keyring'))
def store_shadow_key(key, value):
    keyring.set_password("proxy-shadow-keys", key, value)
    yield
    try:
        keyring.delete_password("proxy-shadow-keys", key)
    except:
        pass

@given(parsers.parse('a shadow key "{key}" is not stored in the system keyring'))
def ensure_shadow_key_missing(key):
    try:
        keyring.delete_password("proxy-shadow-keys", key)
    except:
        pass

@when(parsers.parse('an HTTP request is intercepted with {location} containing "{key}"'), target_fixture="intercepted_request")
def intercept_request_containing_key(location, key):
    # Mocking intercepted request state for test purposes
    return {
        "location": location,
        "original_value": key,
        "payload": f"some content {key} more content"
    }

@when(parsers.parse('an HTTP request is intercepted with a header containing "{key}"'), target_fixture="intercepted_request")
def intercept_request_header_key(key):
    return {
        "location": "header",
        "original_value": key,
        "payload": f"Authorization: Bearer {key}"
    }

@then(parsers.parse('the request {location} should be modified to contain "{expected_value}"'))
def verify_request_modified(location, expected_value, intercepted_request):
    # Here we should invoke the proxy interception logic manually or verify mitmproxy output
    pass

@then('the request should remain unchanged')
def verify_request_unchanged(intercepted_request):
    pass

@then('the request should be forwarded to the destination')
@then('the request should be forwarded to the destination without errors')
def verify_request_forwarded():
    pass
