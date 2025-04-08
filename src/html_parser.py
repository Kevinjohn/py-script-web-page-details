# src/html_parser.py
import logging
from urllib.parse import urlparse, ParseResult # Added ParseResult for type hint
# Make sure typing includes Dict for the new function's return type
from typing import Optional, List, Any, Dict
from bs4 import BeautifulSoup, Tag # Import Tag for type hinting if needed

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


# --- Existing HTML Parsing and Data Extraction Functions ---
# (Includes minor robustness enhancements)

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

# ========================================
# Function: extract_h1
# Description: Extract the text of the first H1 tag, optionally within a specific scope.
# ========================================
def extract_h1(soup: BeautifulSoup, scope_selector: Optional[str] = None) -> str:
    """ Extract the text of the first H1 tag, optionally within a specific scope. """
    h1_text = ""
    search_area: Optional[Tag | BeautifulSoup] = None # Define variable before try block
    try:
        if scope_selector:
            search_area = soup.select_one(scope_selector)
            if not search_area:
                logging.warning(f"Scope '{scope_selector}' not found for H1 extraction.")
                return h1_text # Return "" if scope not found
        else:
            search_area = soup.body
            if not search_area:
                 logging.warning("Could not find body element for H1 extraction.")
                 return h1_text # Return "" if body not found

        # Proceed only if search_area is valid
        h1 = search_area.find("h1") # Find within the determined area
        if h1:
            h1_text = h1.get_text(strip=True)
            logging.debug(f"Found H1 in scope '{scope_selector or 'body'}': '{h1_text}'")
        else:
            logging.debug(f"No H1 tag found within scope '{scope_selector or 'body'}'.")

    except Exception as e:
        logging.warning(f"Error extracting H1 within scope '{scope_selector or 'body'}': {e}", exc_info=True)
    return h1_text

# ========================================
# Function: count_tags
# Description: Counts specified tags (e.g., H1-H6, img) within an optional scope.
# ========================================
def count_tags(soup: BeautifulSoup, tags: List[str], scope_selector: Optional[str] = None) -> int:
    """ Counts specified tags within an optional scope. """
    count = 0
    if not tags or not isinstance(tags, list): return count # Nothing to count or invalid input
    search_area: Optional[Tag | BeautifulSoup] = None # Define variable
    try:
        if scope_selector:
            search_area = soup.select_one(scope_selector)
            if not search_area:
                 logging.warning(f"Scope '{scope_selector}' not found for counting tags {tags}.")
                 return count # Return 0 if scope not found
        else:
             search_area = soup.body
             if not search_area:
                  logging.warning(f"Could not find body element for counting tags {tags}.")
                  return count # Return 0 if body not found

        # Ensure tags in the list are strings before passing to find_all
        valid_tags = [tag for tag in tags if isinstance(tag, str)]
        if not valid_tags:
             logging.warning("No valid string tag names provided for counting.")
             return count

        found_tags = search_area.find_all(valid_tags)
        count = len(found_tags)
        logging.debug(f"Found {count} tags {valid_tags} in scope '{scope_selector or 'body'}'")

    except Exception as e:
        logging.warning(f"Error counting tags '{tags}' within scope '{scope_selector or 'body'}': {e}", exc_info=True)
    return count

# ========================================
# Function: count_links
# Description: Counts internal or external links within an optional scope.
# ========================================
def count_links(soup: BeautifulSoup, base_url: str, internal: bool, scope_selector: Optional[str] = None) -> int:
    """ Counts internal or external links within an optional scope. """
    count = 0
    link_type_str = 'internal' if internal else 'external'
    search_area: Optional[Tag | BeautifulSoup] = None # Define variable
    try:
        if scope_selector:
            search_area = soup.select_one(scope_selector)
            if not search_area:
                logging.warning(f"Scope '{scope_selector}' not found for counting links.")
                return count
        else:
             search_area = soup.body
             if not search_area:
                  logging.warning(f"Could not find body element for counting links.")
                  return count

        base_domain = urlparse(base_url).netloc.lower() if base_url and isinstance(base_url, str) else ""
        links = search_area.find_all("a", href=True)
        logging.debug(f"Found {len(links)} total <a> tags with href in scope '{scope_selector or 'body'}'. Base domain: {base_domain}")

        for link in links:
            href = link.get("href") # Use .get for safety
            if not href or not isinstance(href, str): continue # Skip if no href or not string
            href = href.strip()
            if not href or href.startswith("#") or href.startswith(("mailto:", "tel:", "javascript:")):
                continue

            try: # Add inner try-except for robustness against invalid hrefs during urlparse
                parsed_link = urlparse(href)
                link_domain = parsed_link.netloc.lower()
            except ValueError:
                logging.debug(f"Skipping link due to parsing error: {href}")
                continue # Skip malformed URLs

            is_internal_link = False
            # Check base_domain exists before comparing
            if base_domain and link_domain and link_domain == base_domain:
                 is_internal_link = True
            # Ensure href is treated as string for startswith
            elif not link_domain and (href.startswith('/') or not href.startswith(('http', '//'))):
                 is_internal_link = True

            if internal and is_internal_link:
                count += 1
            elif not internal and not is_internal_link:
                count += 1

        logging.debug(f"Counted {count} {link_type_str} links in scope '{scope_selector or 'body'}'")

    except Exception as e:
        logging.warning(f"Error counting {link_type_str} links: {e}", exc_info=True)
    return count

# ========================================
# Function: count_images_no_alt
# Description: Counts images without alt text or with empty alt text within an optional scope.
# ========================================
def count_images_no_alt(soup: BeautifulSoup, scope_selector: Optional[str] = None) -> int:
    """ Counts images without alt text or with empty alt text within an optional scope. """
    count = 0
    search_area: Optional[Tag | BeautifulSoup] = None # Define variable
    try:
        if scope_selector:
             search_area = soup.select_one(scope_selector)
             if not search_area:
                  logging.warning(f"Scope '{scope_selector}' not found for counting images.")
                  return count
        else:
             search_area = soup.body
             if not search_area:
                  logging.warning(f"Could not find body element for counting images.")
                  return count

        images = search_area.find_all("img")
        count = sum(1 for img in images if not img.get("alt", "").strip()) # .get is safe
        logging.debug(f"Found {count} images without alt text in scope '{scope_selector or 'body'}' out of {len(images)} total images.")
    except Exception as e:
        logging.warning(f"Error counting images without alt text: {e}", exc_info=True)
    return count

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
        return slug if slug else "index"
    except Exception as e:
        logging.warning(f"Error extracting page slug from {url}: {e}", exc_info=True)
        return "unknown"

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

# ========================================
# Function: extract_placeholder_data
# Description: Placeholder function for future data extraction.
# ========================================
def extract_placeholder_data(soup: BeautifulSoup, data_type: str) -> Optional[Any]:
    """ Placeholder function for future data extraction. """
    logging.debug(f"Placeholder function called for {data_type}. Needs implementation.")
    return None