import re
from mitmproxy import http
import keyring

APP_NAME = "proxy-shadow-keys"
SHADOW_KEY_PATTERN = re.compile(r'(shadow_[a-zA-Z0-9_]+)')

class ShadowKeyInterceptor:
    def replace_shadow_keys(self, content: str) -> str:
        """Finds shadow keys in content and replaces them with secure vault keys."""
        if not content:
            return content
            
        def replacer(match):
            shadow_key = match.group(0)
            secure_key = keyring.get_password(APP_NAME, shadow_key)
            # If secure key exists, replace it, otherwise leave as is
            return secure_key if secure_key else shadow_key

        return SHADOW_KEY_PATTERN.sub(replacer, content)

    def request(self, flow: http.HTTPFlow) -> None:
        """Intercepts HTTP requests and replaces shadow keys in headers and body."""
        # Replace in Headers
        for key, value in flow.request.headers.items():
            if 'shadow_' in value:
                flow.request.headers[key] = self.replace_shadow_keys(value)
        
        # Replace in Body
        if flow.request.content:
            try:
                # Assuming text/json content for replacement
                content_str = flow.request.content.decode('utf-8')
                if 'shadow_' in content_str:
                    modified_content = self.replace_shadow_keys(content_str)
                    flow.request.content = modified_content.encode('utf-8')
            except UnicodeDecodeError:
                # Not a decodable text body, ignore
                pass

        # Replace in URL query parameters
        if flow.request.query:
            for key, value in flow.request.query.items():
                 if 'shadow_' in value:
                     flow.request.query[key] = self.replace_shadow_keys(value)

addons = [
    ShadowKeyInterceptor()
]
