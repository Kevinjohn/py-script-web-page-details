# tests/test_orchestrator.py
import pytest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup # Import for type hinting if needed, not strictly necessary for mocks

# Import the function to test
from src.orchestrator import extract_metadata

# Define standard expected keys for easier assertion checks
# Should match the keys initialized in extract_metadata
EXPECTED_KEYS = [
    "http-code", "http-type", "Page-URL", "page-slug", "Page-id", "Parent-ID",
    "Title", "Description", "Keywords", "Opengraph type", "Opengraph image",
    "Opengraph title", "Opengraph description", "Article H1", "Article Headings",
    "Article Links Internal", "Article Links External", "Article Images",
    "Article Images NoAlt", "content-count", "content-ratio", "Parent-URL", "IA error",
]

# ========================================
# Test: Happy Path Success Flow
# ========================================
# Patch all dependencies called by extract_metadata, targeting them within orchestrator's namespace
@patch('src.orchestrator.extract_body_class')
@patch('src.orchestrator.count_images_no_alt')
@patch('src.orchestrator.count_links')
@patch('src.orchestrator.count_tags')
@patch('src.orchestrator.extract_h1')
@patch('src.orchestrator.extract_meta_content')
@patch('src.orchestrator.extract_meta_title')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.fetch_http_status_and_type')
def test_extract_metadata_success_flow(
    mock_fetch_status, mock_fetch_parse, mock_extract_page_slug, mock_extract_meta_title,
    mock_extract_meta_content, mock_extract_h1, mock_count_tags, mock_count_links,
    mock_count_images_no_alt, mock_extract_body_class
    ):
    """Tests the normal successful flow of extract_metadata."""
    # --- Mock Setup ---
    test_url = "https://good.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = MagicMock(spec=BeautifulSoup) # Mock a soup object

    # Configure return values for all mocks
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_extract_page_slug.return_value = "good_slug"
    mock_extract_meta_title.return_value = "Good Title"
    # Use side_effect to return different values for different calls if needed
    mock_extract_meta_content.side_effect = ["Good Description", "Good Keywords", "website", "og_image.jpg", "OG Title", "OG Description"]
    mock_extract_h1.return_value = "Good H1"
    mock_count_tags.side_effect = [5, 10] # Example: Headings, Images
    mock_count_links.side_effect = [3, 2] # Example: Internal, External
    mock_count_images_no_alt.return_value = 1
    mock_extract_body_class.side_effect = ["page-1", "parent-0"] # Example: Page-id, Parent-ID

    # --- Call the function ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    # --- Assertions ---
    assert result is not None
    assert isinstance(result, dict)
    assert list(result.keys()) == EXPECTED_KEYS # Check all expected keys are present
    assert result["IA error"] == "" # No error on happy path
    assert result["Page-URL"] == test_url
    assert result["http-code"] == 200
    assert result["http-type"] == "text/html"
    assert result["page-slug"] == "good_slug"
    assert result["Title"] == "Good Title"
    assert result["Description"] == "Good Description"
    assert result["Keywords"] == "Good Keywords"
    assert result["Opengraph type"] == "website"
    assert result["Opengraph image"] == "og_image.jpg"
    assert result["Opengraph title"] == "OG Title"
    assert result["Opengraph description"] == "OG Description"
    assert result["Article H1"] == "Good H1"
    assert result["Article Headings"] == 5 # Corresponds to first call to count_tags
    assert result["Article Links Internal"] == 3 # Corresponds to first call to count_links
    assert result["Article Links External"] == 2 # Corresponds to second call to count_links
    assert result["Article Images"] == 10 # Corresponds to second call to count_tags
    assert result["Article Images NoAlt"] == 1
    assert result["Page-id"] == "page-1" # Corresponds to first call to extract_body_class
    assert result["Parent-ID"] == "parent-0" # Corresponds to second call to extract_body_class

    # Check dependencies were called correctly
    mock_fetch_status.assert_called_once_with(test_url, ssl_decision=ssl_decision_state)
    mock_fetch_parse.assert_called_once_with(test_url, mock_driver)
    mock_extract_page_slug.assert_called_once_with(test_url)
    mock_extract_meta_title.assert_called_once_with(mock_soup)
    assert mock_extract_meta_content.call_count == 6 # Called for desc, keywords, og:type, og:image, og:title, og:description
    mock_extract_h1.assert_called_once_with(mock_soup, scope_selector="article")
    assert mock_count_tags.call_count == 2 # Called for headings and images
    assert mock_count_links.call_count == 2 # Called for internal and external
    mock_count_images_no_alt.assert_called_once_with(mock_soup, scope_selector="article")
    assert mock_extract_body_class.call_count == 2 # Called for page-id and parent-pageid


# ========================================
# Test: HEAD Request Fails
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
def test_extract_metadata_head_fails(mock_extract_slug, mock_fetch_parse, mock_fetch_status):
    """Tests behavior when the initial HEAD request fails."""
    test_url = "https://timeout.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    mock_fetch_status.return_value = (None, "Timeout Error")
    mock_extract_slug.return_value = "timeout_slug" # Slug might still be extractable

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["http-code"] is None
    assert result["http-type"] == "Timeout Error" # Uses error message as type
    assert result["IA error"] == "Timeout Error" # Copies error here
    assert result["page-slug"] == "timeout_slug"
    # Ensure parsing functions were not called
    mock_fetch_parse.assert_not_called()
    # Check other fields are default
    assert result["Title"] == ""
    assert result["Article H1"] == ""

# ========================================
# Test: Non-HTML Content Type
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
def test_extract_metadata_non_html(mock_extract_slug, mock_fetch_parse, mock_fetch_status):
    """Tests behavior for non-HTML content types."""
    test_url = "https://image.example.com/logo.jpg"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    mock_fetch_status.return_value = (200, "image/jpeg")
    mock_extract_slug.return_value = "logo.jpg"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["http-code"] == 200
    assert result["http-type"] == "image/jpeg"
    assert result["IA error"] == "Non-HTML content (image/jpeg)"
    assert result["page-slug"] == "logo.jpg"
    mock_fetch_parse.assert_not_called()
    assert result["Title"] == ""
    assert result["Article H1"] == ""

# ========================================
# Test: Selenium Fetch/Parse Fails
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.extract_meta_title') # Should not be called
def test_extract_metadata_selenium_fails(
    mock_extract_title, mock_extract_slug, mock_fetch_parse, mock_fetch_status
    ):
    """Tests behavior when Selenium fetch/parse returns None."""
    test_url = "https://broken.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = None # Simulate failure
    mock_extract_slug.return_value = "broken_slug"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["http-code"] == 200
    assert result["http-type"] == "text/html"
    assert result["IA error"] == "Failed to fetch/parse HTML (Selenium)"
    assert result["page-slug"] == "broken_slug"
    mock_fetch_status.assert_called_once()
    mock_fetch_parse.assert_called_once_with(test_url, mock_driver)
    # Ensure HTML parsing functions were not called
    mock_extract_title.assert_not_called()
    assert result["Title"] == ""
    assert result["Article H1"] == ""