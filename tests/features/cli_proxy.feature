Feature: CLI Proxy Service Management
  As a developer
  I want to easily start, stop, and configure the proxy service
  So that I can intercept requests using my shadow keys

  Scenario: Start the proxy service
    Given the proxy service is not running
    When I run the CLI with "start"
    Then the mitmproxy service should start in the background
    And the macOS system proxy should be configured to use the proxy service
    And it should print a success message

  Scenario: Stop the proxy service
    Given the proxy service is running
    When I run the CLI with "stop"
    Then the mitmproxy service should stop
    And the macOS system proxy should be removed
    And it should print a success message

  Scenario: Install the proxy certificate
    When I run the CLI with "install-cert"
    Then the mitmproxy certificate should be installed and trusted in the macOS Keychain
    And it should print a success message

  Scenario: Proxy service auto-disables system proxy on shutdown
    Given the proxy service is running with system proxy management enabled
    When the mitmproxy background process terminates unexpectedly
    Then the macOS system proxy should be removed automatically

  Scenario: Safe proxy termination using PID tracking
    Given the proxy service is not running
    When I run the CLI with "start"
    Then it should save the proxy PID to a tracker file
    When I run the CLI with "stop"
    Then it should terminate the process using the tracked PID
    And it should remove the PID tracker file

  Scenario: Watchdog auto-disables proxy on SIGKILL
    Given the proxy service is running with a watchdog
    When the mitmproxy process is forcefully killed
    Then the watchdog should automatically remove the system proxy
    And the watchdog process should terminate
