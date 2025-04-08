# src/web_utils.py
import logging
import time
from typing import Optional, Tuple, Dict

import requests
from requests.exceptions import RequestException, SSLError
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
from colorama import Fore # For user interaction prompts

# Import DEFAULT_SETTINGS to use for default argument values
from .config_loader import DEFAULT_SETTINGS

# --- Helper Functions ---

# ========================================
# Function: fetch_http_status_and_type
# Description: Fetch the HTTP status code and content type using requests.
# ========================================
def fetch_http_status_and_type(
    url: str,
    ssl_decision: Dict[str, bool], # Use mutable dict for state
    # Use defaults from DEFAULT_SETTINGS directly in the signature
    max_retries: int = DEFAULT_SETTINGS["request_max_retries"],
    timeout: int = DEFAULT_SETTINGS["request_timeout"]
) -> Tuple[Optional[int], Optional[str]]:
    """
    Fetch the HTTP status code and content type using requests.
    Handles retries and interactive SSL verification skipping.

    Args:
        url: The URL to fetch.
        ssl_decision: Dictionary tracking user's choice ('skip_all': True/False).
        max_retries: Maximum number of retry attempts.
        timeout: Request timeout in seconds.

    Returns:
        A tuple containing the HTTP status code (int) and content type (str),
        or (None, "Error Description") if fetching fails or user declines SSL skip.
    """
    attempt_verify = not ssl_decision.get("skip_all", False) # Initial verify state
    last_error: Optional[Exception] = None # Store the last exception

    # Now use max_retries and timeout arguments directly
    for attempt in range(max_retries):
        current_verify_state = attempt_verify # Verify state for *this* attempt
        logging.debug(f"Attempt {attempt + 1}/{max_retries} for {url} with verify={current_verify_state}")
        try:
            response = requests.head(
                url,
                allow_redirects=True,
                timeout=timeout, # Use the timeout argument
                verify=current_verify_state
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            http_code: int = response.status_code
            content_type: str = response.headers.get("Content-Type", "Unknown").split(";")[0]
            logging.debug(f"HEAD request for {url} successful: {http_code}, {content_type}")
            return http_code, content_type
        except SSLError as ssl_err:
            last_error = ssl_err
            logging.error(f"SSL error for {url} on attempt {attempt + 1}: {ssl_err}")

            if not ssl_decision.get("skip_all", False): # Only ask if not already decided
                print(Fore.YELLOW + f"\nSSL Certificate verification error encountered for: {url}")
                answer = input(
                    Fore.YELLOW + "Do you want to skip SSL verification for this and all future URLs in this session? (y/n): "
                ).strip().lower()

                if answer == 'y':
                    print(Fore.CYAN + "Okay, skipping SSL verification for future requests.")
                    ssl_decision["skip_all"] = True # Update shared state
                    attempt_verify = False # Skip for the *next* retry attempt onwards
                    # Continue to the next iteration to retry with verify=False
                else:
                    print(Fore.RED + "SSL verification not skipped. Cannot proceed with HEAD request for this URL.")
                    return None, "SSL Error (User Declined Skip)" # Return specific error
            else:
                 attempt_verify = False
                 logging.warning(f"Retrying {url} with SSL verification skipped as previously requested.")

        except RequestException as e:
            last_error = e
            logging.warning(f"Request error for {url} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logging.debug(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time) # Exponential backoff before retry
            else:
                logging.error(f"Failed to fetch {url} after {max_retries} attempts due to RequestException.")
                return None, f"Request Error ({type(e).__name__})"

        except Exception as e: # Catch any other unexpected errors
            last_error = e
            logging.error(f"Unexpected error fetching HEAD for {url} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logging.debug(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                return None, f"Unknown Error ({type(e).__name__})"

    # --- Loop finished without success ---
    logging.error(f"All {max_retries} attempts failed for {url}.")
    final_error = "Fetch Failed (Max Retries)"
    if isinstance(last_error, SSLError):
        final_error = "SSL Error (Retries Failed After Skip)" if ssl_decision.get("skip_all") else "SSL Error (User Declined Skip or Retries Failed)"
    elif isinstance(last_error, RequestException):
        final_error = f"Request Error ({type(last_error).__name__})"
    elif last_error:
        final_error = f"Unknown Error ({type(last_error).__name__})"

    return None, final_error


# ========================================
# Function: fetch_and_parse_html
# Description: Fetches HTML content using Selenium, waits for page load, parses with BeautifulSoup.
# ========================================
def fetch_and_parse_html(url: str, driver: webdriver.Chrome, page_load_timeout: int = 30) -> Optional[BeautifulSoup]:
    """
    Fetches HTML content using Selenium, waits for page load, parses with BeautifulSoup.

    Args:
        url: The URL to fetch.
        driver: The Selenium WebDriver instance.
        page_load_timeout: Maximum time in seconds to wait for page load state.

    Returns:
        A BeautifulSoup object of the page source, or None if fetching/parsing fails.
    """
    try:
        logging.debug(f"Navigating to {url} with Selenium...")
        driver.get(url)
        logging.debug(f"Waiting up to {page_load_timeout}s for page state 'complete'...")
        WebDriverWait(driver, page_load_timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logging.debug(f"Page state 'complete' reached for {url}")
        page_source = driver.page_source
        logging.debug(f"Got page source (length: {len(page_source)}). Parsing with BeautifulSoup...")
        soup = BeautifulSoup(page_source, "html.parser")
        logging.debug(f"Successfully parsed HTML for {url}")
        return soup
    except TimeoutException:
        logging.error(f"Timeout ({page_load_timeout}s) waiting for page load state 'complete' for {url}")
        return None
    except Exception as e:
        logging.error(f"Error fetching or parsing {url} with Selenium: {e}", exc_info=True)
        return None