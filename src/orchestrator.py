# src/orchestrator.py
import logging
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver

# --- Updated Imports (Keep no_semantic_base_html_tag) ---
from .web_utils import fetch_http_status_and_type, fetch_and_parse_html
from .url_utils import extract_page_slug
# Import both functions from html_scope again
from .html_parsing.html_scope import find_content_scope, no_semantic_base_html_tag
from .html_parsing.html_metadata import extract_meta_content, extract_meta_title
from .html_parsing.html_content import (
    extract_h1, count_tags, count_links, count_images_no_alt,
    extract_placeholder_data
)
from .html_parsing.html_page import extract_body_class
# --- End Updated Imports ---

from .config_loader import DEFAULT_SETTINGS

# --- Orchestration Function ---

# ========================================
# Function: extract_metadata (Updated Scope Logic Again)
# ========================================
def extract_metadata(
    url: str,
    driver: WebDriver,
    ssl_decision: Dict[str, bool],
    settings: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the extraction of various metadata elements for a given URL.
    Determines the main content scope dynamically based on settings.
    Falls back to using body scope if no primary semantic scope is found,
    logging this fact via no_semantic_base_html_tag.

    Args:
        url: The URL to analyze.
        driver: The Selenium WebDriver instance.
        ssl_decision: Dictionary tracking the user's decision on skipping SSL.
        settings: The loaded configuration settings dictionary.

    Returns:
        A dictionary containing the extracted metadata.
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

    try:
        # 1. Fetch HTTP status and type
        http_code, http_type = fetch_http_status_and_type(url, ssl_decision=ssl_decision)
        result_data["http-code"] = http_code
        result_data["http-type"] = http_type # Will store None or error message if fetch fails
        result_data["page-slug"] = extract_page_slug(url) # Can run even if fetch fails

        # 2. Handle non-HTML or fetch error cases (return early after recording code/type)
        if http_code is None:
             result_data["IA error"] = str(http_type or "HEAD request failed") # Store error msg
             logging.warning(f"Skipping Selenium fetch for {url} due to HEAD request failure ({result_data['IA error']}).")
             return result_data
        if http_type and "html" not in str(http_type).lower():
            result_data["IA error"] = f"Non-HTML content ({http_type})"
            logging.warning(f"Skipping detailed parsing for {url}. Status: {http_code}, Type: {http_type}")
            return result_data # Return results with code/type but no parsed data

        # 3. Fetch and parse HTML
        wait_seconds = settings.get("wait_after_load_seconds", DEFAULT_SETTINGS["wait_after_load_seconds"])
        logging.debug(f"Fetching HTML for {url} (wait_after_load={wait_seconds}s)...")
        soup = fetch_and_parse_html(url, driver, wait_after_load=wait_seconds) # Pass wait time
        if not soup:
            result_data["IA error"] = "Failed to fetch/parse HTML (Selenium)"
            logging.error(f"Failed to fetch or parse HTML for {url}.")
            # Return results with code/type but failed parse status
            return result_data

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


        # --- 5. Find content scope AND Perform Scoped Analysis (Updated Logic) ---
        scope_priority = settings.get("scope_selectors_priority", DEFAULT_SETTINGS["scope_selectors_priority"])
        logging.debug(f"Finding primary content scope using priority: {scope_priority}")
        scope_selector = find_content_scope(soup, priority_list=scope_priority) # Attempt to find scope

        if scope_selector is None:
            # *** Call handler function to get fallback selector ("body") ***
            # This logs the warning internally now
            scope_selector = no_semantic_base_html_tag(url) # Returns "body"
            # *** Set IA error message indicating fallback ***
            error_msg = "No primary semantic tag found; analysis performed on <body>"
            if result_data["IA error"]: # Append if error already exists
                result_data["IA error"] += f"; {error_msg}"
            else:
                result_data["IA error"] = error_msg
            logging.info(f"Using fallback scope '{scope_selector}' for detailed content analysis.") # Log using the returned "body"
        else:
            logging.info(f"Using scope '{scope_selector}' for detailed content analysis.")

        # --- Always perform scoped analysis using the determined scope_selector ('main', 'article', or 'body') ---
        # Note: Passing scope_selector="body" explicitly works the same as passing scope_selector=None
        # for the underlying parser functions, as they default to body if selector is None or not found.
        logging.debug(f"Performing scoped analysis using selector: {scope_selector}")
        result_data["Article H1"] = extract_h1(soup, scope_selector=scope_selector)
        result_data["Article Headings"] = count_tags(soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector=scope_selector)
        result_data["Article Links Internal"] = count_links(soup, url, internal=True, scope_selector=scope_selector)
        result_data["Article Links External"] = count_links(soup, url, internal=False, scope_selector=scope_selector)
        result_data["Article Images"] = count_tags(soup, ["img"], scope_selector=scope_selector)
        result_data["Article Images NoAlt"] = count_images_no_alt(soup, scope_selector=scope_selector)

        logging.info(f"Successfully extracted metadata for: {url}")
        return result_data

    except Exception as e:
        logging.exception(f"Critical unexpected error during metadata extraction for {url}: {e}")
        # Error handling: ensure Page-URL and IA error are set
        error_result = {"Page-URL": url, "IA error": f"Critical Orchestrator Error ({type(e).__name__})"}
        # Merge with any partially collected data, prioritizing critical error message
        for key in result_data:
             if key not in error_result:
                 error_result[key] = result_data.get(key, None) # Use .get for safety
        error_result["IA error"] = f"Critical Orchestrator Error ({type(e).__name__})"
        return error_result