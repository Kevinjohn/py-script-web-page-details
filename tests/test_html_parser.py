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
    <meta name="empty_meta" content="">
</head>
<body class="page-id-123 parent-pageid-45 some-other-class">
    <article>
        <h1>Main Article H1</h1>
        <p>Some text with an <a href="/internal/link">internal link</a>.</p>
        <p>Another paragraph with <a href="https://www.external.com">external link</a>.</p>
        <a href="relative/page.html">Relative Link</a>
        <img src="image1.jpg" alt="Image 1">
        <img src="image2.jpg"> <h2>Subtitle</h2>
        <a href="mailto:test@example.com">Mail Me</a>
        <a href="#">Anchor Link</a>
        <a href="">Empty Href</a>
        <img src="image3.jpg" alt=""> <img src="image4.jpg" alt="   "> </article>
    <div id="no-h1-scope">
        <p>No H1 here.</p>
    </div>
    <aside>
        <h1>Sidebar H1 (Outside Article)</h1>
        <a href="/another/internal?query=1#frag">Another internal</a>
    </aside>
</body>
</html>
"""

SAMPLE_HTML_NO_TITLE = """
<html><head></head><body><p>Hello</p></body></html>
"""

SAMPLE_HTML_NO_ARTICLE = """
<html><head><title>No Article</title></head><body><p>Content</p></body></html>
"""

SAMPLE_HTML_NO_BODY_CLASS = """
<html><head><title>No Body Class</title></head><body><p>Content</p></body></html>
"""

# --- Helper to create soup objects ---
@pytest.fixture
def basic_soup():
    """Provides a basic BeautifulSoup object for testing."""
    return BeautifulSoup(SAMPLE_HTML_BASIC, 'html.parser')

@pytest.fixture
def no_title_soup():
    """Provides BeautifulSoup object with no title tag."""
    return BeautifulSoup(SAMPLE_HTML_NO_TITLE, 'html.parser')

@pytest.fixture
def no_article_soup():
    """Provides BeautifulSoup object with no article tag."""
    return BeautifulSoup(SAMPLE_HTML_NO_ARTICLE, 'html.parser')

@pytest.fixture
def no_body_class_soup():
    """Provides BeautifulSoup object with no body class attribute."""
    return BeautifulSoup(SAMPLE_HTML_NO_BODY_CLASS, 'html.parser')

# --- Existing Tests (kept for regression) ---

def test_extract_meta_title(basic_soup):
    assert extract_meta_title(basic_soup) == "Test Title"

def test_extract_meta_content(basic_soup):
    assert extract_meta_content(basic_soup, "description") == "Test Description."
    assert extract_meta_content(basic_soup, "keywords") == "test, python, code"
    assert extract_meta_content(basic_soup, "og:title") == "OG Test Title"

def test_extract_h1_in_article(basic_soup):
    assert extract_h1(basic_soup, scope_selector="article") == "Main Article H1"

def test_extract_h1_no_scope(basic_soup):
    assert extract_h1(basic_soup, scope_selector=None) == "Main Article H1"

def test_count_tags_in_article(basic_soup):
    assert count_tags(basic_soup, ['h1'], scope_selector="article") == 1
    assert count_tags(basic_soup, ['h2'], scope_selector="article") == 1
    assert count_tags(basic_soup, ['h1', 'h2'], scope_selector="article") == 2
    assert count_tags(basic_soup, ['h3'], scope_selector="article") == 0
    assert count_tags(basic_soup, ['img'], scope_selector="article") == 4 # Updated count

def test_count_links_internal_external(basic_soup):
    base_url = "http://example.com/page"
    # /internal/link, relative/page.html should count as internal
    assert count_links(basic_soup, base_url, internal=True, scope_selector="article") == 2
    # https://www.external.com should count as external
    assert count_links(basic_soup, base_url, internal=False, scope_selector="article") == 1
    # Test outside scope (aside)
    assert count_links(basic_soup, base_url, internal=True, scope_selector="aside") == 1
    assert count_links(basic_soup, base_url, internal=False, scope_selector="aside") == 0

def test_count_images_no_alt_in_article(basic_soup):
    # Expecting 3: one missing alt, one empty alt="", one whitespace alt="   "
    assert count_images_no_alt(basic_soup, scope_selector="article") == 3

def test_extract_body_class(basic_soup):
    assert extract_body_class(basic_soup, "page-id-") == "123"
    assert extract_body_class(basic_soup, "parent-pageid-") == "45"
    assert extract_body_class(basic_soup, "nonexistent-") is None
    assert extract_body_class(basic_soup, "nonexistent-", default="default") == "default"

@pytest.mark.parametrize("url, expected_slug", [
    ("http://example.com/path/to/page", "page"),
    ("https://example.com/path/to/page/", "page"),
    ("https://example.com/", "homepage"),
    ("https://example.com", "homepage"),
    ("http://example.com/path/", "path"),
    ("http://example.com/slug.html", "slug.html"),
])
def test_extract_page_slug(url, expected_slug):
    assert extract_page_slug(url) == expected_slug

# --- NEW Tests ---

# ========================================
# Function: test_extract_meta_title_missing_tag
# Description: Tests title extraction when the tag is missing.
# ========================================
def test_extract_meta_title_missing_tag(no_title_soup):
    """Tests title extraction when <title> tag is absent."""
    assert extract_meta_title(no_title_soup) == ""

# ========================================
# Function: test_extract_meta_content_missing_tag
# Description: Tests meta content extraction when the specific tag is missing.
# ========================================
def test_extract_meta_content_missing_tag(basic_soup):
    """Tests meta content extraction for a non-existent meta tag."""
    assert extract_meta_content(basic_soup, "nonexistent_meta") == ""

# ========================================
# Function: test_extract_meta_content_empty_content
# Description: Tests meta content extraction when content attribute is empty.
# ========================================
def test_extract_meta_content_empty_content(basic_soup):
    """Tests meta content extraction when content=''."""
    assert extract_meta_content(basic_soup, "empty_meta") == ""

# ========================================
# Function: test_extract_h1_missing_in_scope
# Description: Tests H1 extraction when H1 is missing within the scope.
# ========================================
def test_extract_h1_missing_in_scope(basic_soup):
    """Tests H1 extraction when the scope exists but has no H1."""
    assert extract_h1(basic_soup, scope_selector="#no-h1-scope") == ""

# ========================================
# Function: test_extract_h1_missing_scope
# Description: Tests H1 extraction when the scope selector finds nothing.
# ========================================
def test_extract_h1_missing_scope(basic_soup):
    """Tests H1 extraction when the scope itself is missing."""
    assert extract_h1(basic_soup, scope_selector="#nonexistent-scope") == ""

# ========================================
# Function: test_count_tags_missing_scope
# Description: Tests tag counting when the scope selector finds nothing.
# ========================================
def test_count_tags_missing_scope(basic_soup):
    """Tests tag counting returns 0 if scope is missing."""
    assert count_tags(basic_soup, ['h1', 'p'], scope_selector="#nonexistent-scope") == 0

# ========================================
# Function: test_count_links_variations
# Description: Tests link counting with different href types within the article scope.
# ========================================
def test_count_links_variations(basic_soup):
    """Tests different types of links within the article scope."""
    base_url = "http://example.com/page/"
    # Internal: /internal/link (absolute path), relative/page.html (relative) -> Expected 2
    assert count_links(basic_soup, base_url, internal=True, scope_selector="article") == 2
    # External: https://www.external.com -> Expected 1
    assert count_links(basic_soup, base_url, internal=False, scope_selector="article") == 1
    # Check total links found (excluding mailto:, #, empty href)
    # /internal/link, https://www.external.com, relative/page.html -> 3 countable links
    article_scope = basic_soup.select_one("article")
    all_a_tags = article_scope.find_all("a", href=True)
    countable_links = [a for a in all_a_tags if a['href'] and not a['href'].startswith(('#', 'mailto:', 'javascript:'))]
    assert len(countable_links) == 3


# ========================================
# Function: test_count_links_missing_scope
# Description: Tests link counting when the scope selector finds nothing.
# ========================================
def test_count_links_missing_scope(basic_soup):
    """Tests link counting returns 0 if scope is missing."""
    base_url = "http://example.com/page"
    assert count_links(basic_soup, base_url, internal=True, scope_selector="#nonexistent-scope") == 0
    assert count_links(basic_soup, base_url, internal=False, scope_selector="#nonexistent-scope") == 0

# ========================================
# Function: test_extract_page_slug_variations
# Description: Tests page slug extraction with query params and fragments.
# ========================================
@pytest.mark.parametrize("url, expected_slug", [
    ("http://example.com/page?query=1", "page"),
    ("https://example.com/page#fragment", "page"),
    ("https://example.com/page/?query=1#frag", "page"),
    ("http://example.com", "homepage"), # Just domain
])
def test_extract_page_slug_variations(url, expected_slug):
    """Tests extracting page slugs with query params and fragments."""
    assert extract_page_slug(url) == expected_slug

# ========================================
# Function: test_extract_body_class_missing
# Description: Tests body class extraction when body/class attribute is missing.
# ========================================
def test_extract_body_class_missing(no_body_class_soup):
    """Tests body class extraction when body or class attribute is missing."""
    assert extract_body_class(no_body_class_soup, "page-id-") is None
    assert extract_body_class(no_body_class_soup, "page-id-", default="fallback") == "fallback"

# ========================================
# Function: test_count_images_no_alt_missing_scope
# Description: Tests image alt counting when scope is missing.
# ========================================
def test_count_images_no_alt_missing_scope(basic_soup):
    """Tests counting images with no alt returns 0 if scope is missing."""
    assert count_images_no_alt(basic_soup, scope_selector="#nonexistent-scope") == 0