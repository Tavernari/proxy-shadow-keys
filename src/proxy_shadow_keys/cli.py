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
@click.option('--allow-host', multiple=True, help='Limit this key to specific hosts (e.g. *.openai.com).')
def set(key, value, allow_host):
    """Set a shadow key mapping in the secure vault."""
    import json
    try:
        data = {"value": value, "allowed_hosts": list(allow_host)}
        keyring.set_password(APP_NAME, key, json.dumps(data))
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
@click.option('--no-system-proxy', is_flag=True, help='Skip configuring the OS system proxy.')
def start(port, no_system_proxy):
    """Start the proxy service and configure system proxy."""
    import subprocess
    import time
    from proxy_shadow_keys.system_proxy import get_system_proxy_manager

    try:
        import os
        import proxy_shadow_keys
        interceptor_path = os.path.join(os.path.dirname(proxy_shadow_keys.__file__), "interceptor.py")
        
        # 1. Start Mitmproxy in the background (mitmdump for non-interactive)
        cmd = ["mitmdump", "-s", interceptor_path, "-p", str(port)]
        if not no_system_proxy:
            cmd.extend(["--set", "manage_system_proxy=true"])
            
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Give it a second to start
        time.sleep(1)

        if proc.poll() is not None:
             click.echo("Error: mitmproxy failed to start.", err=True)
             sys.exit(1)

        # 2. Configure System Proxy (unless skipped)
        if not no_system_proxy:
            manager = get_system_proxy_manager(port=port)
            manager.enable_proxy()
            click.echo(f"Success: Proxy service started in the background out port {port} and system proxy configured.")
        else:
            click.echo(f"Success: Proxy service started on port {port} (System proxy NOT configured).")
            
        click.echo(f"PID: {proc.pid}. Use 'shadow-keys stop' to disable.")
    except Exception as e:
        click.echo(f"Error starting proxy: {e}", err=True)
        sys.exit(1)

@main.command()
@click.option('--no-system-proxy', is_flag=True, help='Skip modifying the OS system proxy.')
def stop(no_system_proxy):
    """Stop the proxy service and restore system proxy."""
    import subprocess
    from proxy_shadow_keys.system_proxy import get_system_proxy_manager

    try:
        # 1. Disable System Proxy (unless skipped)
        if not no_system_proxy:
            manager = get_system_proxy_manager()
            manager.disable_proxy()

        # 2. Stop Mitmproxy (naively kill mitmdump processes)
        import os
        import proxy_shadow_keys
        interceptor_path = os.path.join(os.path.dirname(proxy_shadow_keys.__file__), "interceptor.py")
        subprocess.run(["pkill", "-f", f"mitmdump -s {interceptor_path}"], check=False)
        
        if not no_system_proxy:
            click.echo("Success: Proxy service stopped and system proxy disabled.")
        else:
            click.echo("Success: Proxy service stopped.")
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
