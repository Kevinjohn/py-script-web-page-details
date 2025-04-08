# tests/test_html_parser.py
import pytest
from bs4 import BeautifulSoup

# Import the functions to test from your source file
from src.html_parser import (
    extract_meta_content, extract_meta_title, extract_h1, count_tags,
    count_links, count_images_no_alt, extract_body_class, extract_page_slug
)

# --- Test Data ---
SAMPLE_HTML_BASIC = """
<html>
<head>
    <title>Test Title</title>
    <meta name="description" content="Test Description.">
    <meta name="keywords" content="test, python, code">
    <meta property="og:title" content="OG Test Title">
</head>
<body class="page-id-123 parent-pageid-45 some-other-class">
    <article>
        <h1>Main Article H1</h1>
        <p>Some text with an <a href="/internal/link">internal link</a>.</p>
        <p>Another paragraph with <a href="https://www.external.com">external link</a>.</p>
        <img src="image1.jpg" alt="Image 1">
        <img src="image2.jpg"> <h2>Subtitle</h2>
        <a href="mailto:test@example.com">Mail Me</a>
        <a href="#">Anchor Link</a>
        <img src="image3.jpg" alt=""> </article>
    <aside>
        <h1>Sidebar H1 (Outside Article)</h1>
        <a href="/another/internal">Another internal</a>
    </aside>
</body>
</html>
"""

# --- Helper to create soup object ---
@pytest.fixture
def basic_soup():
    """Provides a basic BeautifulSoup object for testing."""
    return BeautifulSoup(SAMPLE_HTML_BASIC, 'html.parser')

# --- Tests ---

# ========================================
# Function: test_extract_meta_title
# Description: Tests extraction of the <title> tag content.
# ========================================
def test_extract_meta_title(basic_soup):
    """Tests extracting the page title."""
    assert extract_meta_title(basic_soup) == "Test Title"

# ========================================
# Function: test_extract_meta_content
# Description: Tests extracting content from various meta tags.
# ========================================
def test_extract_meta_content(basic_soup):
    """Tests extracting meta description and keywords."""
    assert extract_meta_content(basic_soup, "description") == "Test Description."
    assert extract_meta_content(basic_soup, "keywords") == "test, python, code"
    assert extract_meta_content(basic_soup, "og:title") == "OG Test Title"
    assert extract_meta_content(basic_soup, "nonexistent") == ""

# ========================================
# Function: test_extract_h1
# Description: Tests extracting the first H1 within the 'article' scope.
# ========================================
def test_extract_h1_in_article(basic_soup):
    """Tests extracting H1 within the default 'article' scope."""
    assert extract_h1(basic_soup, scope_selector="article") == "Main Article H1"

# ========================================
# Function: test_extract_h1_no_scope
# Description: Tests extracting the first H1 without a specific scope (finds first in body).
# ========================================
def test_extract_h1_no_scope(basic_soup):
    """Tests extracting H1 without scope (should find first in body)."""
    # This behavior might depend on exact implementation detail if multiple H1s exist
    assert extract_h1(basic_soup, scope_selector=None) == "Main Article H1" # Assumes article H1 is first

# ========================================
# Function: test_count_tags
# Description: Tests counting specific tags (h1, h2) within the 'article' scope.
# ========================================
def test_count_tags_in_article(basic_soup):
    """Tests counting H1 and H2 tags within the 'article' scope."""
    assert count_tags(basic_soup, ['h1'], scope_selector="article") == 1
    assert count_tags(basic_soup, ['h2'], scope_selector="article") == 1
    assert count_tags(basic_soup, ['h1', 'h2'], scope_selector="article") == 2
    assert count_tags(basic_soup, ['h3'], scope_selector="article") == 0
    assert count_tags(basic_soup, ['img'], scope_selector="article") == 3

# ========================================
# Function: test_count_links_internal_external
# Description: Tests counting internal and external links within the 'article' scope.
# ========================================
def test_count_links_internal_external(basic_soup):
    """Tests counting internal and external links within the 'article' scope."""
    base_url = "http://example.com/page" # Base URL needed for context
    assert count_links(basic_soup, base_url, internal=True, scope_selector="article") == 1
    assert count_links(basic_soup, base_url, internal=False, scope_selector="article") == 1
    # Test outside scope (should ignore links in aside)
    assert count_links(basic_soup, base_url, internal=True, scope_selector="aside") == 1
    assert count_links(basic_soup, base_url, internal=False, scope_selector="aside") == 0


# ========================================
# Function: test_count_images_no_alt
# Description: Tests counting images with missing or empty alt text within the 'article' scope.
# ========================================
def test_count_images_no_alt_in_article(basic_soup):
    """Tests counting images without proper alt text in 'article' scope."""
    # Expecting 2: one missing alt, one empty alt=""
    assert count_images_no_alt(basic_soup, scope_selector="article") == 2

# ========================================
# Function: test_extract_body_class
# Description: Tests extracting class prefixes from the body tag.
# ========================================
def test_extract_body_class(basic_soup):
    """Tests extracting prefixed classes from the body tag."""
    assert extract_body_class(basic_soup, "page-id-") == "123"
    assert extract_body_class(basic_soup, "parent-pageid-") == "45"
    assert extract_body_class(basic_soup, "nonexistent-") is None
    assert extract_body_class(basic_soup, "nonexistent-", default="default") == "default"

# ========================================
# Function: test_extract_page_slug
# Description: Tests extracting the slug from various URL formats.
# ========================================
# Parametrize allows running the same test function with different inputs/outputs
@pytest.mark.parametrize("url, expected_slug", [
    ("http://example.com/path/to/page", "page"),
    ("https://example.com/path/to/page/", "page"),
    ("https://example.com/", "homepage"),
    ("https://example.com", "homepage"),
    ("http://example.com/path/", "path"),
    ("http://example.com/slug.html", "slug.html"),
])
def test_extract_page_slug(url, expected_slug):
    """Tests extracting page slugs from various URLs."""
    assert extract_page_slug(url) == expected_slug