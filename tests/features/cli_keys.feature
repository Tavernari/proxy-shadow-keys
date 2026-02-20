Feature: CLI Key Management
  As a developer
  I want to securely store and remove shadow keys mapped to real keys
  So that the proxy can use them during interception without exposing real keys in code

  Scenario: Set a new shadow key
    Given the CLI is available
    When I run the CLI with "set shadow_my_api sk_prod_12345"
    Then the key "shadow_my_api" with value "sk_prod_12345" should be stored in the system keyring
    And it should print a success message

  Scenario: Remove an existing shadow key
    Given a shadow key "shadow_my_api" with value "sk_prod_12345" is stored in the system keyring
    When I run the CLI with "rm shadow_my_api"
    Then the key "shadow_my_api" should be removed from the system keyring
    And it should print a success message

  Scenario: Set a new shadow key with an allowed host
    Given the CLI is available
    When I run the CLI with "set shadow_openai_key sk_live_12345 --allow-host *.openai.com"
    Then the key "shadow_openai_key" should be stored with value "sk_live_12345" and allowed hosts "*.openai.com"
    And it should print a success message
