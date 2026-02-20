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

        # 1b. Write PID to a tracking file
        pid_file = os.path.expanduser("~/.mitmproxy/proxy_shadow_keys.pid")
        os.makedirs(os.path.dirname(pid_file), exist_ok=True)
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
            
        # 1c. Spawn watchdog daemon
        cmd_watchdog = [sys.executable, "-m", "proxy_shadow_keys.cli", "watchdog", str(proc.pid), str(port)]
        if not no_system_proxy:
            cmd_watchdog.append("--manage-system-proxy")
            
        subprocess.Popen(
            cmd_watchdog,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True # Detach from terminal
        )

        # 2. Configure System Proxy (unless skipped)
        if not no_system_proxy:
            manager = get_system_proxy_manager(port=port)
            manager.enable_proxy()
            click.echo(f"Success: Proxy service started in the background out port {port} and system proxy configured.")
        else:
            click.echo(f"Success: Proxy service started on port {port} (System proxy NOT configured).")
            
        click.echo(f"PID: {proc.pid}. Use 'proxy-shadow-keys stop' to disable.")
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

        # 2. Stop Mitmproxy (prefer PID file tracking for safety)
        import os
        import signal
        import time
        import proxy_shadow_keys
        
        pid_file = os.path.expanduser("~/.mitmproxy/proxy_shadow_keys.pid")
        stopped = False
        
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    pid = int(f.read().strip())
                
                os.kill(pid, signal.SIGTERM)
                
                # Wait for process to fully release the port
                for _ in range(25): # 5 seconds max
                    time.sleep(0.2)
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        stopped = True
                        break
                        
                os.remove(pid_file)
            except Exception as e:
                click.echo(f"Warning: Failed to stop proxy cleanly via PID: {e}")
                
        # Fallback to pkill if PID file method failed or file was missing
        if not stopped:
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

@main.command(hidden=True)
@click.argument('pid', type=int)
@click.argument('port', type=int)
@click.option('--manage-system-proxy', is_flag=True)
def watchdog(pid, port, manage_system_proxy):
    """Hidden background daemon: disables system proxy if mitmdump dies unexpectedly."""
    import os
    import time
    from proxy_shadow_keys.system_proxy import get_system_proxy_manager
    
    # Wait for the parent to finish bootstrapping proxy if needed
    time.sleep(2)
    
    while True:
        try:
            # Poll process existence
            os.kill(pid, 0)
            time.sleep(2)
        except ProcessLookupError:
            # The proxy process died! (e.g. killed via task manager, OOM, kill -9)
            if manage_system_proxy:
                try:
                    manager = get_system_proxy_manager(port=port)
                    manager.disable_proxy()
                except Exception:
                    pass
            break

if __name__ == "__main__":
    main()
