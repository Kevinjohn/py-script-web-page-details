# src/orchestrator.py
import logging
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from selenium.webdriver.remote.webdriver import WebDriver # More specific type hint

# Import specific functions from other modules using relative imports
from .web_utils import fetch_http_status_and_type, fetch_and_parse_html
from .html_parser import (
    extract_meta_content, extract_meta_title, extract_h1, count_tags,
    count_links, count_images_no_alt, extract_body_class, extract_page_slug,
    extract_placeholder_data
)

# --- Orchestration Function ---

# ========================================
# Function: extract_metadata
# Description: Orchestrates the extraction of various metadata elements for a given URL.
# ========================================
def extract_metadata(
    url: str,
    driver: WebDriver, # Use the more specific WebDriver type
    ssl_decision: Dict[str, bool] # Accept the decision state
) -> Optional[Dict[str, Any]]:
    """
    Orchestrates the extraction of various metadata elements for a given URL.

    Args:
        url: The URL to analyze.
        driver: The Selenium WebDriver instance.
        ssl_decision: Dictionary tracking the user's decision on skipping SSL.

    Returns:
        A dictionary containing the extracted metadata, or a basic dictionary
        with an error flag if a critical error occurs. Returns None only on
        very unexpected internal errors.
    """
    logging.info(f"Starting metadata extraction for: {url}")
    # Initialize all potential fields to ensure CSV consistency
    # Use empty strings or 0/None as appropriate defaults
    result_data = {
        "http-code": None, "http-type": "Unknown", "Page-URL": url,
        "page-slug": "", "Page-id": "", "Parent-ID": "0", # Assuming '0' is default parent
        "Title": "", "Description": "", "Keywords": "",
        "Opengraph type": "", "Opengraph image": "", "Opengraph title": "", "Opengraph description": "",
        "Article H1": "", "Article Headings": 0,
        "Article Links Internal": 0, "Article Links External": 0,
        "Article Images": 0, "Article Images NoAlt": 0,
        "content-count": None, "content-ratio": None,
        "Parent-URL": "", # Placeholder, seems unused currently
        "IA error": "", # Information Architecture / Internal Analysis error
    }

    try:
        # 1. Fetch HTTP status and type first
        http_code, http_type = fetch_http_status_and_type(url, ssl_decision=ssl_decision)
        result_data["http-code"] = http_code
        result_data["http-type"] = http_type
        result_data["page-slug"] = extract_page_slug(url) # Can be extracted even if HEAD fails

        # 2. Handle non-HTML or error cases from HEAD request
        if http_code is None:
            # fetch_http_status_and_type already logged the specific error
             result_data["IA error"] = http_type or "HEAD request failed" # Use error message from fetch
             logging.warning(f"Skipping Selenium fetch for {url} due to HEAD request failure ({result_data['IA error']}).")
             return result_data # Return basic info with error

        if http_type and "html" not in str(http_type).lower():
            logging.warning(f"Skipping detailed parsing for {url}. Status: {http_code}, Type: {http_type}")
            result_data["IA error"] = f"Non-HTML content ({http_type})"
            return result_data # Return basic info as it's not HTML

        # 3. Fetch and parse HTML using Selenium (only if HEAD was okay and type is HTML)
        logging.debug(f"Proceeding to fetch full HTML for {url} with Selenium...")
        soup = fetch_and_parse_html(url, driver)
        if not soup:
            logging.error(f"Failed to fetch or parse HTML for {url} with Selenium. Cannot extract details.")
            result_data["IA error"] = "Failed to fetch/parse HTML (Selenium)"
            return result_data # Return basic info with error

        # 4. Extract detailed data from BeautifulSoup object
        logging.debug(f"HTML parsed for {url}. Extracting details...")
        article_scope = "article" # Define scope selector once

        # Meta Tags
        result_data["Title"] = extract_meta_title(soup)
        result_data["Description"] = extract_meta_content(soup, "description")
        result_data["Keywords"] = extract_meta_content(soup, "keywords")
        result_data["Opengraph type"] = extract_meta_content(soup, "og:type")
        result_data["Opengraph image"] = extract_meta_content(soup, "og:image")
        result_data["Opengraph title"] = extract_meta_content(soup, "og:title") # Often more specific than <title>
        result_data["Opengraph description"] = extract_meta_content(soup, "og:description") # Often more specific than meta description

        # Article Scope Analysis (using the defined scope)
        result_data["Article H1"] = extract_h1(soup, scope_selector=article_scope)
        result_data["Article Headings"] = count_tags(soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector=article_scope)
        result_data["Article Links Internal"] = count_links(soup, url, internal=True, scope_selector=article_scope)
        result_data["Article Links External"] = count_links(soup, url, internal=False, scope_selector=article_scope)
        result_data["Article Images"] = count_tags(soup, ["img"], scope_selector=article_scope)
        result_data["Article Images NoAlt"] = count_images_no_alt(soup, scope_selector=article_scope)

        # Other page data
        result_data["Page-id"] = extract_body_class(soup, "page-id-", default="") # Default to empty string
        result_data["Parent-ID"] = extract_body_class(soup, "parent-pageid-", default="0") # Keep '0' default

        # Placeholder datactions
        result_data["content-count"] = extract_placeholder_data(soup, "content-count")
        result_data["content-ratio"] = extract_placeholder_data(soup, "content-ratio")

        logging.info(f"Successfully extracted metadata for: {url}")
        return result_data

    except Exception as e:
        logging.exception(f"Critical unexpected error during metadata extraction orchestrator for {url}: {e}")
        # Fill basic info if possible, ensure error is marked
        error_result = {**result_data, "IA error": f"Critical Orchestrator Error ({type(e).__name__})"}
        return error_result # Return data with error flag