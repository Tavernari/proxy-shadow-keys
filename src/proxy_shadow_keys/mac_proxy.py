import subprocess
import logging

logger = logging.getLogger(__name__)

class MacOSProxyManager:
    """Manages the macOS system proxy settings via networksetup."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
    
    def _run_networksetup(self, args: list[str]) -> str:
        try:
            result = subprocess.run(["networksetup"] + args, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"networksetup command failed: {e.stderr}")
            raise Exception(f"Failed to configure macOS proxy: {e.stderr}")
            
    def _get_active_network_services(self) -> list[str]:
        """Returns a list of all active network services (e.g., 'Wi-Fi', 'Ethernet')."""
        stdout = self._run_networksetup(["-listallnetworkservices"])
        services = []
        for line in stdout.splitlines():
            # Skip the first informational line and any disabled services (which have an asterisk)
            if line and not line.startswith("An asterisk") and not line.startswith("*"):
                services.append(line)
        return services

    def enable_proxy(self):
        """Enables the web and secure web proxy for all active network services."""
        services = self._get_active_network_services()
        for service in services:
            logger.info(f"Enabling proxy on {service}")
            self._run_networksetup(["-setwebproxy", service, self.host, str(self.port)])
            self._run_networksetup(["-setsecurewebproxy", service, self.host, str(self.port)])
            self._run_networksetup(["-setwebproxystate", service, "on"])
            self._run_networksetup(["-setsecurewebproxystate", service, "on"])

    def disable_proxy(self):
        """Disables the web and secure web proxy for all active network services."""
        services = self._get_active_network_services()
        for service in services:
            logger.info(f"Disabling proxy on {service}")
            self._run_networksetup(["-setwebproxystate", service, "off"])
            self._run_networksetup(["-setsecurewebproxystate", service, "off"])

