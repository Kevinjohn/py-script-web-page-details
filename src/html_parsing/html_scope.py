# src/html_parsing/html_scope.py
import logging
from typing import Optional, List, Any, Dict # Keep Dict for now, change later if function fully changes
from bs4 import BeautifulSoup

# ========================================
# Function: find_content_scope
# Description: Finds the best semantic main content scope selector based on priority list.
# ========================================
# (This function remains the same as the last correct version)
def find_content_scope(soup: BeautifulSoup, priority_list: List[str]) -> Optional[str]:
    """
    Finds the best CSS selector for the main content area based on a priority list.
    Handles special case for 'article' (must be unique).

    Args:
        soup: BeautifulSoup object of the page.
        priority_list: Ordered list of CSS selectors to check.

    Returns:
        A CSS selector string for the best scope found, or None if none match.
    """
    logging.debug(f"Finding content scope using priority: {priority_list}")
    if not isinstance(priority_list, list):
        logging.error("Invalid priority_list provided to find_content_scope. Must be a list.")
        return None # Return None if priority_list is invalid

    for selector in priority_list:
        if not isinstance(selector, str):
            logging.warning(f"Invalid selector type in priority list: {selector}. Skipping.")
            continue # Skip non-string selectors

        # Special handling for 'article' - must be unique on page
        if selector.lower() == "article":
            try:
                article_tags = soup.find_all("article")
                if len(article_tags) == 1:
                    logging.debug("Found single <article> tag matching priority list.")
                    return "article"
                elif len(article_tags) > 1:
                    logging.warning(f"Found {len(article_tags)} <article> tags. Skipping 'article' selector due to non-uniqueness.")
                    continue # Try next selector in priority list
                else:
                    # No articles found, continue to next selector
                    continue
            except Exception as e:
                 logging.warning(f"Error during 'article' tag check: {e}. Skipping.")
                 continue
        else:
            # For other selectors, find the first match
            try:
                 # Add try-except for robustness against invalid selectors from config
                 found_element = soup.select_one(selector)
                 if found_element:
                     logging.debug(f"Found element matching selector '{selector}' for content scope.")
                     return selector # Return the selector that matched
            except Exception as e:
                 # Catch potential exceptions from invalid CSS selectors in select_one
                 logging.warning(f"Error applying selector '{selector}' from priority list: {e}. Skipping.")
                 continue

    # None of the selectors in the priority list yielded a valid scope
    logging.debug(f"No suitable content scope found matching priority list.")
    return None

# ========================================
# Function: no_semantic_base_html_tag (Modified)
# Description: Logs warning and returns 'body' as the fallback scope selector.
# ========================================
def no_semantic_base_html_tag(url: str) -> str: # Changed return type hint
    """
    Logs a warning that no primary semantic tag was found and returns 'body'
    as the fallback scope selector.

    Args:
        url: The URL of the page being processed.

    Returns:
        The string "body" to be used as the CSS selector.
    """
    error_msg = "No primary semantic content tag found matching priority list"
    logging.warning(f"{error_msg}. Falling back to <body> scope for URL: {url}")
    # NOTE: We still return "body", but the IA error in orchestrator will reflect the *reason*
    return "body"