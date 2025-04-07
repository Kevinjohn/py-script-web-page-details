# src/html_parser.py
import logging
from urllib.parse import urlparse
from typing import Optional, List, Any
from bs4 import BeautifulSoup

# --- HTML Parsing and Data Extraction Functions ---

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
        # Prioritize 'property' (often used for OpenGraph) then 'name'
        tag = soup.find("meta", attrs={"property": meta_name}) or \
              soup.find("meta", attrs={"name": meta_name})
        if tag and tag.has_attr("content"):
             content = tag["content"].strip()
             logging.debug(f"Found meta '{meta_name}': '{content[:50]}...'") # Log snippet
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
def extract_h1(soup: BeautifulSoup, scope_selector: Optional[str] = "article") -> str:
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
        scope_element = soup.select_one(scope_selector) if scope_selector else soup.body
        if scope_element:
            h1 = scope_element.find("h1")
            if h1:
                h1_text = h1.get_text(strip=True) # Use get_text() for robustness
                logging.debug(f"Found H1 in scope '{scope_selector or 'body'}': '{h1_text}'")
            else:
                logging.debug(f"No H1 tag found within scope '{scope_selector or 'body'}'.")
        else:
            logging.warning(f"Scope '{scope_selector}' not found for H1 extraction.")
    except Exception as e:
        logging.warning(f"Error extracting H1 within scope '{scope_selector}': {e}")
    return h1_text


# ========================================
# Function: count_tags
# Description: Counts specified tags (e.g., H1-H6, img) within an optional scope.
# ========================================
def count_tags(soup: BeautifulSoup, tags: List[str], scope_selector: Optional[str] = "article") -> int:
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
        scope_element = soup.select_one(scope_selector) if scope_selector else soup.body
        if scope_element:
            found_tags = scope_element.find_all(tags)
            count = len(found_tags)
            logging.debug(f"Found {count} tags {tags} in scope '{scope_selector or 'body'}'")
        else:
             logging.warning(f"Scope '{scope_selector}' not found for counting tags {tags}.")
    except Exception as e:
        logging.warning(f"Error counting tags '{tags}' within scope '{scope_selector}': {e}")
    return count


# ========================================
# Function: count_links
# Description: Counts internal or external links within an optional scope.
# ========================================
def count_links(soup: BeautifulSoup, base_url: str, internal: bool, scope_selector: Optional[str] = "article") -> int:
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
    try:
        scope_element = soup.select_one(scope_selector) if scope_selector else soup.body
        if not scope_element:
            logging.warning(f"Scope '{scope_selector}' not found for counting links.")
            return 0

        base_domain = urlparse(base_url).netloc.lower()
        links = scope_element.find_all("a", href=True)
        logging.debug(f"Found {len(links)} total <a> tags with href in scope '{scope_selector or 'body'}'. Base domain: {base_domain}")


        for link in links:
            href = link["href"].strip()
            if not href or href.startswith("#") or href.startswith(("mailto:", "tel:", "javascript:")):
                continue # Skip anchors, mailto, tel, javascript links

            parsed_link = urlparse(href)
            link_domain = parsed_link.netloc.lower()

            # Determine if internal based on domain or path structure
            is_internal_link = False
            if link_domain and link_domain == base_domain:
                 is_internal_link = True
            elif not link_domain and (href.startswith('/') or not href.startswith('http')):
                 # No domain, starts with / or is relative path without http -> internal
                 is_internal_link = True
            # else: link has a different domain or is absolute without matching domain -> external

            if internal and is_internal_link:
                count += 1
                logging.debug(f"  Internal link counted: {href}")
            elif not internal and not is_internal_link:
                count += 1
                logging.debug(f"  External link counted: {href}")

        link_type = 'internal' if internal else 'external'
        logging.debug(f"Counted {count} {link_type} links in scope '{scope_selector or 'body'}'")
        return count
    except Exception as e:
        link_type = 'internal' if internal else 'external'
        logging.warning(f"Error counting {link_type} links: {e}", exc_info=True)
        return 0 # Return 0 on error


# ========================================
# Function: count_images_no_alt
# Description: Counts images without alt text or with empty alt text within an optional scope.
# ========================================
def count_images_no_alt(soup: BeautifulSoup, scope_selector: Optional[str] = "article") -> int:
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
        scope_element = soup.select_one(scope_selector) if scope_selector else soup.body
        if not scope_element:
            logging.warning(f"Scope '{scope_selector}' not found for counting images.")
            return 0

        images = scope_element.find_all("img")
        # Count if 'alt' attribute is missing OR if it's present but empty/whitespace
        count = sum(1 for img in images if not img.get("alt", "").strip())
        logging.debug(f"Found {count} images without alt text in scope '{scope_selector or 'body'}' out of {len(images)} total images.")
    except Exception as e:
        logging.warning(f"Error counting images without alt text: {e}")
    return count


# ========================================
# Function: extract_page_slug
# Description: Extract the page slug (last part of the path) from the URL.
# ========================================
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
        # Get the last non-empty part of the path
        slug = path.rstrip("/").split("/")[-1]
        # Handle cases like '/folder/' which might result in empty slug after split
        return slug if slug else "index" # Or perhaps return the parent folder name? 'index' seems reasonable default
    except Exception as e:
        logging.warning(f"Error extracting page slug from {url}: {e}")
        return "unknown"


# ========================================
# Function: extract_body_class
# Description: Extracts the value of a specific class prefixed class from the body tag.
# ========================================
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
            classes = body.get("class", []) # body['class'] can return a list
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
def extract_placeholder_data(soup: BeautifulSoup, data_type: str) -> Optional[Any]:
    """Placeholder function for future data extraction."""
    # Example: Could be implemented to count words, find specific elements, etc.
    logging.debug(f"Placeholder function called for {data_type}. Needs implementation.")
    return None # Consistent return for unimplemented/failed extraction