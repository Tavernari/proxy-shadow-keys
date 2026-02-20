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
@click.option('--port', default=8080, help='Port to run the proxy on.')
def start(port):
    """Start the proxy service and configure system proxy."""
    import subprocess
    import time
    from proxy_shadow_keys.mac_proxy import MacOSProxyManager

    try:
        # 1. Start Mitmproxy in the background (mitmdump for non-interactive)
        cmd = ["mitmdump", "-s", "src/proxy_shadow_keys/interceptor.py", "-p", str(port)]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Give it a second to start
        time.sleep(1)

        if proc.poll() is not None:
             click.echo("Error: mitmproxy failed to start.", err=True)
             sys.exit(1)

        # 2. Configure System Proxy
        manager = MacOSProxyManager(port=port)
        manager.enable_proxy()
        
        click.echo(f"Success: Proxy service started in the background on port {port}.")
        click.echo(f"PID: {proc.pid}. Use 'shadow-keys stop' to disable.")
    except Exception as e:
        click.echo(f"Error starting proxy: {e}", err=True)
        sys.exit(1)

@main.command()
def stop():
    """Stop the proxy service and restore system proxy."""
    import subprocess
    from proxy_shadow_keys.mac_proxy import MacOSProxyManager

    try:
        # 1. Disable System Proxy
        manager = MacOSProxyManager()
        manager.disable_proxy()

        # 2. Stop Mitmproxy (naively kill mitmdump processes)
        subprocess.run(["pkill", "-f", "mitmdump -s src/proxy_shadow_keys/interceptor.py"], check=False)
        
        click.echo("Success: Proxy service stopped and system proxy disabled.")
    except Exception as e:
         click.echo(f"Error stopping proxy: {e}", err=True)
         sys.exit(1)

@main.command(name="install-cert")
def install_cert():
    """Install the mitmproxy certificate to the system Keychain."""
    import os
    import subprocess

    cert_path = os.path.expanduser("~/.mitmproxy/mitmproxy-ca-cert.pem")
    
    if not os.path.exists(cert_path):
        click.echo("Error: Certificate not found. Ensure mitmproxy has been started at least once.", err=True)
        sys.exit(1)

    try:
        # Command to add the certificate to the system keychain and trust it
        cmd = [
            "sudo", "security", "add-trusted-cert", "-d", "-r", "trustRoot",
            "-k", "/Library/Keychains/System.keychain", cert_path
        ]
        click.echo("Installing certificate... (This may require your password)")
        subprocess.run(cmd, check=True)
        click.echo("Success: Certificate installed and trusted.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error installing certificate: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
