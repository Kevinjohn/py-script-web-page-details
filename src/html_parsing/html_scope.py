# src/html_parsing/html_scope.py
import logging
from typing import Optional, List, Any, Dict
from bs4 import BeautifulSoup

# ========================================
# Function: find_content_scope
# Description: Finds the best semantic main content scope selector based on priority list.
# ========================================
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
# Function: no_semantic_base_html_tag (Placeholder)
# Description: Handles cases where no primary content scope is identified.
# ========================================
def no_semantic_base_html_tag(url: str) -> Dict[str, Any]:
    """
    Placeholder function for when no main semantic tag (based on priority list)
    is found. Returns default/empty values for scoped metrics.

    Args:
        url: The URL of the page being processed.

    Returns:
        A dictionary with default values for scope-dependent fields and an error message.
    """
    error_msg = "No primary semantic content tag found matching priority list"
    logging.warning(f"{error_msg} for URL: {url}")
    # Return default values for the fields normally extracted from a scope
    return {
        "Article H1": "",
        "Article Headings": 0,
        "Article Links Internal": 0,
        "Article Links External": 0,
        "Article Images": 0,
        "Article Images NoAlt": 0,
        "IA error": error_msg, # Set specific error
        # Add other scope-dependent fields here if any are added later
    }