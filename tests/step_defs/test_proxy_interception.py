import pytest
from pytest_bdd import scenarios, given, when, then, parsers
import keyring
from proxy_shadow_keys.interceptor import ShadowKeyInterceptor
from mitmproxy import http
from mitmproxy.test.tflow import tflow

scenarios("../features/proxy_interception.feature")

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

@when(parsers.parse('an HTTP request is intercepted with header Authorization containing "{key}"'), target_fixture="intercepted_flow")
def intercept_request_header_key(key):
    flow = tflow()
    flow.request.headers["Authorization"] = f"Bearer {key}"
    interceptor = ShadowKeyInterceptor()
    interceptor.request(flow)
    return flow

@when(parsers.parse('an HTTP request is intercepted with JSON body payload containing "{key}"'), target_fixture="intercepted_flow")
def intercept_request_body_key(key):
    flow = tflow()
    flow.request.content = f'{{"api_key": "{key}"}}'.encode('utf-8')
    interceptor = ShadowKeyInterceptor()
    interceptor.request(flow)
    return flow

@when(parsers.parse('an HTTP request is intercepted with URL query parameters containing "{key}"'), target_fixture="intercepted_flow")
def intercept_request_query_key(key):
    flow = tflow()
    flow.request.query["token"] = key
    interceptor = ShadowKeyInterceptor()
    interceptor.request(flow)
    return flow

@when(parsers.parse('an HTTP request is intercepted with a header containing "{key}"'), target_fixture="intercepted_flow")
def intercept_request_missing_key(key):
    flow = tflow()
    flow.request.headers["Authorization"] = f"Bearer {key}"
    interceptor = ShadowKeyInterceptor()
    interceptor.request(flow)
    return flow

@then(parsers.parse('the request header Authorization should be modified to contain "{expected_value}"'))
def verify_request_header_modified(expected_value, intercepted_flow):
    assert expected_value in intercepted_flow.request.headers["Authorization"]

@then(parsers.parse('the request JSON body payload should be modified to contain "{expected_value}"'))
def verify_request_body_modified(expected_value, intercepted_flow):
    assert expected_value in intercepted_flow.request.content.decode('utf-8')

@then(parsers.parse('the request URL query parameters should be modified to contain "{expected_value}"'))
def verify_request_query_modified(expected_value, intercepted_flow):
    assert expected_value in intercepted_flow.request.query["token"]

@then('the request should remain unchanged')
def verify_request_unchanged(intercepted_flow):
    assert "shadow_missing_key" in intercepted_flow.request.headers["Authorization"]

@given(parsers.parse('a shadow key "{key}" with value "{value}" and allowed hosts "{hosts}" is stored in the system keyring'))
def store_shadow_key_with_hosts(key, value, hosts):
    import json
    data = {"value": value, "allowed_hosts": hosts.split(",")}
    keyring.set_password("proxy-shadow-keys", key, json.dumps(data))
    yield
    try:
        keyring.delete_password("proxy-shadow-keys", key)
    except:
        pass

@when(parsers.parse('an HTTP request is intercepted with a header containing "{key}" to host "{host}"'), target_fixture="intercepted_flow")
def intercept_request_missing_key_to_host(key, host):
    flow = tflow()
    flow.request.host = host
    flow.request.headers["Authorization"] = f"Bearer {key}"
    interceptor = ShadowKeyInterceptor()
    interceptor.request(flow)
    return flow

@then(parsers.parse('the request header should be modified to contain "{expected_value}"'))
def verify_request_header_modified_gen(expected_value, intercepted_flow):
    assert expected_value in intercepted_flow.request.headers["Authorization"]

@then('the request header should remain unchanged')
def verify_request_header_unchanged_gen(intercepted_flow):
    assert "shadow_" in intercepted_flow.request.headers["Authorization"]

@then('the request should be forwarded to the destination')
@then('the request should be forwarded to the destination without errors')
def verify_request_forwarded():
    pass
