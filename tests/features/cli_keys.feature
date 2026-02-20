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
