# src/html_parsing/html_metadata.py
import logging
from typing import Optional
from bs4 import BeautifulSoup

# ========================================
# Function: extract_meta_content
# Description: Extract content from a specific meta tag (name or property).
# ========================================
def extract_meta_content(soup: BeautifulSoup, meta_name: str) -> str:
    """ Extract content from a specific meta tag (name or property). """
    content = ""
    if not meta_name or not isinstance(meta_name, str): return content # Basic robustness check
    try:
        # Search by property first (commonly used for OpenGraph)
        tag = soup.find("meta", attrs={"property": meta_name})
        # If not found by property, search by name
        if not tag:
            tag = soup.find("meta", attrs={"name": meta_name})

        if tag and tag.has_attr("content"):
             # Ensure content is treated as string, handle potential None explicitly
             tag_content = tag.get("content")
             content = str(tag_content).strip() if tag_content is not None else ""
             logging.debug(f"Found meta '{meta_name}': '{content[:50]}...'")
        else:
             logging.debug(f"Meta tag '{meta_name}' not found or has no content attribute.")
    except Exception as e:
        logging.warning(f"Error extracting meta content for '{meta_name}': {e}", exc_info=True)
    return content

# ========================================
# Function: extract_meta_title
# Description: Extract the text content from the <title> tag.
# ========================================
def extract_meta_title(soup: BeautifulSoup) -> str:
    """ Extract the text content from the <title> tag. """
    title = ""
    try:
        title_tag = soup.title
        if title_tag and title_tag.string:
            # Ensure string content is handled safely and stripped
            title = str(title_tag.string).strip()
            logging.debug(f"Found title: '{title}'")
        else:
            logging.debug("Title tag not found or is empty.")
    except Exception as e:
        logging.warning(f"Error extracting meta title: {e}", exc_info=True)
    return title