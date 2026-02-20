import pytest
import subprocess
import os

@pytest.fixture(scope="session", autouse=True)
def ensure_proxy_disabled():
    yield
    # After all tests, ensure the system proxy is disabled
    try:
        # We use --no-system-proxy as a safeguard, but the user wants to ensure 
        # it's disabled if it was accidentally enabled.
        subprocess.run(["proxy-shadow-keys", "stop"], capture_output=True)
    except Exception:
        pass
