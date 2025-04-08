# src/orchestrator.py
import logging
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver

# --- Updated Imports ---
from .web_utils import fetch_http_status_and_type, fetch_and_parse_html
from .url_utils import extract_page_slug # Moved here
from .html_parsing.html_scope import find_content_scope, no_semantic_base_html_tag # New location
from .html_parsing.html_metadata import extract_meta_content, extract_meta_title # New location
from .html_parsing.html_content import ( # New location
    extract_h1, count_tags, count_links, count_images_no_alt,
    extract_placeholder_data
)
from .html_parsing.html_page import extract_body_class # New location
# --- End Updated Imports ---

from .config_loader import DEFAULT_SETTINGS

# --- Orchestration Function ---

# ========================================
# Function: extract_metadata (Signature unchanged from previous step)
# ========================================
def extract_metadata(
    url: str,
    driver: WebDriver,
    ssl_decision: Dict[str, bool],
    settings: Dict[str, Any] # Pass loaded settings dictionary
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the extraction of various metadata elements for a given URL.
    Determines the main content scope dynamically based on settings.
    Includes optional wait after page load based on settings.

    Args:
        url: The URL to analyze.
        driver: The Selenium WebDriver instance.
        ssl_decision: Dictionary tracking the user's decision on skipping SSL.
        settings: The loaded configuration settings dictionary.

    Returns:
        A dictionary containing the extracted metadata, or a basic dictionary
        with an error flag if a critical error occurs. Returns None only on
        very unexpected internal errors.
    """
    logging.info(f"Starting metadata extraction for: {url}")
    # --- Initialization (remains the same) ---
    result_data = {
        "http-code": None, "http-type": "Unknown", "Page-URL": url,
        "page-slug": "", "Page-id": "", "Parent-ID": "0",
        "Title": "", "Description": "", "Keywords": "",
        "Opengraph type": "", "Opengraph image": "", "Opengraph title": "", "Opengraph description": "",
        "Article H1": "", "Article Headings": 0,
        "Article Links Internal": 0, "Article Links External": 0,
        "Article Images": 0, "Article Images NoAlt": 0,
        "content-count": None, "content-ratio": None,
        "Parent-URL": "", "IA error": "",
    }

    try:
        # 1. Fetch HTTP status and type (remains the same)
        http_code, http_type = fetch_http_status_and_type(url, ssl_decision=ssl_decision)
        result_data["http-code"] = http_code
        result_data["http-type"] = http_type
        # Uses function from url_utils now
        result_data["page-slug"] = extract_page_slug(url)

        # 2. Handle non-HTML or error cases (remains the same)
        if http_code is None:
             result_data["IA error"] = http_type or "HEAD request failed"
             logging.warning(f"Skipping Selenium fetch for {url}...")
             return result_data
        if http_type and "html" not in str(http_type).lower():
            result_data["IA error"] = f"Non-HTML content ({http_type})"
            logging.warning(f"Skipping detailed parsing for {url}...")
            return result_data

        # 3. Fetch and parse HTML (remains the same, uses wait_seconds from settings)
        wait_seconds = settings.get("wait_after_load_seconds", DEFAULT_SETTINGS["wait_after_load_seconds"])
        logging.debug(f"Fetching HTML for {url} (wait_after_load={wait_seconds}s)...")
        soup = fetch_and_parse_html(url, driver, wait_after_load=wait_seconds)
        if not soup:
            result_data["IA error"] = "Failed to fetch/parse HTML (Selenium)"
            logging.error(f"Failed to fetch or parse HTML for {url}.")
            return result_data

        # 4. Extract non-scoped data (uses functions from new locations)
        logging.debug("Extracting non-scoped details...")
        result_data["Title"] = extract_meta_title(soup) # from html_metadata
        result_data["Description"] = extract_meta_content(soup, "description") # from html_metadata
        result_data["Keywords"] = extract_meta_content(soup, "keywords") # from html_metadata
        result_data["Opengraph type"] = extract_meta_content(soup, "og:type") # from html_metadata
        result_data["Opengraph image"] = extract_meta_content(soup, "og:image") # from html_metadata
        result_data["Opengraph title"] = extract_meta_content(soup, "og:title") # from html_metadata
        result_data["Opengraph description"] = extract_meta_content(soup, "og:description") # from html_metadata
        result_data["Page-id"] = extract_body_class(soup, "page-id-", default="") # from html_page
        result_data["Parent-ID"] = extract_body_class(soup, "parent-pageid-", default="0") # from html_page
        result_data["content-count"] = extract_placeholder_data(soup, "content-count") # from html_content
        result_data["content-ratio"] = extract_placeholder_data(soup, "content-ratio") # from html_content

        # 5. Find content scope and extract scoped data (uses functions from new locations)
        scope_priority = settings.get("scope_selectors_priority", DEFAULT_SETTINGS["scope_selectors_priority"])
        logging.debug(f"Finding primary content scope using priority: {scope_priority}")
        scope_selector = find_content_scope(soup, priority_list=scope_priority) # from html_scope

        if scope_selector:
            logging.info(f"Using scope '{scope_selector}' for detailed content analysis.")
            # Calls use functions from html_content
            result_data["Article H1"] = extract_h1(soup, scope_selector=scope_selector)
            result_data["Article Headings"] = count_tags(soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector=scope_selector)
            result_data["Article Links Internal"] = count_links(soup, url, internal=True, scope_selector=scope_selector)
            result_data["Article Links External"] = count_links(soup, url, internal=False, scope_selector=scope_selector)
            result_data["Article Images"] = count_tags(soup, ["img"], scope_selector=scope_selector)
            result_data["Article Images NoAlt"] = count_images_no_alt(soup, scope_selector=scope_selector)
        else:
            logging.warning(f"No primary content scope found for {url}. Calling handler.")
            scope_fallback_data = no_semantic_base_html_tag(url) # from html_scope
            result_data.update(scope_fallback_data)
            # Append error message if another one already exists
            if result_data["IA error"] and result_data["IA error"] != scope_fallback_data.get("IA error"):
                 result_data["IA error"] += f"; {scope_fallback_data.get('IA error', '')}"
            elif not result_data["IA error"]:
                 result_data["IA error"] = scope_fallback_data.get("IA error", "")

        logging.info(f"Successfully extracted metadata for: {url}")
        return result_data

    except Exception as e:
        logging.exception(f"Critical unexpected error during metadata extraction for {url}: {e}")
        # Error handling remains the same
        error_result = {"Page-URL": url, "IA error": f"Critical Orchestrator Error ({type(e).__name__})"}
        for key in result_data:
             if key not in error_result:
                 error_result[key] = result_data[key]
        error_result["IA error"] = f"Critical Orchestrator Error ({type(e).__name__})"
        return error_result