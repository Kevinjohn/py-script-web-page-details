# test_connection.py
import requests
import os
import sys

# --- Configuration ---
# This is a common URL webdriver-manager needs to check for the latest version
# You could also try "https://chromedriver.storage.googleapis.com/"
TARGET_URL = "https://chromedriver.storage.googleapis.com/LATEST_RELEASE"
TIMEOUT_SECONDS = 15 # Increased timeout slightly just in case

print(f"Attempting to connect to: {TARGET_URL}")
print("-" * 30)

# --- Check for Proxy Environment Variables ---
http_proxy = os.environ.get('HTTP_PROXY')
https_proxy = os.environ.get('HTTPS_PROXY')

if http_proxy:
    print(f"INFO: HTTP_PROXY environment variable found: {http_proxy}")
if https_proxy:
    print(f"INFO: HTTPS_PROXY environment variable found: {https_proxy}")
if not http_proxy and not https_proxy:
    print("INFO: No HTTP_PROXY or HTTPS_PROXY environment variables found.")
    # Note: Python requests might still pick up system proxy settings even if env vars aren't set.

print("-" * 30)

# --- Attempt Connection ---
try:
    print(f"Making request with timeout={TIMEOUT_SECONDS}s...")
    # Explicitly trust environment settings for proxies
    # You might need to configure verify=False if using a corporate proxy with custom certs,
    # but try without it first. Add verify=False only if you get SSL errors.
    response = requests.get(TARGET_URL, timeout=TIMEOUT_SECONDS, proxies=None) # proxies=None explicitly tells requests to use env vars if set

    response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

    print(f"\nSUCCESS! Connection established.")
    print(f"Status Code: {response.status_code}")
    print(f"Content (first 100 bytes): {response.content[:100]}...")

except requests.exceptions.ProxyError as e:
    print(f"\nERROR: Proxy Error occurred.")
    print("This strongly suggests an issue with the proxy configuration or accessibility.")
    print(f"Details: {e}")
    sys.exit(1) # Exit with error code

except requests.exceptions.SSLError as e:
     print(f"\nERROR: SSL Error occurred.")
     print("This might indicate a corporate proxy intercepting traffic with a custom certificate.")
     print("You may need to configure certificate verification (e.g., set REQUESTS_CA_BUNDLE env var or use verify=False - use verify=False with caution).")
     print(f"Details: {e}")
     sys.exit(1)

except requests.exceptions.Timeout as e:
    print(f"\nERROR: Connection timed out after {TIMEOUT_SECONDS} seconds.")
    print("This could be a firewall blocking the connection, a slow network, or the server being temporarily unresponsive.")
    print(f"Details: {e}")
    sys.exit(1)

except requests.exceptions.ConnectionError as e:
    print(f"\nERROR: Connection Error occurred.")
    print(f"This often indicates a DNS issue, refused connection, or network problem preventing access to the host.")
    print("Check firewall rules and general network connectivity to the target host.")
    print(f"Details: {e}")
    sys.exit(1)

except requests.exceptions.RequestException as e:
    # Catch any other Requests exceptions (like HTTPError from raise_for_status)
    print(f"\nERROR: An error occurred during the request.")
    print(f"Type: {type(e).__name__}")
    if hasattr(e, 'response') and e.response is not None:
         print(f"Status Code: {e.response.status_code}")
         print(f"Response: {e.response.text[:200]}...")
    print(f"Details: {e}")
    sys.exit(1)

except Exception as e:
     print(f"\nERROR: An unexpected error occurred: {type(e).__name__}")
     print(f"Details: {e}")
     sys.exit(1)

print("-" * 30)
print("Test finished.")