# tests/html_parsing/test_html_page.py
import pytest
from bs4 import BeautifulSoup

# Import function to test
from src.html_parsing.html_page import extract_body_class

# --- Test Data ---
SAMPLE_HTML_BODY_CLASS = """
<html><head><title>Body Class Test</title></head>
<body class=" page-id-123  parent-pageid-45 other another-class page-id-extra ">
<p>Content</p>
</body></html>
"""
SAMPLE_HTML_NO_BODY_CLASS = """
<html><head><title>No Body Class</title></head><body><p>Content</p></body></html>
"""
SAMPLE_HTML_NO_BODY = "<html><head><title>No Body</title></head></html>"

# --- Fixtures ---
@pytest.fixture
def body_class_soup():
    return BeautifulSoup(SAMPLE_HTML_BODY_CLASS, 'html.parser')

@pytest.fixture
def no_body_class_soup():
    return BeautifulSoup(SAMPLE_HTML_NO_BODY_CLASS, 'html.parser')

@pytest.fixture
def no_body_soup():
     return BeautifulSoup(SAMPLE_HTML_NO_BODY, 'html.parser')

# --- Tests ---

def test_extract_body_class_found(body_class_soup):
    """Tests finding existing prefixed classes."""
    assert extract_body_class(body_class_soup, "page-id-") == "123" # Finds first match
    assert extract_body_class(body_class_soup, "parent-pageid-") == "45"
    assert extract_body_class(body_class_soup, "other") == "" # Prefix matches but value is empty after replace

def test_extract_body_class_not_found(body_class_soup):
    """Tests searching for a prefix that doesn't exist."""
    assert extract_body_class(body_class_soup, "nonexistent-") is None

def test_extract_body_class_default_value(body_class_soup):
    """Tests using the default value when prefix is not found."""
    assert extract_body_class(body_class_soup, "nonexistent-", default="fallback") == "fallback"

def test_extract_body_class_missing_class_attr(no_body_class_soup):
    """Tests when the body tag has no class attribute."""
    assert extract_body_class(no_body_class_soup, "page-id-") is None
    assert extract_body_class(no_body_class_soup, "page-id-", default="fb") == "fb"

def test_extract_body_class_missing_body(no_body_soup):
    """Tests when the body tag itself is missing."""
    assert extract_body_class(no_body_soup, "page-id-") is None
    assert extract_body_class(no_body_soup, "page-id-", default="fb") == "fb"

def test_extract_body_class_invalid_prefix(body_class_soup):
     """Tests passing None or empty string as prefix."""
     assert extract_body_class(body_class_soup, None) is None
     assert extract_body_class(body_class_soup, "") is None
     assert extract_body_class(body_class_soup, "", default="fb") == "fb"