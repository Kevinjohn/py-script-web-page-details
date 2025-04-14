# tests/html_parsing/test_html_content.py
import pytest
from bs4 import BeautifulSoup

# Import functions to test
from src.html_parsing.html_content import (
    extract_h1, count_tags, count_links, count_images_no_alt,
    extract_placeholder_data # Keep placeholder test
)

# --- Test Data ---
SAMPLE_HTML_CONTENT = """
<html><head><title>Content Test</title></head><body>
    <header><h1>Site Title (Outside Scope)</h1></header>
    <main>
        <h1>Main Content H1</h1>
        <p>Paragraph 1 with <a href="/page1">internal</a> link.</p>
        <section>
            <h2>Section H2</h2>
            <p>Para 2 with <a href="https://example.org">external</a>.</p>
            <img src="img1.jpg" alt="Good Alt">
            <img src="img2.jpg">
            <img src="img3.jpg" alt="">
            <a href="#frag">Fragment</a>
        </section>
    </main>
    <article> <h2>Article H2</h2>
         <p>Article text.</p>
         <a href="rel/page2.html">Relative</a>
         <img src="img4.jpg" alt=" "> </article>
    <div id="no-h1-scope">
        <p>No H1 here.</p>
    </div>
</body></html>
"""

# --- Fixtures ---
@pytest.fixture
def content_soup():
    return BeautifulSoup(SAMPLE_HTML_CONTENT, 'html.parser')

# --- Tests ---

# ========================================
# Tests for extract_h1
# ========================================
def test_extract_h1_in_scope(content_soup):
    assert extract_h1(content_soup, scope_selector="main") == "Main Content H1"
    assert extract_h1(content_soup, scope_selector="article") == "" # No H1 in article

def test_extract_h1_no_scope(content_soup):
    # Should find first H1 in body, which is in header
    assert extract_h1(content_soup, scope_selector=None) == "Site Title (Outside Scope)"

def test_extract_h1_missing_in_scope(content_soup):
    assert extract_h1(content_soup, scope_selector="#no-h1-scope") == ""

def test_extract_h1_missing_scope(content_soup):
    assert extract_h1(content_soup, scope_selector="#nonexistent") == ""


# ========================================
# Tests for count_tags
# ========================================
def test_count_tags_in_scope(content_soup):
    assert count_tags(content_soup, ['h1'], scope_selector="main") == 1
    assert count_tags(content_soup, ['h2'], scope_selector="main") == 1
    assert count_tags(content_soup, ['img'], scope_selector="main") == 3
    assert count_tags(content_soup, ['p'], scope_selector="main") == 2
    assert count_tags(content_soup, ['h1', 'h2', 'p'], scope_selector="main") == 4

def test_count_tags_different_scope(content_soup):
     assert count_tags(content_soup, ['h2'], scope_selector="article") == 1
     assert count_tags(content_soup, ['p'], scope_selector="article") == 1
     assert count_tags(content_soup, ['h1'], scope_selector="article") == 0

def test_count_tags_no_scope(content_soup):
    # Counts across whole body
    assert count_tags(content_soup, ['h1'], scope_selector=None) == 2
    assert count_tags(content_soup, ['h2'], scope_selector=None) == 2
    assert count_tags(content_soup, ['p'], scope_selector=None) == 4
    assert count_tags(content_soup, ['img'], scope_selector=None) == 4

def test_count_tags_missing_scope(content_soup):
    assert count_tags(content_soup, ['p'], scope_selector="#nonexistent") == 0

def test_count_tags_empty_list(content_soup):
     assert count_tags(content_soup, [], scope_selector="main") == 0

def test_count_tags_invalid_tags(content_soup):
     assert count_tags(content_soup, ['p', None, 123], scope_selector="main") == 2 # Should ignore non-strings


# ========================================
# Tests for count_links
# ========================================
BASE_URL_FOR_LINKS = "http://example.com/some/path"

def test_count_links_in_scope(content_soup):
    # main scope: /page1 (internal), https://example.org (external), #frag (ignore)
    assert count_links(content_soup, BASE_URL_FOR_LINKS, internal=True, scope_selector="main") == 1
    assert count_links(content_soup, BASE_URL_FOR_LINKS, internal=False, scope_selector="main") == 1

def test_count_links_different_scope(content_soup):
    # article scope: rel/page2.html (internal)
    assert count_links(content_soup, BASE_URL_FOR_LINKS, internal=True, scope_selector="article") == 1
    assert count_links(content_soup, BASE_URL_FOR_LINKS, internal=False, scope_selector="article") == 0

def test_count_links_no_scope(content_soup):
    # whole body: /page1, rel/page2.html -> 2 internal
    # https://example.org -> 1 external
    assert count_links(content_soup, BASE_URL_FOR_LINKS, internal=True, scope_selector=None) == 2
    assert count_links(content_soup, BASE_URL_FOR_LINKS, internal=False, scope_selector=None) == 1

def test_count_links_missing_scope(content_soup):
    assert count_links(content_soup, BASE_URL_FOR_LINKS, internal=True, scope_selector="#nonexistent") == 0

# ========================================
# Tests for count_images_no_alt
# ========================================
def test_count_images_no_alt_in_scope(content_soup):
    # main scope: img2 (missing), img3 (empty) -> 2
    assert count_images_no_alt(content_soup, scope_selector="main") == 2

def test_count_images_no_alt_different_scope(content_soup):
    # article scope: img4 (whitespace) -> 1
    assert count_images_no_alt(content_soup, scope_selector="article") == 1

def test_count_images_no_alt_no_scope(content_soup):
    # whole body: img2, img3, img4 -> 3
    assert count_images_no_alt(content_soup, scope_selector=None) == 3

def test_count_images_no_alt_missing_scope(content_soup):
    assert count_images_no_alt(content_soup, scope_selector="#nonexistent") == 0

# ========================================
# Test for extract_placeholder_data
# ========================================
def test_extract_placeholder_data(content_soup):
    # Just test that it returns None for now
    assert extract_placeholder_data(content_soup, "any_type") is None