# tests/html_parsing/test_html_metadata.py
import pytest
from bs4 import BeautifulSoup

# Import functions to test
from src.html_parsing.html_metadata import extract_meta_content, extract_meta_title

# --- Test Data ---
SAMPLE_HTML_META = """
<html><head>
    <title>Test Title </title> <meta name="description" content=" Test Description. ">
    <meta name="keywords" content="test, python, code">
    <meta property="og:title" content=" OG Test Title ">
    <meta name="empty_meta" content="">
    <meta property="no_content_prop">
    <meta name="no_content_name">
</head><body></body></html>
"""
SAMPLE_HTML_NO_TITLE = "<html><head></head><body></body></html>"

# --- Fixtures ---
@pytest.fixture
def meta_soup():
    return BeautifulSoup(SAMPLE_HTML_META, 'html.parser')

@pytest.fixture
def no_title_soup():
    return BeautifulSoup(SAMPLE_HTML_NO_TITLE, 'html.parser')

# --- Tests ---

def test_extract_meta_title(meta_soup):
    """Tests extracting and stripping the page title."""
    assert extract_meta_title(meta_soup) == "Test Title" # Should be stripped

def test_extract_meta_title_missing_tag(no_title_soup):
    """Tests title extraction when <title> tag is absent."""
    assert extract_meta_title(no_title_soup) == ""

def test_extract_meta_content_name(meta_soup):
    """Tests extracting meta description by name."""
    assert extract_meta_content(meta_soup, "description") == "Test Description." # Should be stripped

def test_extract_meta_content_property(meta_soup):
    """Tests extracting meta property for OpenGraph title."""
    assert extract_meta_content(meta_soup, "og:title") == "OG Test Title" # Should be stripped

def test_extract_meta_content_keywords(meta_soup):
    """Tests extracting meta keywords."""
    assert extract_meta_content(meta_soup, "keywords") == "test, python, code"

def test_extract_meta_content_missing_tag(meta_soup):
    """Tests meta content extraction for a non-existent meta tag."""
    assert extract_meta_content(meta_soup, "nonexistent_meta") == ""

def test_extract_meta_content_empty_content(meta_soup):
    """Tests meta content extraction when content=''."""
    assert extract_meta_content(meta_soup, "empty_meta") == ""

def test_extract_meta_content_no_content_attr(meta_soup):
    """Tests meta tag extraction when the tag exists but lacks a content attribute."""
    assert extract_meta_content(meta_soup, "no_content_prop") == ""
    assert extract_meta_content(meta_soup, "no_content_name") == ""

def test_extract_meta_content_none_input(meta_soup):
    """Tests passing None as meta_name."""
    assert extract_meta_content(meta_soup, None) == ""

def test_extract_meta_content_empty_input(meta_soup):
    """Tests passing empty string as meta_name."""
    assert extract_meta_content(meta_soup, "") == ""