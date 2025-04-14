import os
import time
import csv
import logging
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional, List, Dict, Tuple, Any # Added typing imports

import requests
from requests.exceptions import RequestException, SSLError
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait # Added WebDriverWait
from selenium.common.exceptions import TimeoutException # Added TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import yaml

# Initialise Colorama
init(autoreset=True)

# Load Configuration
try:
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
        settings = config.get("settings", {}) # Use .get for safer access
except FileNotFoundError:
    logging.error("CRITICAL: config.yaml not found. Please create it.")
    exit(1)
except yaml.YAMLError as e:
    logging.error(f"CRITICAL: Error parsing config.yaml: {e}")
    exit(1)

# --- Configuration Variables ---
# Use .get() with defaults for robustness
INPUT_FILE: str = settings.get("input_file", "input_urls.txt")
OUTPUT_BASE_DIR: str = settings.get("output_base_dir", "output")
OUTPUT_SUBFOLDER: str = settings.get("output_subfolder", "metadata_reports")
LOG_LEVEL_STR: str = settings.get("log_level", "INFO")
HEADLESS: bool = settings.get("headless", True)
WINDOW_WIDTH: int = settings.get("window_width", 1440)
WINDOW_HEIGHT: int = settings.get("window_height", 1080)
# Added config options (with defaults)
REQUEST_MAX_RETRIES: int = settings.get("request_max_retries", 3)
REQUEST_TIMEOUT: int = settings.get("request_timeout", 10) # seconds
SKIP_SSL_CHECK_ON_ERROR: bool = settings.get("skip_ssl_check_on_error", False)


# --- Configure logging ---
log_level: int = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Logging configured.")


# --- Helper Functions ---

# --- Helper Functions ---

def fetch_http_status_and_type(
    url: str,
    ssl_decision: Dict[str, bool], # Use mutable dict for state
    max_retries: int = REQUEST_MAX_RETRIES,
    timeout: int = REQUEST_TIMEOUT
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

    for attempt in range(max_retries):
        try:
            response = requests.head(
                url,
                allow_redirects=True,
                timeout=timeout,
                verify=attempt_verify # Use current attempt's verify state
            )
            http_code: int = response.status_code
            content_type: str = response.headers.get("Content-Type", "Unknown").split(";")[0]
            logging.debug(f"HEAD request for {url} successful: {http_code}, {content_type}")
            return http_code, content_type
        except SSLError as ssl_err:
            logging.error(f"SSL error for {url} on attempt {attempt + 1}: {ssl_err}")

            # Check if we should ask the user or if they already said yes
            if not ssl_decision.get("skip_all", False):
                print(Fore.YELLOW + f"SSL Certificate verification error encountered for: {url}")
                answer = input(
                    Fore.YELLOW + "Do you want to skip SSL verification for this and all future URLs in this session? (y/n): "
                ).strip().lower()

                if answer == 'y':
                    print(Fore.CYAN + "Okay, skipping SSL verification for future requests.")
                    ssl_decision["skip_all"] = True # Update shared state
                    attempt_verify = False # Skip verification for the *next* retry attempt
                    # Continue to the next iteration to retry with verify=False
                else:
                    print(Fore.RED + "SSL verification not skipped. Cannot proceed with this URL.")
                    return None, "SSL Error (User Declined Skip)" # Return specific error
            else:
                # User already agreed to skip all, retry immediately without verification
                 attempt_verify = False
                 logging.warning(f"Retrying {url} with SSL verification skipped as previously requested.")
                 # No time.sleep here, immediately retry in the next loop iteration

        except RequestException as e:
            logging.warning(f"Request error for {url} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff before retry
            else:
                logging.error(f"Failed to fetch {url} after {max_retries} attempts due to RequestException.")
                return None, "Request Error"
        except Exception as e: # Catch any other unexpected errors
             logging.error(f"Unexpected error fetching HEAD for {url} on attempt {attempt + 1}: {e}")
             if attempt < max_retries - 1:
                 time.sleep(2 ** attempt)
             else:
                 return None, "Unknown Error"

        # --- Important: Only sleep if it wasn't an SSL error we are immediately retrying ---
        # (Prevents double sleep: one here, one if RequestException follows the SSL retry)
        # We only reach here after the except blocks if we need to retry (and it wasn't an SSLError where user said 'y')
        if attempt < max_retries - 1:
             # Check if we are about to retry an SSLError without verify (user said 'y')
             # In this specific case, we don't sleep here because the loop will immediately retry.
             # We only sleep for non-SSL errors or if user said 'n' to SSL skip (which returns).
             if not isinstance(ssl_err, SSLError) or not ssl_decision.get("skip_all", False):
                 time.sleep(2 ** attempt) # Exponential backoff only for non-SSL retries


    logging.error(f"All {max_retries} attempts failed for {url}.")
    # Determine final error type if loop finishes
    final_error = "Fetch Failed"
    if isinstance(ssl_err, SSLError) and not ssl_decision.get("skip_all", False):
        final_error = "SSL Error (User Declined Skip or Retries Failed)"
    elif isinstance(ssl_err, SSLError):
        final_error = "SSL Error (Retries Failed After Skip)"

    return None, final_error


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
        driver.get(url)
        # Wait for the document.readyState to be 'complete'
        WebDriverWait(driver, page_load_timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logging.debug(f"Page state 'complete' reached for {url}")
        # Optional short sleep respecting potential rate limits after load confirmed
        time.sleep(1)
        return BeautifulSoup(driver.page_source, "html.parser")
    except TimeoutException:
        logging.error(f"Timeout ({page_load_timeout}s) waiting for page load state 'complete' for {url}")
        return None
    except Exception as e:
        logging.error(f"Error fetching or parsing {url} with Selenium: {e}")
        return None


def extract_meta_content(soup: BeautifulSoup, meta_name: str) -> str:
    """
    Extract content from a specific meta tag (name or property).

    Args:
        soup: BeautifulSoup object of the page.
        meta_name: The 'name' or 'property' attribute value of the meta tag.

    Returns:
        The content of the meta tag, or an empty string if not found or on error.
    """
    try:
        tag = soup.find("meta", attrs={"name": meta_name}) or \
              soup.find("meta", attrs={"property": meta_name})
        return tag["content"].strip() if tag and tag.has_attr("content") else ""
    except Exception as e:
        logging.warning(f"Error extracting meta content for '{meta_name}': {e}")
        return ""


def extract_meta_title(soup: BeautifulSoup) -> str:
    """
    Extract the text content from the <title> tag.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        The title text, or an empty string if not found or on error.
    """
    try:
        return soup.title.string.strip() if soup.title and soup.title.string else ""
    except Exception as e:
        logging.warning(f"Error extracting meta title: {e}")
        return ""


def extract_h1(soup: BeautifulSoup, scope_selector: Optional[str] = "article") -> str:
    """
    Extract the text of the first H1 tag, optionally within a specific scope.

    Args:
        soup: BeautifulSoup object of the page.
        scope_selector: CSS selector for the scope (e.g., 'article', 'main').
                        If None, searches the whole document.

    Returns:
        The H1 text, or an empty string if not found or on error.
    """
    try:
        scope = soup.find(scope_selector) if scope_selector else soup
        if scope:
            h1 = scope.find("h1")
            return h1.text.strip() if h1 else ""
        return ""
    except Exception as e:
        logging.warning(f"Error extracting H1 within scope '{scope_selector}': {e}")
        return ""


def count_tags(soup: BeautifulSoup, tags: List[str], scope_selector: Optional[str] = "article") -> int:
    """
    Counts specified tags (e.g., H1-H6, img) within an optional scope.

    Args:
        soup: BeautifulSoup object of the page.
        tags: A list of tag names to count (e.g., ['h1', 'h2', 'h3']).
        scope_selector: CSS selector for the scope. If None, searches the whole document.

    Returns:
        The count of the specified tags, or 0 on error or if scope not found.
    """
    try:
        scope = soup.find(scope_selector) if scope_selector else soup
        return len(scope.find_all(tags)) if scope else 0
    except Exception as e:
        logging.warning(f"Error counting tags '{tags}' within scope '{scope_selector}': {e}")
        return 0


def count_links(soup: BeautifulSoup, base_url: str, internal: bool, scope_selector: Optional[str] = "article") -> int:
    """
    Counts internal or external links within an optional scope.

    Args:
        soup: BeautifulSoup object of the page.
        base_url: The base URL of the page being analyzed (for domain comparison).
        internal: If True, count internal links; otherwise, count external links.
        scope_selector: CSS selector for the scope. If None, searches the whole document.

    Returns:
        The count of links, or 0 on error or if scope not found.
    """
    count = 0
    try:
        scope = soup.find(scope_selector) if scope_selector else soup
        if not scope:
            return 0

        base_domain = urlparse(base_url).netloc
        links = scope.find_all("a", href=True)

        for link in links:
            href = link["href"]
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue # Skip anchors, mailto, tel links

            link_domain = urlparse(href).netloc
            # Simple check: same domain is internal, different or empty is external
            is_internal = base_domain in href or (not link_domain and (href.startswith('/') or not href.startswith('http')))

            if internal and is_internal:
                count += 1
            elif not internal and not is_internal:
                count += 1
        return count
    except Exception as e:
        logging.warning(f"Error counting {'internal' if internal else 'external'} links: {e}")
        return 0


def count_images_no_alt(soup: BeautifulSoup, scope_selector: Optional[str] = "article") -> int:
    """
    Counts images without alt text or with empty alt text within an optional scope.

    Args:
        soup: BeautifulSoup object of the page.
        scope_selector: CSS selector for the scope. If None, searches the whole document.

    Returns:
        The count of images without proper alt text, or 0 on error or if scope not found.
    """
    try:
        scope = soup.find(scope_selector) if scope_selector else soup
        if not scope:
            return 0
        images = scope.find_all("img")
        # Count if 'alt' attribute is missing OR if it's present but empty/whitespace
        return sum(1 for img in images if not img.get("alt", "").strip())
    except Exception as e:
        logging.warning(f"Error counting images without alt text: {e}")
        return 0


def extract_page_slug(url: str) -> str:
    """
    Extract the page slug (last part of the path) from the URL.

    Args:
        url: The URL string.

    Returns:
        The slug, 'homepage' if path is '/', or 'unknown' on error.
    """
    try:
        path = urlparse(url).path
        # Handle potential empty paths or just "/"
        if not path or path == "/":
            return "homepage"
        # Get the last non-empty part of the path
        slug = path.rstrip("/").split("/")[-1]
        return slug if slug else "unknown" # Fallback if split results in empty
    except Exception as e:
        logging.warning(f"Error extracting page slug from {url}: {e}")
        return "unknown"


def extract_body_class(soup: BeautifulSoup, prefix: str, default: Optional[str] = None) -> Optional[str]:
    """
    Extracts the value of a specific class prefixed class from the body tag.

    Args:
        soup: BeautifulSoup object of the page.
        prefix: The prefix of the class name to find (e.g., 'page-id-').
        default: The value to return if the class is not found.

    Returns:
        The class value (without prefix), or the default value.
    """
    try:
        body = soup.body
        if body and body.has_attr("class"):
            for cls in body["class"]:
                if cls.startswith(prefix):
                    return cls.replace(prefix, "").strip()
        return default
    except Exception as e:
        logging.warning(f"Error extracting body class with prefix '{prefix}': {e}")
        return default


def extract_placeholder_data(soup: BeautifulSoup, data_type: str) -> Optional[Any]:
    """Placeholder function for future data extraction."""
    logging.debug(f"Placeholder function called for {data_type}. Needs implementation.")
    return None # Consistent return for unimplemented/failed extraction


# --- Orchestration ---

# --- Orchestration ---

def extract_metadata(
    url: str,
    driver: webdriver.Chrome,
    ssl_decision: Dict[str, bool] # Accept the decision state
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the extraction of various metadata elements for a given URL.

    Args:
        url: The URL to analyze.
        driver: The Selenium WebDriver instance.
        ssl_decision: Dictionary tracking the user's decision on skipping SSL.

    Returns:
        A dictionary containing the extracted metadata, or None if a critical
        error occurs (e.g., unable to fetch status or parse HTML).
    """
    logging.info(f"Starting metadata extraction for: {url}")
    try:
        # Pass the ssl_decision dict down
        http_code, http_type = fetch_http_status_and_type(url, ssl_decision=ssl_decision)
        page_slug = extract_page_slug(url)

        # Basic info always returned if HEAD request worked, even if not HTML
        base_data = {
            "http-code": http_code,
            "http-type": http_type,
            "Page-URL": url,
            "page-slug": page_slug,
            # Initialize all fields
            "Page-id": None, "Parent-ID": None, "Parent-URL": "", "IA error": "",
            "Title": "", "Description": "", "Keywords": "",
            "Opengraph type": "", "Opengraph image": "", "Opengraph title": "", "Opengraph description": "",
            "Article H1": "", "Article Headings": 0,
            "Article Links Internal": 0, "Article Links External": 0,
            "Article Images": 0, "Article Images NoAlt": 0,
            "content-count": None, "content-ratio": None,
        }

        if http_type == "SSL Error (User Declined Skip)":
             base_data["IA error"] = "SSL Error (User Declined Skip)"
             logging.warning(f"Skipping detailed parsing for {url} due to user declining SSL skip.")
             return base_data # Return basic info with error flag

        if http_code is None or http_type is None or "html" not in str(http_type).lower():
            logging.warning(f"Skipping detailed parsing for {url}. Status: {http_code}, Type: {http_type}")
            # Add specific error if known
            if http_type in ["SSL Error", "Request Error", "Unknown Error", "Fetch Failed"]:
                 base_data["IA error"] = http_type
            return base_data # Return basic info if not HTML or fetch failed

        soup = fetch_and_parse_html(url, driver)
        if not soup:
            logging.error(f"Failed to fetch or parse HTML for {url}. Cannot extract further details.")
            base_data["IA error"] = "Failed to fetch/parse HTML"
            return base_data

        # --- Extract detailed data if HTML is available ---
        article_scope = "article"

        meta_data = {
            "Title": extract_meta_title(soup),
            "Description": extract_meta_content(soup, "description"),
            "Keywords": extract_meta_content(soup, "keywords"),
            "Opengraph type": extract_meta_content(soup, "og:type"),
            "Opengraph image": extract_meta_content(soup, "og:image"),
            "Opengraph title": extract_meta_content(soup, "og:title"),
            "Opengraph description": extract_meta_content(soup, "og:description"),
        }

        article_data = {
            "Article H1": extract_h1(soup, scope_selector=article_scope),
            "Article Headings": count_tags(soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector=article_scope),
            "Article Links Internal": count_links(soup, url, internal=True, scope_selector=article_scope),
            "Article Links External": count_links(soup, url, internal=False, scope_selector=article_scope),
            "Article Images": count_tags(soup, ["img"], scope_selector=article_scope),
            "Article Images NoAlt": count_images_no_alt(soup, scope_selector=article_scope),
        }

        other_data = {
            "Page-id": extract_body_class(soup, "page-id-"),
            "Parent-ID": extract_body_class(soup, "parent-pageid-", default="0"),
            "content-count": extract_placeholder_data(soup, "content-count"),
            "content-ratio": extract_placeholder_data(soup, "content-ratio"),
        }

        return {**base_data, **meta_data, **article_data, **other_data}

    except Exception as e:
        logging.exception(f"Critical unexpected error during metadata extraction for {url}: {e}")
        return None

# --- File Operations ---

# --- File Operations ---

def read_input_file(input_file_path: str) -> List[str]:
    """
    Reads URLs from a specified input file, one URL per line.
    If the initial path is invalid, prompts the user for a correct path.

    Args:
        input_file_path: The initial path to the input file (from config).

    Returns:
        A list of valid URLs found in the file. Returns empty list on critical error.
    """
    current_path = input_file_path
    # --- Added check and interactive prompt ---
    while not os.path.exists(current_path):
        logging.warning(f"Input file specified in config not found: {current_path}")
        print(Fore.YELLOW + f"Input file specified ('{current_path}') not found.")
        new_path = input(Fore.CYAN + "Please enter the correct path to the input URL file: ").strip()
        # Basic check if the user provided any input
        if not new_path:
             print(Fore.RED + "No path entered. Exiting.")
             return [] # Exit if user provides no path
        current_path = new_path
    # --- End of added check ---

    urls: List[str] = []
    try:
        with open(current_path, "r", encoding="utf-8") as file:
            for line in file:
                url = line.strip()
                if url and urlparse(url).scheme in ["http", "https"]: # Basic URL validation
                    urls.append(url)
                elif url:
                    logging.warning(f"Skipping invalid or non-HTTP(S) line in input file: {url}")
        logging.info(f"Read {len(urls)} valid URLs from {current_path}")
        return urls
    except IOError as e:
        logging.error(f"Error reading input file {current_path}: {e}")
        print(Fore.RED + f"Error reading file: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error reading input file {current_path}: {e}")
        print(Fore.RED + f"An unexpected error occurred reading the file: {e}")
        return []


def sanitise_domain(url: str) -> str:
    """
    Extracts and sanitises the domain name from a URL for use in filenames.

    Args:
        url: The URL string.

    Returns:
        A sanitised domain name (e.g., 'www_example_com') or 'unknown_domain'.
    """
    try:
        domain = urlparse(url).netloc
        # Replace common invalid filename characters
        sanitised = domain.replace(".", "_").replace(":", "_").replace("/", "_")
        return sanitised if sanitised else "unknown_domain"
    except Exception as e:
        logging.warning(f"Error sanitising domain for {url}: {e}")
        return "unknown_domain"


def write_to_csv(file_path: str, data: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    """
    Writes a list of dictionaries to a CSV file.

    Args:
        file_path: The full path to the output CSV file.
        data: A list of dictionaries, where each dictionary represents a row.
        fieldnames: A list of strings defining the header row and column order.
    """
    if not data:
        logging.warning("No data to write to CSV.")
        return
    try:
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            # Use extrasaction='ignore' if data dicts might have extra keys
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)
        logging.info(f"Successfully wrote {len(data)} rows to {file_path}")
    except IOError as e:
        logging.error(f"Error writing to CSV file {file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error writing CSV {file_path}: {e}")


# --- Main Execution ---

# --- Main Execution ---

def main() -> None:
    """Main script execution function."""
    logging.info("Script starting.")

    # --- Read Input File (includes interactive prompt if needed) ---
    urls = read_input_file(INPUT_FILE) # Using the updated read_input_file from previous step
    if not urls:
        logging.critical("No valid URLs found in input file. Exiting.")
        print(Fore.RED + "Error: No valid URLs found. Check input file and logs.")
        return # Exit if no URLs

    # --- User prompt for number of URLs (optional) ---
    num_to_process_str = input(
        f"{Fore.CYAN}How many URLs to process? (Enter 0 or leave blank for all {len(urls)}): "
    ).strip()
    try:
        num_to_process = int(num_to_process_str) if num_to_process_str else 0
        if num_to_process < 0:
            num_to_process = 0
        if num_to_process > 0:
            urls = urls[:num_to_process]
            logging.info(f"Processing the first {len(urls)} URLs as requested.")
        else:
            logging.info("Processing all URLs.")
    except ValueError:
        logging.warning("Invalid input for number of URLs, processing all.")
        num_to_process = 0


    # --- Setup Output Path ---
    output_dir = os.path.join(OUTPUT_BASE_DIR, OUTPUT_SUBFOLDER)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitised_domain = sanitise_domain(urls[0]) if urls else "unknown_domain" # Use first URL for filename base
    output_csv_file = f"page_details_{sanitised_domain}_{timestamp}.csv"
    output_path = os.path.join(output_dir, output_csv_file)
    logging.info(f"Output CSV will be saved to: {output_path}")

    # --- Configure Selenium WebDriver ---
    options = Options()
    if HEADLESS:
        options.add_argument('--headless=new') # Use modern headless
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}')

    driver: Optional[webdriver.Chrome] = None # Initialize driver variable
    metadata_list: List[Dict[str, Any]] = []
    # --- Initialize SSL decision state ---
    ssl_decision: Dict[str, bool] = {"skip_all": False} # Tracks if user said 'y'

    try:
        logging.info("Initializing WebDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("WebDriver initialized successfully.")

        # --- Process URLs ---
        for idx, url in enumerate(urls, start=1):
            print(Fore.GREEN + f"Processing ({idx}/{len(urls)}): {url}")
            # Pass the ssl_decision dictionary down
            metadata = extract_metadata(url, driver, ssl_decision=ssl_decision)
            if metadata:
                metadata_list.append(metadata)
            else:
                 metadata_list.append({"Page-URL": url, "IA error": "Critical extraction failure"})
                 logging.error(f"Critical failure processing {url}, adding basic error row.")


        # --- Define CSV Headers ---
        fieldnames = [
            "http-code", "http-type", "Page-URL", "page-slug", "Page-id", "Parent-ID",
            "Title", "Description", "Keywords",
            "Opengraph type", "Opengraph image", "Opengraph title", "Opengraph description",
            "Article H1", "Article Headings", "Article Links Internal", "Article Links External",
            "Article Images", "Article Images NoAlt",
            "content-count", "content-ratio",
            "Parent-URL", "IA error",
        ]

        # --- Write Results ---
        write_to_csv(output_path, metadata_list, fieldnames)
        print(Fore.CYAN + f"\nMetadata saved to {output_path}")

    except Exception as e:
        logging.critical(f"A critical error occurred in the main script execution: {e}", exc_info=True)
        print(Fore.RED + f"A critical error occurred. Check logs. Error: {e}")

    finally:
        # --- Cleanup ---
        if driver:
            try:
                driver.quit()
                logging.info("WebDriver quit successfully.")
            except Exception as e:
                logging.error(f"Error quitting WebDriver: {e}")
        print(Style.BRIGHT + Fore.CYAN + "Script finished.")


if __name__ == "__main__":
    main()