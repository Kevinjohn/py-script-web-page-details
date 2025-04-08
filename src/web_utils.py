# src/web_utils.py
import logging
import time # Import time
from typing import Optional, Tuple, Dict

import requests
from requests.exceptions import RequestException, SSLError
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException # Added WebDriverException
from bs4 import BeautifulSoup
from colorama import Fore

from .config_loader import DEFAULT_SETTINGS

# --- Helper Functions ---

# ========================================
# Function: fetch_http_status_and_type
# Description: Fetch the HTTP status code and content type using requests.
# ========================================
# (No changes needed in this function from the last working version)
def fetch_http_status_and_type(
    url: str,
    ssl_decision: Dict[str, bool],
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
    attempt_verify = not ssl_decision.get("skip_all", False)
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        current_verify_state = attempt_verify
        logging.debug(f"Attempt {attempt + 1}/{max_retries} for {url} with verify={current_verify_state}")
        try:
            response = requests.head(
                url,
                allow_redirects=True,
                timeout=timeout,
                verify=current_verify_state
            )
            response.raise_for_status()
            http_code: int = response.status_code
            content_type: str = response.headers.get("Content-Type", "Unknown").split(";")[0]
            logging.debug(f"HEAD request for {url} successful: {http_code}, {content_type}")
            return http_code, content_type
        except SSLError as ssl_err:
            last_error = ssl_err
            logging.error(f"SSL error for {url} on attempt {attempt + 1}: {ssl_err}")

            if not ssl_decision.get("skip_all", False):
                print(Fore.YELLOW + f"\nSSL Certificate verification error encountered for: {url}")
                answer = input(
                    Fore.YELLOW + "Do you want to skip SSL verification for this and all future URLs in this session? (y/n): "
                ).strip().lower()

                if answer == 'y':
                    print(Fore.CYAN + "Okay, skipping SSL verification for future requests.")
                    ssl_decision["skip_all"] = True
                    attempt_verify = False
                else:
                    print(Fore.RED + "SSL verification not skipped. Cannot proceed with HEAD request for this URL.")
                    return None, "SSL Error (User Declined Skip)"
            else:
                 attempt_verify = False
                 logging.warning(f"Retrying {url} with SSL verification skipped as previously requested.")

        except RequestException as e:
            last_error = e
            logging.warning(f"Request error for {url} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logging.debug(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                logging.error(f"Failed to fetch {url} after {max_retries} attempts due to RequestException.")
                return None, f"Request Error ({type(e).__name__})"

        except Exception as e:
            last_error = e
            logging.error(f"Unexpected error fetching HEAD for {url} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logging.debug(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                return None, f"Unknown Error ({type(e).__name__})"

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
# Function: fetch_and_parse_html (Updated)
# Description: Fetches HTML content using Selenium, waits for page load, parses with BeautifulSoup.
# ========================================
def fetch_and_parse_html(
    url: str,
    driver: webdriver.Chrome,
    page_load_timeout: int = 30,
    wait_after_load: int = 0 # NEW Argument with default
    ) -> Optional[BeautifulSoup]:
    """
    Fetches HTML content using Selenium, waits for page load, optionally waits longer,
    and parses with BeautifulSoup.

    Args:
        url: The URL to fetch.
        driver: The Selenium WebDriver instance.
        page_load_timeout: Maximum time in seconds to wait for page load state.
        wait_after_load: Additional fixed seconds to wait after page load state is complete.

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

        # --- NEW: Add optional fixed wait ---
        if wait_after_load > 0:
            logging.debug(f"Performing fixed wait of {wait_after_load}s after page load state reached.")
            time.sleep(wait_after_load)
        # --- End NEW ---

        page_source = driver.page_source
        logging.debug(f"Got page source (length: {len(page_source)}). Parsing with BeautifulSoup...")
        # Handle potential errors during parsing itself if needed
        try:
            soup = BeautifulSoup(page_source, "html.parser")
            logging.debug(f"Successfully parsed HTML for {url}")
            return soup
        except Exception as parse_err: # Catch errors during BS parsing specifically
             logging.error(f"Error parsing HTML content for {url} with BeautifulSoup: {parse_err}", exc_info=True)
             return None

    except TimeoutException:
        logging.error(f"Timeout ({page_load_timeout}s) waiting for page load state 'complete' for {url}")
        return None
    except WebDriverException as wd_err: # More specific catch for webdriver errors
         logging.error(f"WebDriver error navigating to/interacting with {url}: {wd_err}", exc_info=False) # Often long tracebacks
         return None
    except Exception as e: # Catch other unexpected errors during Selenium interaction
        logging.error(f"Unexpected error fetching or processing {url} with Selenium: {e}", exc_info=True)
        return None