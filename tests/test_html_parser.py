# tests/test_html_parser.py
import pytest
from bs4 import BeautifulSoup

# Import ALL functions to test from your source file, including the new ones
from src.html_parser import (
    find_content_scope, no_semantic_base_html_tag, # Make sure these are included
    extract_meta_content, extract_meta_title, extract_h1, count_tags,
    count_links, count_images_no_alt, extract_body_class, extract_page_slug
)
# Import DEFAULT_SETTINGS to easily access the default priority list for tests
from src.config_loader import DEFAULT_SETTINGS


# --- Test Data ---
# (Define ALL sample HTML strings as constants at the module level)
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

# --- Samples for Scope Testing (Defined as constants) ---
HTML_WITH_MAIN = "<body><header></header><main><h1>Main Content</h1></main><footer></footer></body>"
HTML_WITH_DIV_ROLE = '<body><header></header><div role="main"><h1>Div Role Main</h1></div><footer></footer></body>'
HTML_WITH_MULTI_ARTICLE = "<body><article>One</article><article>Two</article></body>"
HTML_WITH_MAIN_AND_ARTICLE = "<body><main><h1>Main</h1><article>Sub</article></main></body>"
HTML_WITH_DIV_AND_ARTICLE = '<body><div role="main"><h1>Main</h1><article>Sub</article></div></body>'
HTML_WITH_NONE = "<body><header></header><div>Just a div</div><footer></footer></body>"


# --- Helper Fixtures ---
# (Keep existing fixtures)
@pytest.fixture
def basic_soup():
    return BeautifulSoup(SAMPLE_HTML_BASIC, 'html.parser')

@pytest.fixture
def no_title_soup():
    return BeautifulSoup(SAMPLE_HTML_NO_TITLE, 'html.parser')

@pytest.fixture
def no_article_soup():
    """Provides BeautifulSoup object with no article tag."""
    return BeautifulSoup(SAMPLE_HTML_NO_ARTICLE, 'html.parser')

@pytest.fixture
def no_body_class_soup():
    """Provides BeautifulSoup object with no body class attribute."""
    return BeautifulSoup(SAMPLE_HTML_NO_BODY_CLASS, 'html.parser')


# --- Existing Tests ---
# (Keep all existing test functions: test_extract_meta_title, etc.)
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
    assert count_links(basic_soup, base_url, internal=True, scope_selector="article") == 2
    assert count_links(basic_soup, base_url, internal=False, scope_selector="article") == 1
    assert count_links(basic_soup, base_url, internal=True, scope_selector="aside") == 1
    assert count_links(basic_soup, base_url, internal=False, scope_selector="aside") == 0

def test_count_images_no_alt_in_article(basic_soup):
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

def test_extract_meta_title_missing_tag(no_title_soup):
    assert extract_meta_title(no_title_soup) == ""

def test_extract_meta_content_missing_tag(basic_soup):
    assert extract_meta_content(basic_soup, "nonexistent_meta") == ""

def test_extract_meta_content_empty_content(basic_soup):
    assert extract_meta_content(basic_soup, "empty_meta") == ""

def test_extract_h1_missing_in_scope(basic_soup):
    assert extract_h1(basic_soup, scope_selector="#no-h1-scope") == ""

def test_extract_h1_missing_scope(basic_soup):
    assert extract_h1(basic_soup, scope_selector="#nonexistent-scope") == ""

def test_count_tags_missing_scope(basic_soup):
    assert count_tags(basic_soup, ['h1', 'p'], scope_selector="#nonexistent-scope") == 0

def test_count_links_variations(basic_soup):
    base_url = "http://example.com/page/"
    assert count_links(basic_soup, base_url, internal=True, scope_selector="article") == 2
    assert count_links(basic_soup, base_url, internal=False, scope_selector="article") == 1
    article_scope = basic_soup.select_one("article")
    all_a_tags = article_scope.find_all("a", href=True)
    countable_links = [a for a in all_a_tags if a['href'] and not a['href'].startswith(('#', 'mailto:', 'javascript:'))]
    assert len(countable_links) == 3

def test_count_links_missing_scope(basic_soup):
    base_url = "http://example.com/page"
    assert count_links(basic_soup, base_url, internal=True, scope_selector="#nonexistent-scope") == 0
    assert count_links(basic_soup, base_url, internal=False, scope_selector="#nonexistent-scope") == 0

@pytest.mark.parametrize("url, expected_slug", [
    ("http://example.com/page?query=1", "page"),
    ("https://example.com/page#fragment", "page"),
    ("https://example.com/page/?query=1#frag", "page"),
    ("http://example.com", "homepage"),
])
def test_extract_page_slug_variations(url, expected_slug):
    assert extract_page_slug(url) == expected_slug

def test_extract_body_class_missing(no_body_class_soup):
    assert extract_body_class(no_body_class_soup, "page-id-") is None
    assert extract_body_class(no_body_class_soup, "page-id-", default="fallback") == "fallback"

def test_count_images_no_alt_missing_scope(basic_soup):
    assert count_images_no_alt(basic_soup, scope_selector="#nonexistent-scope") == 0


# --- NEW Tests for Scope Finding (Corrected Calls & Assertions) ---

# Use the default priority list for most scope tests for simplicity
DEFAULT_PRIORITY = DEFAULT_SETTINGS["scope_selectors_priority"]

# ========================================
# Function: test_find_content_scope_main
# ========================================
def test_find_content_scope_main():
    """Tests that <main> tag is preferred."""
    soup = BeautifulSoup(HTML_WITH_MAIN, 'html.parser') # Use constant
    # *** Pass priority_list argument ***
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "main" # Use imported function

# ========================================
# Function: test_find_content_scope_div_role
# ========================================
def test_find_content_scope_div_role():
    """Tests that <div role='main'> is found if <main> is not present."""
    soup = BeautifulSoup(HTML_WITH_DIV_ROLE, 'html.parser') # Use constant
    # *** Corrected Assertion: Expect single quotes inside ***
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "div[role='main']" # Use imported function

# ========================================
# Function: test_find_content_scope_single_article
# ========================================
def test_find_content_scope_single_article(basic_soup):
    """Tests finding a single <article> if <main> and div[role=main] absent."""
    # *** Pass priority_list argument ***
    assert find_content_scope(basic_soup, priority_list=DEFAULT_PRIORITY) == "article" # Use imported function

# ========================================
# Function: test_find_content_scope_multiple_articles
# ========================================
def test_find_content_scope_multiple_articles():
    """Tests that multiple <article> tags result in no scope found."""
    soup = BeautifulSoup(HTML_WITH_MULTI_ARTICLE, 'html.parser') # Use constant
    # *** Pass priority_list argument ***
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) is None # Use imported function

# ========================================
# Function: test_find_content_scope_main_preferred
# ========================================
def test_find_content_scope_main_preferred():
    """Tests that <main> is chosen even if <article> is present."""
    soup = BeautifulSoup(HTML_WITH_MAIN_AND_ARTICLE, 'html.parser') # Use constant
    # *** Pass priority_list argument ***
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "main" # Use imported function

# ========================================
# Function: test_find_content_scope_div_role_preferred
# ========================================
def test_find_content_scope_div_role_preferred():
    """Tests that <div role='main'> is chosen over <article>."""
    soup = BeautifulSoup(HTML_WITH_DIV_AND_ARTICLE, 'html.parser') # Use constant
    # *** Corrected Assertion: Expect single quotes inside ***
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "div[role='main']" # Use imported function

# ========================================
# Function: test_find_content_scope_none_found
# ========================================
def test_find_content_scope_none_found():
    """Tests returning None when no suitable tags are present."""
    soup = BeautifulSoup(HTML_WITH_NONE, 'html.parser') # Use constant
    # *** Pass priority_list argument ***
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) is None # Use imported function

# ========================================
# Function: test_find_content_scope_custom_priority
# ========================================
def test_find_content_scope_custom_priority():
    """Tests using a custom priority list."""
    # HTML has main and article, custom priority prefers article
    soup = BeautifulSoup(HTML_WITH_MAIN_AND_ARTICLE, 'html.parser')
    custom_priority = ["article", "main"] # Article first
     # *** Pass custom priority_list argument ***
    assert find_content_scope(soup, priority_list=custom_priority) == "article"


# ========================================
# Function: test_no_semantic_base_html_tag
# ========================================
# (No changes needed here as it didn't call the modified function)
def test_no_semantic_base_html_tag():
    """Tests the structure and error message from the fallback function."""
    test_url = "http://example.com/no-scope"
    result = no_semantic_base_html_tag(test_url) # Use imported function

    assert isinstance(result, dict)
    assert "IA error" in result
    assert "No primary semantic content tag found" in result["IA error"]
    # Check that scope-dependent fields have default values
    assert result.get("Article H1") == ""
    assert result.get("Article Headings") == 0
    # ... (add checks for other fields if needed)