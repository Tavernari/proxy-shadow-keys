import pytest
import subprocess
import time
import urllib.request
import urllib.error
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SERVER_PORT = 9999
PROXY_PORT = 8899
REAL_KEY = "my_real_secret_key_123"
SHADOW_KEY = "shadow_e2e_key"

class E2EHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        auth_header = self.headers.get("Authorization")
        expected = f"Bearer {REAL_KEY}"
        
        if auth_header == expected:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(f"Not Found. Got: {auth_header}".encode())
            
    def log_message(self, format, *args):
        # Suppress logging to keep test output clean
        pass

class ReusableServer(HTTPServer):
    allow_reuse_address = True

@pytest.fixture(scope="module")
def fake_server():
    server = ReusableServer(("127.0.0.1", SERVER_PORT), E2EHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield
    server.shutdown()
    server.server_close()
    thread.join()

def run_cli(args):
    """Helper to run the CLI directly."""
    return subprocess.run(["proxy-shadow-keys"] + args, capture_output=True, text=True, check=True)

def test_e2e_proxy_interception(fake_server):
    import os
    os.environ["SHADOW_KEYS_TEST_MODE"] = "1"
    try:
        # 1. Store the key
        run_cli(["set", SHADOW_KEY, REAL_KEY])
        
        # 2. Start the proxy
        try:
            run_cli(["start", "--port", str(PROXY_PORT), "--no-system-proxy"])
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to start proxy:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        
        # Give mitmproxy a moment to fully bind to the port
        time.sleep(2)
        
        # 3. Make a proxied request
        proxy_support = urllib.request.ProxyHandler({'http': f'http://127.0.0.1:{PROXY_PORT}'})
        opener = urllib.request.build_opener(proxy_support)
        urllib.request.install_opener(opener)
        
        req = urllib.request.Request(f"http://127.0.0.1:{SERVER_PORT}/")
        req.add_header("Authorization", f"Bearer {SHADOW_KEY}")
        
        # If the proxy works, it replaces "shadow_e2e_key" -> "my_real_secret_key_123"
        # The fake_server returns 200
        try:
            response = urllib.request.urlopen(req, timeout=5)
            assert response.status == 200
            assert response.read() == b"OK"
        except urllib.error.HTTPError as e:
            pytest.fail(f"HTTPError: Expected 200 OK, got {e.code}. Response body: {e.read()}")
            
    finally:
        # 4. Clean up
        try:
            run_cli(["stop", "--no-system-proxy"])
        except Exception as e:
            print(f"Cleanup failed on stop: {e}")
            
        try:
            run_cli(["rm", SHADOW_KEY])
        except Exception as e:
            print(f"Cleanup failed on rm: {e}")
            
        if "SHADOW_KEYS_TEST_MODE" in os.environ:
            del os.environ["SHADOW_KEYS_TEST_MODE"]

def test_e2e_allow_host_whitelist(fake_server):
    import os
    import json
    os.environ["SHADOW_KEYS_TEST_MODE"] = "1"
    os.environ["SHADOW_KEY_MOCK_DATA"] = json.dumps({"value": REAL_KEY, "allowed_hosts": ["127.0.0.1"]})
    try:
        # 1. Store the key with an allowed host
        run_cli(["set", SHADOW_KEY, REAL_KEY, "--allow-host", "127.0.0.1"])
        
        # 2. Start the proxy
        try:
            run_cli(["start", "--port", str(PROXY_PORT), "--no-system-proxy"])
        except subprocess.CalledProcessError as e:
            pytest.fail(f"Failed to start proxy:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        
        time.sleep(2)
        
        # 3. Setup proxy for urllib
        proxy_support = urllib.request.ProxyHandler({'http': f'http://127.0.0.1:{PROXY_PORT}'})
        opener = urllib.request.build_opener(proxy_support)
        urllib.request.install_opener(opener)
        
        # 4. Request 1: Allowed Host (127.0.0.1)
        req1 = urllib.request.Request(f"http://127.0.0.1:{SERVER_PORT}/")
        req1.add_header("Authorization", f"Bearer {SHADOW_KEY}")
        
        try:
            response1 = urllib.request.urlopen(req1, timeout=5)
            assert response1.status == 200
            assert response1.read() == b"OK"
        except urllib.error.HTTPError as e:
            pytest.fail(f"HTTPError on allowed host: {e.code}. Response body: {e.read()}")
            
        # 5. Request 2: Disallowed Host (uses localhost instead of 127.0.0.1)
        req2 = urllib.request.Request(f"http://localhost:{SERVER_PORT}/")
        req2.add_header("Authorization", f"Bearer {SHADOW_KEY}")
        
        try:
            response2 = urllib.request.urlopen(req2, timeout=5)
            pytest.fail("Request 2 should have failed with 404 because shadow key was NOT replaced.")
        except urllib.error.HTTPError as e:
            assert e.code == 404
            # The server will log that it received the literal 'shadow_e2e_key' instead of 'my_real_secret_key_123'
            assert b"shadow_e2e_key" in e.read()

    finally:
        # 4. Clean up
        try:
            run_cli(["stop", "--no-system-proxy"])
        except Exception:
            pass
            
        try:
            run_cli(["rm", SHADOW_KEY])
        except Exception:
            pass
            
        if "SHADOW_KEYS_TEST_MODE" in os.environ:
            del os.environ["SHADOW_KEYS_TEST_MODE"]
