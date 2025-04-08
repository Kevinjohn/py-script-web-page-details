# src/url_utils.py
import logging
from urllib.parse import urlparse, ParseResult
from typing import Optional

# ========================================
# Function: extract_page_slug
# Description: Extract the page slug (last part of the path) from the URL.
# ========================================
def extract_page_slug(url: str) -> str:
    """ Extract the page slug (last part of the path) from the URL. """
    if not isinstance(url, str): return "unknown" # Robustness
    try:
        path = urlparse(url).path
        if not path or path == "/":
            return "homepage"
        # Ensure path is treated as string before stripping/splitting
        slug = str(path).rstrip("/").split("/")[-1]
        return slug if slug else "index" # Return 'index' if slug is empty (e.g., from '/folder/')
    except Exception as e:
        logging.warning(f"Error extracting page slug from {url}: {e}", exc_info=True)
        return "unknown"