Feature: Proxy Shadow Keys CLI
  As a user
  I want to use the CLI tool
  So that I can manage my proxy shadow keys

  Scenario: Run CLI to check version
    When I run the CLI with "--version"
    Then it should print the current version
    And exit with code 0

  Scenario: Run CLI without arguments
    When I run the CLI without arguments
    Then it should print the welcome message
    And exit with code 0
