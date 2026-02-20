import subprocess
import logging
import sys

logger = logging.getLogger(__name__)

class SystemProxyManager:
    """Base class for managing the OS system proxy settings."""
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port

    def enable_proxy(self):
        raise NotImplementedError

    def disable_proxy(self):
        raise NotImplementedError

class MacOSProxyManager(SystemProxyManager):
    """Manages the macOS system proxy settings via networksetup."""
    
    def _run_networksetup(self, args: list[str]) -> str:
        try:
            result = subprocess.run(["networksetup"] + args, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"networksetup command failed: {e.stderr}")
            raise Exception(f"Failed to configure macOS proxy: {e.stderr}")
            
    def _get_active_network_services(self) -> list[str]:
        stdout = self._run_networksetup(["-listallnetworkservices"])
        services = []
        for line in stdout.splitlines():
            if line and not line.startswith("An asterisk") and not line.startswith("*"):
                services.append(line)
        return services

    def enable_proxy(self):
        services = self._get_active_network_services()
        for service in services:
            logger.info(f"Enabling proxy on macOS interface: {service}")
            self._run_networksetup(["-setwebproxy", service, self.host, str(self.port)])
            self._run_networksetup(["-setsecurewebproxy", service, self.host, str(self.port)])
            self._run_networksetup(["-setwebproxystate", service, "on"])
            self._run_networksetup(["-setsecurewebproxystate", service, "on"])

    def disable_proxy(self):
        services = self._get_active_network_services()
        for service in services:
            logger.info(f"Disabling proxy on macOS interface: {service}")
            self._run_networksetup(["-setwebproxystate", service, "off"])
            self._run_networksetup(["-setsecurewebproxystate", service, "off"])


class WindowsProxyManager(SystemProxyManager):
    """Manages the Windows system proxy settings via the Registry."""
    
    def enable_proxy(self):
        import winreg
        try:
            logger.info("Enabling proxy on Windows via Registry")
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(registry_key, 'ProxyServer', 0, winreg.REG_SZ, f"{self.host}:{self.port}")
            winreg.CloseKey(registry_key)
        except Exception as e:
            logger.error(f"Failed to enable Windows proxy: {e}")
            raise Exception(f"Failed to enable Windows proxy: {e}")

    def disable_proxy(self):
        import winreg
        try:
            logger.info("Disabling proxy on Windows via Registry")
            registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(registry_key, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(registry_key)
        except Exception as e:
             logger.error(f"Failed to disable Windows proxy: {e}")
             raise Exception(f"Failed to disable Windows proxy: {e}")


class LinuxProxyManager(SystemProxyManager):
    """Manages the Linux system proxy settings via gsettings (GNOME)."""
    
    def _run_gsettings(self, args: list[str]) -> None:
        try:
            subprocess.run(["gsettings"] + args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            logger.warning(f"gsettings command failed. Note: automatic proxy configuration is only supported on GNOME-based Linux distributions.")
            # We don't raise an exception here because Linux users might be headless and want to set HTTP_PROXY manually anyway

    def enable_proxy(self):
        logger.info("Enabling proxy on Linux via gsettings")
        # Set HTTP
        self._run_gsettings(["set", "org.gnome.system.proxy.http", "host", self.host])
        self._run_gsettings(["set", "org.gnome.system.proxy.http", "port", str(self.port)])
        # Set HTTPS
        self._run_gsettings(["set", "org.gnome.system.proxy.https", "host", self.host])
        self._run_gsettings(["set", "org.gnome.system.proxy.https", "port", str(self.port)])
        # Enable it
        self._run_gsettings(["set", "org.gnome.system.proxy", "mode", "'manual'"])

    def disable_proxy(self):
         logger.info("Disabling proxy on Linux via gsettings")
         self._run_gsettings(["set", "org.gnome.system.proxy", "mode", "'none'"])

def get_system_proxy_manager(host: str = "127.0.0.1", port: int = 8080) -> SystemProxyManager:
    """Returns the correct proxy manager for the current OS."""
    if sys.platform == "darwin":
        return MacOSProxyManager(host, port)
    elif sys.platform == "win32":
        return WindowsProxyManager(host, port)
    else:
        # Default to Linux/Unix style using gsettings
        return LinuxProxyManager(host, port)
