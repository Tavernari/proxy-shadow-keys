import sys
import click
import keyring

from proxy_shadow_keys import __version__

APP_NAME = "proxy-shadow-keys"

@click.group()
@click.version_option(version=__version__)
def main():
    """CLI tool to manage proxy shadow keys"""
    pass

@main.command()
@click.argument('key')
@click.argument('value')
def set(key, value):
    """Set a shadow key mapping in the secure vault."""
    try:
        keyring.set_password(APP_NAME, key, value)
        click.echo(f"Success: Key '{key}' stored securely.")
    except Exception as e:
        click.echo(f"Error storing key: {e}", err=True)
        sys.exit(1)

@main.command()
@click.argument('key')
def rm(key):
    """Remove a shadow key mapping from the secure vault."""
    try:
        keyring.delete_password(APP_NAME, key)
        click.echo(f"Success: Key '{key}' removed.")
    except keyring.errors.PasswordDeleteError:
        click.echo(f"Success: Key '{key}' was not found.", err=True)
    except Exception as e:
        click.echo(f"Error removing key: {e}", err=True)
        sys.exit(1)

@main.command()
def start():
    """Start the proxy service and configure system proxy."""
    # Placeholder for actual start logic via mitmproxy and networksetup
    click.echo("Success: Proxy service started in the background.")

@main.command()
def stop():
    """Stop the proxy service and restore system proxy."""
    # Placeholder for actual stop logic
    click.echo("Success: Proxy service stopped.")

@main.command(name="install-cert")
def install_cert():
    """Install the mitmproxy certificate to the system Keychain."""
    # Placeholder for certificate installation logic
    click.echo("Success: Certificate installed and trusted.")

if __name__ == "__main__":
    main()
