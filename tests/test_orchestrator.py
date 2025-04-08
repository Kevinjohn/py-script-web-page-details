# tests/test_orchestrator.py
import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup # Needed for return type hints if used

from src.orchestrator import extract_metadata

# ========================================
# Function: test_extract_metadata_success_flow
# Description: Tests the successful extraction flow, mocking dependencies.
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.extract_meta_title') # Mock all parser functions used
@patch('src.orchestrator.extract_meta_content')
@patch('src.orchestrator.extract_h1')
@patch('src.orchestrator.count_tags')
@patch('src.orchestrator.count_links')
@patch('src.orchestrator.count_images_no_alt')
@patch('src.orchestrator.extract_body_class')
# Add mocks for any other parser functions used by orchestrator...
def test_extract_metadata_success_flow(
    mock_extract_body_class, mock_count_images_no_alt, mock_count_links,
    mock_count_tags, mock_extract_h1, mock_extract_meta_content,
    mock_extract_meta_title, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests the 'happy path' where all dependencies return expected values."""
    # --- Mock Setup ---
    test_url = "https://good.example.com"
    mock_driver = MagicMock() # Mock selenium driver object
    ssl_decision_state = {}

    # Mock return values for dependencies
    mock_fetch_status.return_value = (200, "text/html")
    mock_sample_soup = BeautifulSoup("<html><title>Good Page</title></html>", 'html.parser')
    mock_fetch_parse.return_value = mock_sample_soup
    mock_extract_page_slug.return_value = "good_page"
    mock_extract_meta_title.return_value = "Good Page Title"
    # Setup returns for all other mocked parser functions...
    mock_extract_meta_content.return_value = "Mock Description" # Example for one
    mock_extract_h1.return_value = "Mock H1"
    mock_count_tags.return_value = 5 # Example
    mock_count_links.return_value = 10 # Example
    mock_count_images_no_alt.return_value = 1 # Example
    mock_extract_body_class.return_value = "page-id-mock" # Example


    # --- Call the function ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    # --- Assertions ---
    assert result is not None
    assert result["Page-URL"] == test_url
    assert result["http-code"] == 200
    assert result["http-type"] == "text/html"
    assert result["IA error"] == "" # No error on happy path
    assert result["page-slug"] == "good_page"
    assert result["Title"] == "Good Page Title"
    assert result["Description"] == "Mock Description" # Check other mocked values...
    assert result["Article H1"] == "Mock H1"
    # Add assertions for all the fields based on mocked returns

    # Check that dependencies were called
    mock_fetch_status.assert_called_once_with(test_url, ssl_decision=ssl_decision_state)
    mock_fetch_parse.assert_called_once_with(test_url, mock_driver)
    mock_extract_page_slug.assert_called_once_with(test_url)
    mock_extract_meta_title.assert_called_once_with(mock_sample_soup)
    # Add assert_called_once for all other mocked functions...


# ========================================
# Function: test_extract_metadata_head_request_fails
# Description: Tests scenario where the initial HEAD request fails.
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html') # Should not be called
@patch('src.orchestrator.extract_page_slug') # Might still be called
def test_extract_metadata_head_request_fails(mock_extract_slug, mock_fetch_parse, mock_fetch_status):
    """Tests that parsing is skipped if the HEAD request fails."""
    test_url = "https://bad.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    # Simulate HEAD request failure
    mock_fetch_status.return_value = (None, "Connection Error")
    mock_extract_slug.return_value = "bad_page" # Slug extraction might still work

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["http-code"] is None
    assert result["IA error"] == "Connection Error"
    assert result["page-slug"] == "bad_page" # Check slug was extracted
    # Check that HTML fetch/parse was NOT called
    mock_fetch_parse.assert_not_called()
    # Check other fields are likely defaults (e.g., empty strings or None)
    assert result["Title"] == ""


# ========================================
# Function: test_extract_metadata_non_html
# Description: Tests scenario where content type is not HTML.
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html') # Should not be called
@patch('src.orchestrator.extract_page_slug')
def test_extract_metadata_non_html(mock_extract_slug, mock_fetch_parse, mock_fetch_status):
    """Tests that parsing is skipped for non-HTML content types."""
    test_url = "https://image.example.com/logo.png"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    # Simulate successful HEAD but non-HTML type
    mock_fetch_status.return_value = (200, "image/png")
    mock_extract_slug.return_value = "logo.png"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["http-code"] == 200
    assert result["http-type"] == "image/png"
    assert result["IA error"] == "Non-HTML content (image/png)"
    assert result["page-slug"] == "logo.png"
    mock_fetch_parse.assert_not_called()
    assert result["Title"] == "" # Other fields remain default


# ========================================
# Function: test_extract_metadata_selenium_fails
# Description: Tests scenario where Selenium fetch/parse fails.
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html') # Mock this to return None
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.extract_meta_title') # Should not be called
def test_extract_metadata_selenium_fails(mock_extract_title, mock_extract_slug, mock_fetch_parse, mock_fetch_status):
    """Tests error handling when fetch_and_parse_html returns None."""
    test_url = "https://broken.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    # Simulate successful HEAD, but failed Selenium parse
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = None # Simulate failure
    mock_extract_slug.return_value = "broken_page"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["http-code"] == 200
    assert result["http-type"] == "text/html"
    assert result["IA error"] == "Failed to fetch/parse HTML (Selenium)"
    assert result["page-slug"] == "broken_page"
    mock_fetch_parse.assert_called_once_with(test_url, mock_driver)
    # Ensure subsequent parsing functions were not called
    mock_extract_title.assert_not_called()
    assert result["Title"] == "" # Other fields remain default