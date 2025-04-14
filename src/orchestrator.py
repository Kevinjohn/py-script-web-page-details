# src/orchestrator.py
import logging
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver

# Imports remain the same
from .web_utils import fetch_http_status_and_type, fetch_and_parse_html
from .url_utils import extract_page_slug
from .html_parsing.html_scope import find_content_scope, no_semantic_base_html_tag
from .html_parsing.html_metadata import extract_meta_content, extract_meta_title
from .html_parsing.html_content import (
    extract_h1, count_tags, count_links, count_images_no_alt,
    extract_placeholder_data
)
from .html_parsing.html_page import extract_body_class
from .config_loader import DEFAULT_SETTINGS

# --- Orchestration Function ---

# ========================================
# Function: extract_metadata (Updated Logic for HTTP Errors)
# ========================================
def extract_metadata(
    url: str,
    driver: WebDriver,
    ssl_decision: Dict[str, bool],
    settings: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates extraction. Records HTTP status code (incl. errors) and type.
    Only proceeds to full parsing for successful HTML responses.
    Falls back to body scope if no primary semantic scope is found.
    """
    logging.info(f"Starting metadata extraction for: {url}")
    result_data = { # Initialize all fields
        "http-code": None, "http-type": "Unknown", "Page-URL": url, "page-slug": "",
        "Page-id": "", "Parent-ID": "0", "Title": "", "Description": "", "Keywords": "",
        "Opengraph type": "", "Opengraph image": "", "Opengraph title": "", "Opengraph description": "",
        "Article H1": "", "Article Headings": 0, "Article Links Internal": 0,
        "Article Links External": 0, "Article Images": 0, "Article Images NoAlt": 0,
        "content-count": None, "content-ratio": None, "Parent-URL": "", "IA error": "",
    }

    proceed_to_parse = False # Flag to control execution flow

    try:
        # 1. Fetch HTTP status and type
        http_code, http_type = fetch_http_status_and_type(url, ssl_decision=ssl_decision)
        result_data["http-code"] = http_code # Record code (could be 200, 404, 500, or None)
        result_data["http-type"] = http_type # Record type or error message

        # 2. Determine if we should proceed to Selenium/Parsing
        if http_code is None:
             # Fundamental fetch error (SSL declined, DNS, timeout before response etc.)
             result_data["IA error"] = str(http_type or "HEAD request failed") # Store error msg
             logging.warning(f"Skipping Selenium fetch: Fundamental HEAD request failure ({result_data['IA error']}).")
             proceed_to_parse = False
        # Check if http_type indicates an error string was returned by fetch_http_status_and_type
        elif isinstance(http_type, str) and ( "Error" in http_type):
             # Fetch completed after retries but ended in error (e.g., HTTPError 404/500, final SSL error)
             # We have the http_code (e.g., 404, or None if non-HTTP error) but shouldn't parse.
             result_data["IA error"] = http_type # Record the specific error type string
             logging.warning(f"Skipping Selenium fetch: HEAD request completed with error code {http_code} ({http_type}).")
             proceed_to_parse = False
        elif http_type and "html" not in str(http_type).lower():
             # Successful fetch but non-HTML content
             result_data["IA error"] = f"Non-HTML content ({http_type})"
             logging.warning(f"Skipping detailed parsing: Non-HTML content. Status: {http_code}, Type: {http_type}")
             proceed_to_parse = False
        elif isinstance(http_code, int) and http_code >= 200 and http_code < 300:
             # Successful 2xx response, looks like HTML -> Proceed
             logging.debug(f"HEAD request successful for HTML content ({http_code}). Proceeding to parse.")
             proceed_to_parse = True
        else:
             # Catch-all for other unexpected codes/types from HEAD (e.g., maybe redirects weren't followed properly?)
             result_data["IA error"] = f"Unexpected HEAD result (Code: {http_code}, Type: {http_type})"
             logging.warning(f"Skipping Selenium fetch due to unexpected HEAD result: {result_data['IA error']}")
             proceed_to_parse = False

        # --- Set page slug regardless of parsing ---
        result_data["page-slug"] = extract_page_slug(url)

        # --- Proceed to Parsing only if conditions met ---
        if proceed_to_parse:
            # 3. Fetch and parse HTML using Selenium
            wait_seconds = settings.get("wait_after_load_seconds", DEFAULT_SETTINGS["wait_after_load_seconds"])
            logging.debug(f"Fetching full HTML (wait_after_load={wait_seconds}s)...")
            soup = fetch_and_parse_html(url, driver, wait_after_load=wait_seconds) # Pass wait time

            if not soup:
                # Update IA error if fetching/parsing failed
                err_msg = "Failed to fetch/parse HTML (Selenium)"
                if result_data["IA error"]: result_data["IA error"] += f"; {err_msg}"
                else: result_data["IA error"] = err_msg
                logging.error(f"Failed to fetch or parse HTML for {url}.")
                # Return results recorded so far (incl http code/type) + parse error
                return result_data
            else:
                # 4. Extract non-scoped data
                logging.debug("Extracting non-scoped details...")
                result_data["Title"] = extract_meta_title(soup)
                result_data["Description"] = extract_meta_content(soup, "description")
                result_data["Keywords"] = extract_meta_content(soup, "keywords")
                result_data["Opengraph type"] = extract_meta_content(soup, "og:type")
                result_data["Opengraph image"] = extract_meta_content(soup, "og:image")
                result_data["Opengraph title"] = extract_meta_content(soup, "og:title")
                result_data["Opengraph description"] = extract_meta_content(soup, "og:description")
                result_data["Page-id"] = extract_body_class(soup, "page-id-", default="")
                result_data["Parent-ID"] = extract_body_class(soup, "parent-pageid-", default="0")
                result_data["content-count"] = extract_placeholder_data(soup, "content-count")
                result_data["content-ratio"] = extract_placeholder_data(soup, "content-ratio")

                # 5. Find content scope and extract scoped data
                scope_priority = settings.get("scope_selectors_priority", DEFAULT_SETTINGS["scope_selectors_priority"])
                logging.debug(f"Finding primary content scope using priority: {scope_priority}")
                scope_selector = find_content_scope(soup, priority_list=scope_priority) # Attempt to find scope

                if scope_selector is None:
                    scope_selector = no_semantic_base_html_tag(url) # Returns "body"
                    error_msg = "No primary semantic tag found; analysis performed on <body>"
                    if result_data["IA error"]: result_data["IA error"] += f"; {error_msg}"
                    else: result_data["IA error"] = error_msg
                    logging.info(f"Using fallback scope '{scope_selector}' for detailed content analysis.")
                else:
                    logging.info(f"Using scope '{scope_selector}' for detailed content analysis.")

                # --- Always perform scoped analysis using the determined scope_selector ('main', 'article', or 'body') ---
                logging.debug(f"Performing scoped analysis using selector: {scope_selector}")
                result_data["Article H1"] = extract_h1(soup, scope_selector=scope_selector)
                result_data["Article Headings"] = count_tags(soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector=scope_selector)
                result_data["Article Links Internal"] = count_links(soup, url, internal=True, scope_selector=scope_selector)
                result_data["Article Links External"] = count_links(soup, url, internal=False, scope_selector=scope_selector)
                result_data["Article Images"] = count_tags(soup, ["img"], scope_selector=scope_selector)
                result_data["Article Images NoAlt"] = count_images_no_alt(soup, scope_selector=scope_selector)
                # --- End of successful parsing ---

        # --- If not proceed_to_parse, we just fall through ---
        logging.info(f"Finished metadata extraction attempt for: {url}")
        return result_data # Return dictionary with whatever was collected

    except Exception as e:
        logging.exception(f"Critical unexpected error during metadata extraction for {url}: {e}")
        # Error handling: ensure Page-URL and IA error are set
        error_result = {"Page-URL": url, "IA error": f"Critical Orchestrator Error ({type(e).__name__})"}
        # Merge with any partially collected data, prioritizing critical error message
        for key in result_data:
             if key not in error_result:
                 error_result[key] = result_data.get(key, None) # Use .get for safety
        # Preserve http code/type if they were set before the critical error
        error_result["http-code"] = result_data.get("http-code")
        error_result["http-type"] = result_data.get("http-type")
        error_result["IA error"] = f"Critical Orchestrator Error ({type(e).__name__})" # Ensure this is the final error
        return error_result