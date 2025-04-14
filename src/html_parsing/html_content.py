# src/html_parsing/html_content.py
import logging
from typing import Optional, List, Any
from urllib.parse import urlparse # Needed for count_links
from bs4 import BeautifulSoup, Tag

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
# Function: extract_placeholder_data
# Description: Placeholder function for future data extraction.
# ========================================
def extract_placeholder_data(soup: BeautifulSoup, data_type: str) -> Optional[Any]:
    """ Placeholder function for future data extraction. """
    # Needs implementation if used
    logging.debug(f"Placeholder function called for {data_type}. Needs implementation.")
    return None