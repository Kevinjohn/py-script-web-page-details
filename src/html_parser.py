# src/html_parser.py
import logging
from urllib.parse import urlparse
# Make sure typing includes Dict for the new function's return type
from typing import Optional, List, Any, Dict
from bs4 import BeautifulSoup, Tag # Import Tag for type hinting if needed

# --- NEW Function to Find Content Scope ---

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
    for selector in priority_list:
        # Special handling for 'article' - must be unique on page
        if selector.lower() == "article":
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
        else:
            # For other selectors, find the first match
            # Note: select_one implicitly handles cases where multiple might match
            found_element = soup.select_one(selector)
            if found_element:
                logging.debug(f"Found element matching selector '{selector}' for content scope.")
                return selector # Return the selector that matched

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


# --- Existing HTML Parsing and Data Extraction Functions ---
# (These functions remain largely the same, still accepting scope_selector)

# ========================================
# Function: extract_meta_content
# Description: Extract content from a specific meta tag (name or property).
# ========================================
def extract_meta_content(soup: BeautifulSoup, meta_name: str) -> str:
    """
    Extract content from a specific meta tag (name or property).

    Args:
        soup: BeautifulSoup object of the page.
        meta_name: The 'name' or 'property' attribute value of the meta tag.

    Returns:
        The content of the meta tag, or an empty string if not found or on error.
    """
    content = ""
    try:
        tag = soup.find("meta", attrs={"property": meta_name}) or \
              soup.find("meta", attrs={"name": meta_name})
        if tag and tag.has_attr("content"):
             content = tag["content"].strip()
             logging.debug(f"Found meta '{meta_name}': '{content[:50]}...'")
        else:
             logging.debug(f"Meta tag '{meta_name}' not found or has no content.")
    except Exception as e:
        logging.warning(f"Error extracting meta content for '{meta_name}': {e}")
    return content

# ========================================
# Function: extract_meta_title
# Description: Extract the text content from the <title> tag.
# ========================================
def extract_meta_title(soup: BeautifulSoup) -> str:
    """
    Extract the text content from the <title> tag.

    Args:
        soup: BeautifulSoup object of the page.

    Returns:
        The title text, or an empty string if not found or on error.
    """
    title = ""
    try:
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            logging.debug(f"Found title: '{title}'")
        else:
            logging.debug("Title tag not found or is empty.")
    except Exception as e:
        logging.warning(f"Error extracting meta title: {e}")
    return title

# ========================================
# Function: extract_h1
# Description: Extract the text of the first H1 tag, optionally within a specific scope.
# ========================================
# Function signature remains the same (takes scope_selector string)
def extract_h1(soup: BeautifulSoup, scope_selector: Optional[str] = None) -> str:
    """
    Extract the text of the first H1 tag, optionally within a specific scope.

    Args:
        soup: BeautifulSoup object of the page.
        scope_selector: CSS selector for the scope (e.g., 'article', 'main').
                        If None or empty, searches the whole document body.

    Returns:
        The H1 text, or an empty string if not found or on error.
    """
    h1_text = ""
    try:
        # If no selector provided, default to body for searching H1
        search_area: Optional[Tag | BeautifulSoup] = soup.select_one(scope_selector) if scope_selector else soup.body
        if search_area:
            h1 = search_area.find("h1")
            if h1:
                h1_text = h1.get_text(strip=True)
                logging.debug(f"Found H1 in scope '{scope_selector or 'body'}': '{h1_text}'")
            else:
                logging.debug(f"No H1 tag found within scope '{scope_selector or 'body'}'.")
        # If scope_selector was provided but not found, select_one returns None
        elif scope_selector:
            logging.warning(f"Scope '{scope_selector}' not found for H1 extraction.")
        # If scope_selector was None and soup.body is None (unlikely but possible)
        elif not scope_selector and not soup.body:
             logging.warning("Could not find body element for H1 extraction.")

    except Exception as e:
        logging.warning(f"Error extracting H1 within scope '{scope_selector}': {e}")
    return h1_text

# ========================================
# Function: count_tags
# Description: Counts specified tags (e.g., H1-H6, img) within an optional scope.
# ========================================
# Function signature remains the same
def count_tags(soup: BeautifulSoup, tags: List[str], scope_selector: Optional[str] = None) -> int:
    """
    Counts specified tags (e.g., H1-H6, img) within an optional scope.

    Args:
        soup: BeautifulSoup object of the page.
        tags: A list of tag names to count (e.g., ['h1', 'h2', 'h3']).
        scope_selector: CSS selector for the scope.
                        If None or empty, searches the whole document body.

    Returns:
        The count of the specified tags, or 0 on error or if scope not found.
    """
    count = 0
    try:
        search_area = soup.select_one(scope_selector) if scope_selector else soup.body
        if search_area:
            found_tags = search_area.find_all(tags)
            count = len(found_tags)
            logging.debug(f"Found {count} tags {tags} in scope '{scope_selector or 'body'}'")
        elif scope_selector:
             logging.warning(f"Scope '{scope_selector}' not found for counting tags {tags}.")
        elif not scope_selector and not soup.body:
             logging.warning(f"Could not find body element for counting tags {tags}.")

    except Exception as e:
        logging.warning(f"Error counting tags '{tags}' within scope '{scope_selector}': {e}")
    return count

# ========================================
# Function: count_links
# Description: Counts internal or external links within an optional scope.
# ========================================
# Function signature remains the same
def count_links(soup: BeautifulSoup, base_url: str, internal: bool, scope_selector: Optional[str] = None) -> int:
    """
    Counts internal or external links within an optional scope.

    Args:
        soup: BeautifulSoup object of the page.
        base_url: The base URL of the page being analyzed (for domain comparison).
        internal: If True, count internal links; otherwise, count external links.
        scope_selector: CSS selector for the scope. If None or empty, searches the whole document body.

    Returns:
        The count of links, or 0 on error or if scope not found.
    """
    count = 0
    link_type_str = 'internal' if internal else 'external'
    try:
        search_area = soup.select_one(scope_selector) if scope_selector else soup.body
        if not search_area:
            if scope_selector:
                logging.warning(f"Scope '{scope_selector}' not found for counting links.")
            elif not soup.body:
                 logging.warning(f"Could not find body element for counting links.")
            return 0 # Return 0 if scope not found

        base_domain = urlparse(base_url).netloc.lower()
        links = search_area.find_all("a", href=True)
        logging.debug(f"Found {len(links)} total <a> tags with href in scope '{scope_selector or 'body'}'. Base domain: {base_domain}")

        for link in links:
            href = link["href"].strip()
            if not href or href.startswith("#") or href.startswith(("mailto:", "tel:", "javascript:")):
                continue

            parsed_link = urlparse(href)
            link_domain = parsed_link.netloc.lower()

            is_internal_link = False
            if link_domain and link_domain == base_domain:
                 is_internal_link = True
            elif not link_domain and (href.startswith('/') or not href.startswith(('http', '//'))): # Adjusted check for relative/absolute paths
                 is_internal_link = True

            if internal and is_internal_link:
                count += 1
                logging.debug(f"  Internal link counted: {href}")
            elif not internal and not is_internal_link:
                count += 1
                logging.debug(f"  External link counted: {href}")

        logging.debug(f"Counted {count} {link_type_str} links in scope '{scope_selector or 'body'}'")
        return count
    except Exception as e:
        logging.warning(f"Error counting {link_type_str} links: {e}", exc_info=True)
        return 0 # Return 0 on error

# ========================================
# Function: count_images_no_alt
# Description: Counts images without alt text or with empty alt text within an optional scope.
# ========================================
# Function signature remains the same
def count_images_no_alt(soup: BeautifulSoup, scope_selector: Optional[str] = None) -> int:
    """
    Counts images without alt text or with empty alt text within an optional scope.

    Args:
        soup: BeautifulSoup object of the page.
        scope_selector: CSS selector for the scope.
                        If None or empty, searches the whole document body.

    Returns:
        The count of images without proper alt text, or 0 on error or if scope not found.
    """
    count = 0
    try:
        search_area = soup.select_one(scope_selector) if scope_selector else soup.body
        if not search_area:
            if scope_selector:
                logging.warning(f"Scope '{scope_selector}' not found for counting images.")
            elif not soup.body:
                 logging.warning(f"Could not find body element for counting images.")
            return 0

        images = search_area.find_all("img")
        count = sum(1 for img in images if not img.get("alt", "").strip())
        logging.debug(f"Found {count} images without alt text in scope '{scope_selector or 'body'}' out of {len(images)} total images.")
    except Exception as e:
        logging.warning(f"Error counting images without alt text: {e}")
    return count

# ========================================
# Function: extract_page_slug
# Description: Extract the page slug (last part of the path) from the URL.
# ========================================
# (No changes needed here)
def extract_page_slug(url: str) -> str:
    """
    Extract the page slug (last part of the path) from the URL.

    Args:
        url: The URL string.

    Returns:
        The slug, 'homepage' if path is '/' or empty, or 'unknown' on error.
    """
    try:
        path = urlparse(url).path
        if not path or path == "/":
            return "homepage"
        slug = path.rstrip("/").split("/")[-1]
        return slug if slug else "index"
    except Exception as e:
        logging.warning(f"Error extracting page slug from {url}: {e}")
        return "unknown"

# ========================================
# Function: extract_body_class
# Description: Extracts the value of a specific class prefixed class from the body tag.
# ========================================
# (No changes needed here)
def extract_body_class(soup: BeautifulSoup, prefix: str, default: Optional[str] = None) -> Optional[str]:
    """
    Extracts the value of a specific class prefixed class from the body tag.

    Args:
        soup: BeautifulSoup object of the page.
        prefix: The prefix of the class name to find (e.g., 'page-id-').
        default: The value to return if the class is not found.

    Returns:
        The class value (without prefix), or the default value.
    """
    try:
        body = soup.body
        if body and body.has_attr("class"):
            classes = body.get("class", [])
            for cls in classes:
                if cls.startswith(prefix):
                    value = cls.replace(prefix, "").strip()
                    logging.debug(f"Found body class with prefix '{prefix}': {value}")
                    return value
        logging.debug(f"Body class with prefix '{prefix}' not found.")
        return default
    except Exception as e:
        logging.warning(f"Error extracting body class with prefix '{prefix}': {e}")
        return default

# ========================================
# Function: extract_placeholder_data
# Description: Placeholder function for future data extraction.
# ========================================
# (No changes needed here)
def extract_placeholder_data(soup: BeautifulSoup, data_type: str) -> Optional[Any]:
    """Placeholder function for future data extraction."""
    logging.debug(f"Placeholder function called for {data_type}. Needs implementation.")
    return None