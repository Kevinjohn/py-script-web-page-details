import pytest
from src import py_script_web_page_details as script_to_test  # Import your functions
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Mocking (very important for testing web requests!)
from unittest.mock import patch
import requests


def test_extract_page_slug():
    """Tests for extract_page_slug function."""
    assert script_to_test.extract_page_slug("https://www.example.com/about-us/") == "about-us"
    assert script_to_test.extract_page_slug("https://www.example.com/") == "homepage"
    assert script_to_test.extract_page_slug("https://www.example.com/blog/article") == "article"
    assert script_to_test.extract_page_slug("https://www.example.com/index.html") == "index.html"


def test_extract_body_class():
    """Tests for extract_body_class function."""
    soup = BeautifulSoup('<body class="page-id-123 parent-pageid-456"></body>', "html.parser")
    assert script_to_test.extract_body_class(soup, "page-id-") == "123"
    assert script_to_test.extract_body_class(soup, "parent-pageid-", default="0") == "456"
    assert script_to_test.extract_body_class(soup, "nonexistent-", default="None") == "None"
    soup = BeautifulSoup('<body></body>', "html.parser")
    assert script_to_test.extract_body_class(soup, "page-id-") is None


def test_extract_meta_content():
    """Tests for extract_meta_content function."""
    soup = BeautifulSoup(
        '<meta name="description" content="Test description"><meta property="og:image" content="test.jpg">',
        "html.parser"
    )
    assert script_to_test.extract_meta_content(soup, "description") == "Test description"
    assert script_to_test.extract_meta_content(soup, "og:image") == "test.jpg"
    assert script_to_test.extract_meta_content(soup, "keywords") == ""


def test_extract_meta_title():
    """Tests for extract_meta_title function."""
    soup = BeautifulSoup('<title>Test Title</title>', "html.parser")
    assert script_to_test.extract_meta_title(soup) == "Test Title"
    soup = BeautifulSoup('<head></head>', "html.parser")
    assert script_to_test.extract_meta_title(soup) == ""


def test_extract_h1():
    """Tests for extract_h1 function."""
    soup = BeautifulSoup('<article><h1>Main Heading</h1></article>', "html.parser")
    assert script_to_test.extract_h1(soup) == "Main Heading"
    soup = BeautifulSoup('<div><h1>Main Heading</h1></div>', "html.parser")
    assert script_to_test.extract_h1(soup) == ""  # H1 not inside article
    soup = BeautifulSoup('<article></article>', "html.parser")
    assert script_to_test.extract_h1(soup) == ""


def test_count_headings():
    """Tests for count_headings function."""
    soup = BeautifulSoup('<article><h1>H1</h1><h2>H2</h2><h3>H3</h3></article>', "html.parser")
    assert script_to_test.count_headings(soup) == 3
    soup = BeautifulSoup('<div><h1>H1</h1><h2>H2</h2></div>', "html.parser")
    assert script_to_test.count_headings(soup) == 0  # Headings not in article
    soup = BeautifulSoup('<article></article>', "html.parser")
    assert script_to_test.count_headings(soup) == 0


def test_count_internal_links():
    """Tests for count_internal_links function."""
    soup = BeautifulSoup(
        '<article><a href="https://www.example.com/page1"></a><a href="/page2"></a>'
        '<a href="https://www.external.com"></a></article>',
        "html.parser"
    )
    base_url = "https://www.example.com"
    assert script_to_test.count_internal_links(soup, base_url) == 2
    soup = BeautifulSoup('<article></article>', "html.parser")
    assert script_to_test.count_internal_links(soup, base_url) == 0


def test_count_external_links():
    """Tests for count_external_links function."""
    soup = BeautifulSoup(
        '<article><a href="https://www.example.com/page1"></a><a href="/page2"></a>'
        '<a href="https://www.external.com"></a></article>',
        "html.parser"
    )
    base_url = "https://www.example.com"
    assert script_to_test.count_external_links(soup, base_url) == 1
    soup = BeautifulSoup('<article></article>', "html.parser")
    assert script_to_test.count_external_links(soup, base_url) == 0


def test_count_images():
    """Tests for count_images function."""
    soup = BeautifulSoup('<article><img src="1.jpg"><img src="2.jpg"></article>', "html.parser")
    assert script_to_test.count_images(soup) == 2
    soup = BeautifulSoup('<article></article>', "html.parser")
    assert script_to_test.count_images(soup) == 0


def test_count_images_no_alt():
    """Tests for count_images_no_alt function."""
    soup = BeautifulSoup(
        '<article><img src="1.jpg"><img src="2.jpg" alt="Alt text"><img src="3.jpg"></article>',
        "html.parser"
    )
    assert script_to_test.count_images_no_alt(soup) == 2
    soup = BeautifulSoup('<article><img src="1.jpg" alt=""></article>', "html.parser")
    assert script_to_test.count_images_no_alt(soup) == 1
    soup = BeautifulSoup('<article></article>', "html.parser")
    assert script_to_test.count_images_no_alt(soup) == 0


@patch('requests.head')
def test_fetch_http_status_and_type(mock_head):
    """Tests for fetch_http_status_and_type function."""

    # Mock a successful response
    mock_head.return_value.status_code = 200
    mock_head.return_value.headers = {"Content-Type": "text/html; charset=utf-8"}
    code, content_type = script_to_test.fetch_http_status_and_type("http://example.com")
    assert code == 200
    assert content_type == "text/html"

    # Mock a 404 response
    mock_head.return_value.status_code = 404
    mock_head.return_value.headers = {"Content-Type": "text/plain"}
    code, content_type = script_to_test.fetch_http_status_and_type("http://example.com/missing")
    assert code == 404
    assert content_type == "text/plain"

    # Mock an SSL error (this part might need adjusting based on your error handling)
    mock_head.side_effect = requests.exceptions.SSLError("SSL Error")
    code, content_type = script_to_test.fetch_http_status_and_type("https://invalid-ssl.com")
    assert code == "SSL Error"  # Or your specific SSL error code
    assert content_type == "Unknown"

    # Mock a general request exception
    mock_head.side_effect = requests.exceptions.RequestException("Request Exception")
    code, content_type = script_to_test.fetch_http_status_and_type("http://bad-url")
    assert code == "Unknown"
    assert content_type == "Unknown"


# You would add tests for read_input_file, sanitise_domain, and write_to_csv similarly
# (and any other functions you have)

if __name__ == '__main__':
    pytest.main()