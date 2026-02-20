Feature: Proxy Interception and Key Replacement
  As a developer
  I want the proxy to automatically replace shadow keys with real keys in outgoing requests
  So that my applications can use shadow keys securely

  Background:
    Given the mitmproxy service is running

  Scenario Outline: Replace a shadow key in request body and headers
    Given a shadow key "shadow_api_key_1" with value "sk_live_1234" is stored in the system keyring
    When an HTTP request is intercepted with <location> containing "shadow_api_key_1"
    Then the request <location> should be modified to contain "sk_live_1234"
    And the request should be forwarded to the destination

    Examples:
      | location              |
      | header Authorization  |
      | JSON body payload     |
      | URL query parameters  |

  Scenario: Shadow key not found in keyring
    Given a shadow key "shadow_missing_key" is not stored in the system keyring
    When an HTTP request is intercepted with a header containing "shadow_missing_key"
    Then the request should remain unchanged
    And the request should be forwarded to the destination without errors
