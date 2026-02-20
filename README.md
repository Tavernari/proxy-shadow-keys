# Proxy Shadow Keys

A CLI tool and local proxy service designed to intercept network requests and transparently replace "shadow keys" (e.g., `shadow_my_api_key`) with your real, secret keys stored securely in the macOS Keychain.

This tool allows developers to use placeholder keys in their application code or environment files, preventing accidental exposure or commits of sensitive API keys to version control.

## Intentions

- **Security Details**: Never hardcode real API keys in your `.env` files, scripts, or repositories.
- **Convenience**: Use consistent placeholder keys (like `shadow_stripe_secret`) across your projects and let the proxy handle inserting the real sensitive values behind the scenes.
- **Fallbacks**: If a shadow key isn't found in your secure vault, the proxy sends the original placeholder unchanged, preventing unexpected crashes and making debugging easy.

## Project Structure

```text
proxy-shadow-keys/
├── src/
│   └── proxy_shadow_keys/
│       ├── cli.py            # Click-based CLI commands (set, rm, start, stop, install-cert)
│       ├── interceptor.py    # mitmproxy addon that intercepts and replaces shadow keys
│       └── system_proxy.py   # Cross-platform utility to toggle system proxy settings (Windows, macOS, Linux)
├── tests/
│   ├── features/             # Behavior-Driven Development (BDD) feature specifications
│   └── step_defs/            # pytest-bdd step definitions
└── pyproject.toml            # Project configuration and dependencies
```

## How It Works

1. **Store Keys**: Use the CLI to store a real key mapping in your system's keyring (macOS Keychain, Windows Credential Locker, or Linux Secret Service).
2. **Start Proxy**: The CLI starts a local `mitmproxy` instance in the background and configures your OS system proxy (macOS `networksetup`, Windows Registry, or Linux `gsettings`) to route traffic through it.
3. **Intercept & Replace**: As your system makes HTTP/HTTPS requests, the mitmproxy addon parses request headers, JSON bodies, and URL query parameters. When it detects a string starting with `shadow_`, it queries the local keyring to swap the placeholder with the real API key before forwarding the request to its destination.

## Requirements

- macOS, Windows, or Linux (GNOME)
- Python 3.9+
- `mitmproxy` installed and available

## Installation

The recommended way to install and run the CLI globally in an isolated environment is using `pipx` or `uv`:

```bash
# Using uv (fastest)
uv tool install proxy-shadow-keys

# Or using pipx
pipx install proxy-shadow-keys
```

### Standard Installation

You can install `proxy-shadow-keys` via `pip`:

```bash
pip install proxy-shadow-keys
```

### Recommended: Using pipx

For CLI tools, it's recommended to use [pipx](https://github.com/pypa/pipx) to keep dependencies isolated:

```bash
pipx install proxy-shadow-keys
```

### One-liner (curl)

If you have `pip` installed, you can use this one-liner to download and install the latest version directly:

```bash
curl -sSL https://raw.githubusercontent.com/Tavernari/proxy-shadow-keys/main/scripts/install.sh | bash
```

### Development or Source Installation

If you want to contribute or use the latest unreleased changes:

```bash
# Clone the repository
git clone git@github.com:Tavernari/proxy-shadow-keys.git
cd proxy-shadow-keys

# Install in editable mode
pip install -e .
```


## Usage

### 1. Certificate Installation

For the proxy to inspect encrypted HTTPS traffic, you must first install and trust the mitmproxy CA certificate. Run this command once (requires sudo privileges):

```bash
proxy-shadow-keys install-cert
```

### 2. Managing Shadow Keys

Map a placeholder `shadow_` key to your real API key (stored securely via `keyring`):

```bash
proxy-shadow-keys set shadow_openai_key sk-proj-123456789...
```

To remove a mapped key:

```bash
proxy-shadow-keys rm shadow_openai_key
```

### 3. Proxy Lifecycle

Start the proxy. This will launch `mitmproxy` in the background and configure your local network settings to use the local proxy:

```bash
proxy-shadow-keys start
```
*(Default port is 8080. You can optionally pass `--port 8081`)*

When you're done, stop the proxy to restore your standard network settings:

```bash
proxy-shadow-keys stop
```

## Testing

The project uses a BDD approach with `pytest` and `pytest-bdd`. All functionality is strictly defined in feature files before implementation.

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest
```
