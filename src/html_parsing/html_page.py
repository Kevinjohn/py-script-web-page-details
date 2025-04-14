# src/html_parsing/html_page.py
import logging
from typing import Optional
from bs4 import BeautifulSoup

# ========================================
# Function: extract_body_class
# Description: Extracts the value of a specific class prefixed class from the body tag.
# ========================================
def extract_body_class(soup: BeautifulSoup, prefix: str, default: Optional[str] = None) -> Optional[str]:
    """ Extracts the value of a specific class prefixed class from the body tag. """
    if not prefix or not isinstance(prefix, str): return default # Robustness
    try:
        body = soup.body
        if body and body.has_attr("class"):
            # body['class'] can return a list of strings
            classes = body.get("class", [])
            if isinstance(classes, list): # Ensure it's a list
                 for cls in classes:
                     # Ensure cls is string before startswith check
                     if isinstance(cls, str) and cls.startswith(prefix):
                         value = cls.replace(prefix, "").strip()
                         logging.debug(f"Found body class with prefix '{prefix}': {value}")
                         return value
            else:
                 logging.warning(f"Body class attribute was not a list: {classes}")

        logging.debug(f"Body class with prefix '{prefix}' not found.")
        return default
    except Exception as e:
        logging.warning(f"Error extracting body class with prefix '{prefix}': {e}", exc_info=True)
        return default