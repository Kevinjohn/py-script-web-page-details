# src/url_utils.py
import logging
from urllib.parse import urlparse, ParseResult
from typing import Optional

# ========================================
# Function: extract_page_slug (Updated Logic)
# Description: Extract the page slug (last part of the path) from the URL.
# ========================================
def extract_page_slug(url: str) -> str:
    """ Extract the page slug (last part of the path) from the URL. """
    # Initial checks for invalid input types or empty strings
    if not isinstance(url, str) or not url.strip():
        return "unknown"

    try:
        parsed: ParseResult = urlparse(url)
        path: Optional[str] = parsed.path
        scheme: str = parsed.scheme
        netloc: Optional[str] = parsed.netloc

        # If it parsed only as a path (no scheme/domain), treat as unknown
        if path and not scheme and not netloc:
            # Allow file scheme even without netloc
            if scheme == 'file':
                 pass # Let file path logic handle it below
            else:
                 logging.debug(f"Input '{url}' parsed only as path, returning 'unknown' slug.")
                 return "unknown"

        # Handle file scheme specifically if needed (though urlparse handles path correctly)
        # Currently covered by path logic below

        # Existing logic for path processing
        if not path or path == "/":
            # Consider root with query/fragment also homepage slug
            if not parsed.query and not parsed.fragment:
                 return "homepage"
            else:
                 # If there's query/fragment but no path, still 'homepage'
                 if path == "/": return "homepage"
                 # If path is empty but query/fragment exists, urlparse sets path='', so 'homepage'
                 # This case seems correctly handled by 'not path' above returning homepage

        # Ensure path is treated as string before stripping/splitting
        # Remove trailing slashes, then split by slash, take last part
        slug = str(path).rstrip("/").split("/")[-1]
        # If slug is empty after stripping/splitting (e.g., path was '/folder/'), return 'index'
        return slug if slug else "index"

    except Exception as e:
        logging.warning(f"Error extracting page slug from {url}: {e}", exc_info=True)
        return "unknown"