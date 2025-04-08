# src/orchestrator.py
import logging
from typing import Optional, Dict, Any, List # Added List
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver

# Import specific functions from other modules
from .web_utils import fetch_http_status_and_type, fetch_and_parse_html
from .html_parser import (
    find_content_scope, no_semantic_base_html_tag,
    extract_meta_content, extract_meta_title, extract_h1, count_tags,
    count_links, count_images_no_alt, extract_body_class, extract_page_slug,
    extract_placeholder_data
)
# Import DEFAULT_SETTINGS to get default values if not in loaded settings
from .config_loader import DEFAULT_SETTINGS

# --- Orchestration Function ---

# ========================================
# Function: extract_metadata (Updated)
# Description: Orchestrates the extraction of various metadata elements for a given URL.
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
    result_data = {
        "http-code": None, "http-type": "Unknown", "Page-URL": url,
        "page-slug": "", "Page-id": "", "Parent-ID": "0",
        "Title": "", "Description": "", "Keywords": "",
        "Opengraph type": "", "Opengraph image": "", "Opengraph title": "", "Opengraph description": "",
        "Article H1": "", "Article Headings": 0,
        "Article Links Internal": 0, "Article Links External": 0,
        "Article Images": 0, "Article Images NoAlt": 0,
        "content-count": None, "content-ratio": None,
        "Parent-URL": "",
        "IA error": "",
    }

    try:
        # 1. Fetch HTTP status and type (using defaults from web_utils if not overridden)
        http_code, http_type = fetch_http_status_and_type(url, ssl_decision=ssl_decision)
        result_data["http-code"] = http_code
        result_data["http-type"] = http_type
        result_data["page-slug"] = extract_page_slug(url)

        # 2. Handle non-HTML or error cases from HEAD request
        if http_code is None:
             result_data["IA error"] = http_type or "HEAD request failed"
             logging.warning(f"Skipping Selenium fetch for {url} due to HEAD request failure ({result_data['IA error']}).")
             return result_data
        if http_type and "html" not in str(http_type).lower():
            result_data["IA error"] = f"Non-HTML content ({http_type})"
            logging.warning(f"Skipping detailed parsing for {url}. Status: {http_code}, Type: {http_type}")
            return result_data

        # 3. Fetch and parse HTML using Selenium
        # --- Get wait time from settings ---
        wait_seconds = settings.get("wait_after_load_seconds", DEFAULT_SETTINGS["wait_after_load_seconds"])
        logging.debug(f"Proceeding to fetch full HTML for {url} with Selenium (wait_after_load={wait_seconds}s)...")
        soup = fetch_and_parse_html(url, driver, wait_after_load=wait_seconds) # Pass wait time
        if not soup:
            result_data["IA error"] = "Failed to fetch/parse HTML (Selenium)"
            logging.error(f"Failed to fetch or parse HTML for {url} with Selenium.")
            return result_data

        # 4. Extract non-scoped data
        # ... (non-scoped extraction logic remains the same) ...
        logging.debug(f"HTML parsed for {url}. Extracting non-scoped details...")
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


        # --- 5. Find content scope and extract scoped data ---
        # --- Get scope priority list from settings ---
        scope_priority = settings.get("scope_selectors_priority", DEFAULT_SETTINGS["scope_selectors_priority"])
        logging.debug(f"Finding primary content scope for {url} using priority: {scope_priority}")
        scope_selector = find_content_scope(soup, priority_list=scope_priority) # Pass priority list

        if scope_selector:
            logging.info(f"Using scope '{scope_selector}' for detailed content analysis.")
            result_data["Article H1"] = extract_h1(soup, scope_selector=scope_selector)
            result_data["Article Headings"] = count_tags(soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector=scope_selector)
            result_data["Article Links Internal"] = count_links(soup, url, internal=True, scope_selector=scope_selector)
            result_data["Article Links External"] = count_links(soup, url, internal=False, scope_selector=scope_selector)
            result_data["Article Images"] = count_tags(soup, ["img"], scope_selector=scope_selector)
            result_data["Article Images NoAlt"] = count_images_no_alt(soup, scope_selector=scope_selector)
        else:
            logging.warning(f"No primary content scope found for {url}. Calling handler.")
            scope_fallback_data = no_semantic_base_html_tag(url)
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
        # Ensure essential info is present even on critical failure
        error_result = {"Page-URL": url, "IA error": f"Critical Orchestrator Error ({type(e).__name__})"}
        # Merge with any partially collected data, prioritizing the critical error message
        for key in result_data:
             if key not in error_result:
                 error_result[key] = result_data[key]
        error_result["IA error"] = f"Critical Orchestrator Error ({type(e).__name__})" # Overwrite/set error
        return error_result