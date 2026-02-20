import re
from mitmproxy import http
import keyring

APP_NAME = "proxy-shadow-keys"
SHADOW_KEY_PATTERN = re.compile(r'(shadow_[a-zA-Z0-9_]+)')

class ShadowKeyInterceptor:
    def load(self, loader):
        loader.add_option(
            name="manage_system_proxy",
            typespec=bool,
            default=False,
            help="Auto-disable system proxy on shutdown"
        )

    def done(self):
        from mitmproxy import ctx
        if ctx.options.manage_system_proxy:
            import logging
            from proxy_shadow_keys.system_proxy import get_system_proxy_manager
            try:
                get_system_proxy_manager().disable_proxy()
                logging.info("Auto-disabled system proxy on shutdown.")
            except Exception as e:
                logging.error(f"Failed to auto-disable system proxy: {e}")

    def replace_shadow_keys(self, content: str, request_host: str) -> str:
        """Finds shadow keys in content and replaces them with secure vault keys."""
        if not content:
            return content
            
        def replacer(match):
            import os
            import json
            import fnmatch
            shadow_key = match.group(0)
            
            if os.environ.get("SHADOW_KEYS_TEST_MODE") == "1":
                if shadow_key == "shadow_e2e_key":
                    secure_key_data = '{"value": "my_real_secret_key_123", "allowed_hosts": []}'
                else:
                    secure_key_data = None
            else:
                secure_key_data = keyring.get_password(APP_NAME, shadow_key)
            
            if not secure_key_data:
                return shadow_key
                
            value = secure_key_data
            allowed_hosts = []
            
            if secure_key_data.startswith("{"):
                try:
                    data = json.loads(secure_key_data)
                    value = data.get("value", shadow_key)
                    allowed_hosts = data.get("allowed_hosts", [])
                except json.JSONDecodeError:
                    pass
                    
            if allowed_hosts:
                if not any(fnmatch.fnmatch(request_host, host) for host in allowed_hosts):
                    return shadow_key

            return value

        return SHADOW_KEY_PATTERN.sub(replacer, content)

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercepts HTTP requests and replaces shadow keys in headers and body."""
        request_host = flow.request.host
        
        # Replace in Headers
        for key, value in flow.request.headers.items():
            if 'shadow_' in value:
                flow.request.headers[key] = self.replace_shadow_keys(value, request_host)
        
        # Replace in Body
        if flow.request.content:
            try:
                # Assuming text/json content for replacement
                content_str = flow.request.content.decode('utf-8')
                if 'shadow_' in content_str:
                    modified_content = self.replace_shadow_keys(content_str, request_host)
                    flow.request.content = modified_content.encode('utf-8')
            except UnicodeDecodeError:
                # Not a decodable text body, ignore
                pass

        # Replace in URL query parameters
        if flow.request.query:
            for key, value in flow.request.query.items():
                 if 'shadow_' in value:
                     flow.request.query[key] = self.replace_shadow_keys(value, request_host)

addons = [
    ShadowKeyInterceptor()
]
