# tests/test_orchestrator.py
import pytest
from unittest.mock import patch, MagicMock, call # Import call
from bs4 import BeautifulSoup

# Import the function to test
from src.orchestrator import extract_metadata

# Define standard expected keys for easier assertion checks
EXPECTED_KEYS = [
    "http-code", "http-type", "Page-URL", "page-slug", "Page-id", "Parent-ID",
    "Title", "Description", "Keywords", "Opengraph type", "Opengraph image",
    "Opengraph title", "Opengraph description", "Article H1", "Article Headings",
    "Article Links Internal", "Article Links External", "Article Images",
    "Article Images NoAlt", "content-count", "content-ratio", "Parent-URL", "IA error",
]

# --- Helper Function to Create Mock Soup ---
def create_mock_soup():
    # Creates a basic mock soup object for tests where its content doesn't matter
    return MagicMock(spec=BeautifulSoup)

# ========================================
# Test: Happy Path Success Flow (with scope found)
# ========================================
# Patch ALL dependencies called by extract_metadata
# Need to add find_content_scope and no_semantic_base_html_tag
@patch('src.orchestrator.no_semantic_base_html_tag') # Added
@patch('src.orchestrator.find_content_scope')      # Added
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
    mock_count_images_no_alt, mock_extract_body_class,
    mock_find_scope, mock_no_scope_handler # Added mock arguments
    ):
    """Tests the normal successful flow when a content scope is found."""
    # --- Mock Setup ---
    test_url = "https://good.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = create_mock_soup()
    found_scope_selector = "main" # Simulate finding the <main> tag

    # Configure return values
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_find_scope.return_value = found_scope_selector # Simulate scope found
    mock_extract_page_slug.return_value = "good_slug"
    mock_extract_meta_title.return_value = "Good Title"
    mock_extract_meta_content.side_effect = ["Desc", "Keys", "website", "img.jpg", "OG Title", "OG Desc"]
    mock_extract_h1.return_value = "Good H1"
    mock_count_tags.side_effect = [5, 10] # Headings, Images
    mock_count_links.side_effect = [3, 2] # Internal, External
    mock_count_images_no_alt.return_value = 1
    mock_extract_body_class.side_effect = ["page-1", "parent-0"]

    # --- Call function ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    # --- Assertions ---
    assert result["IA error"] == ""
    assert result["page-slug"] == "good_slug"
    assert result["Title"] == "Good Title"
    assert result["Description"] == "Desc"
    # ... (check other non-scoped fields) ...
    assert result["Article H1"] == "Good H1"
    assert result["Article Headings"] == 5
    assert result["Article Links Internal"] == 3
    assert result["Article Images"] == 10
    assert result["Article Images NoAlt"] == 1
    assert result["Page-id"] == "page-1"

    # Check calls
    mock_fetch_status.assert_called_once()
    mock_fetch_parse.assert_called_once()
    mock_find_scope.assert_called_once_with(mock_soup)
    # Check that parser functions were called with the found scope selector
    mock_extract_h1.assert_called_once_with(mock_soup, scope_selector=found_scope_selector)
    mock_count_tags.assert_has_calls([
        call(mock_soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector=found_scope_selector),
        call(mock_soup, ["img"], scope_selector=found_scope_selector)
    ], any_order=False) # Check calls with specific args
    mock_count_links.assert_has_calls([
        call(mock_soup, test_url, internal=True, scope_selector=found_scope_selector),
        call(mock_soup, test_url, internal=False, scope_selector=found_scope_selector)
    ], any_order=False)
    mock_count_images_no_alt.assert_called_once_with(mock_soup, scope_selector=found_scope_selector)
    # Check the fallback handler was NOT called
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: No Content Scope Found
# ========================================
# Patch all dependencies
@patch('src.orchestrator.no_semantic_base_html_tag') # Added
@patch('src.orchestrator.find_content_scope')      # Added
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
def test_extract_metadata_no_scope_found(
    mock_fetch_status, mock_fetch_parse, mock_extract_page_slug, mock_extract_meta_title,
    mock_extract_meta_content, mock_extract_h1, mock_count_tags, mock_count_links,
    mock_count_images_no_alt, mock_extract_body_class,
    mock_find_scope, mock_no_scope_handler # Added mock arguments
    ):
    """Tests behavior when find_content_scope returns None."""
    # --- Mock Setup ---
    test_url = "https://no-scope.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = create_mock_soup()
    # Simulate no scope being found
    mock_find_scope.return_value = None
    # Define what the no_scope_handler should return (matching its actual signature)
    fallback_data = {
        "Article H1": "", "Article Headings": 0, "Article Links Internal": 0,
        "Article Links External": 0, "Article Images": 0, "Article Images NoAlt": 0,
        "IA error": "No primary semantic content tag found (...)" # Use specific message
    }
    mock_no_scope_handler.return_value = fallback_data

    # Configure other mocks needed to reach the scope finding stage
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_extract_page_slug.return_value = "no_scope_slug"
    mock_extract_meta_title.return_value = "No Scope Title"
    mock_extract_meta_content.side_effect = ["Desc", "Keys", "website", "img.jpg", "OG Title", "OG Desc"]
    mock_extract_body_class.side_effect = ["page-2", "parent-1"]

    # --- Call function ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    # --- Assertions ---
    assert result is not None
    assert list(result.keys()) == EXPECTED_KEYS
    # Check non-scoped fields were still populated
    assert result["Title"] == "No Scope Title"
    assert result["Page-id"] == "page-2"
    # Check that scoped fields match the fallback data
    assert result["IA error"] == fallback_data["IA error"]
    assert result["Article H1"] == fallback_data["Article H1"]
    assert result["Article Headings"] == fallback_data["Article Headings"]
    assert result["Article Links Internal"] == fallback_data["Article Links Internal"]
    assert result["Article Links External"] == fallback_data["Article Links External"]
    assert result["Article Images"] == fallback_data["Article Images"]
    assert result["Article Images NoAlt"] == fallback_data["Article Images NoAlt"]

    # Check calls
    mock_fetch_status.assert_called_once()
    mock_fetch_parse.assert_called_once()
    mock_find_scope.assert_called_once_with(mock_soup)
    # Check the fallback handler WAS called
    mock_no_scope_handler.assert_called_once_with(test_url)
    # Check that scoped parsers were NOT called
    mock_extract_h1.assert_not_called()
    mock_count_tags.assert_not_called()
    mock_count_links.assert_not_called()
    mock_count_images_no_alt.assert_not_called()


# ========================================
# Test: HEAD Request Fails (Updated)
# ========================================
# Need to add new mocks to patch list, even if not used in this path
@patch('src.orchestrator.no_semantic_base_html_tag') # Added
@patch('src.orchestrator.find_content_scope')      # Added
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
def test_extract_metadata_head_fails(
    mock_extract_slug, mock_fetch_parse, mock_fetch_status,
    mock_find_scope, mock_no_scope_handler # Add new mocks to signature
    ):
    """Tests behavior when the initial HEAD request fails."""
    test_url = "https://timeout.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    mock_fetch_status.return_value = (None, "Timeout Error")
    mock_extract_slug.return_value = "timeout_slug"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["http-code"] is None
    assert result["IA error"] == "Timeout Error"
    assert result["page-slug"] == "timeout_slug"
    mock_fetch_parse.assert_not_called()
    mock_find_scope.assert_not_called() # Ensure scope finding not reached
    mock_no_scope_handler.assert_not_called() # Ensure handler not reached


# ========================================
# Test: Non-HTML Content Type (Updated)
# ========================================
@patch('src.orchestrator.no_semantic_base_html_tag') # Added
@patch('src.orchestrator.find_content_scope')      # Added
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
def test_extract_metadata_non_html(
    mock_extract_slug, mock_fetch_parse, mock_fetch_status,
    mock_find_scope, mock_no_scope_handler # Add new mocks to signature
    ):
    """Tests behavior for non-HTML content types."""
    test_url = "https://image.example.com/logo.jpg"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    mock_fetch_status.return_value = (200, "image/jpeg")
    mock_extract_slug.return_value = "logo.jpg"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["http-code"] == 200
    assert result["IA error"] == "Non-HTML content (image/jpeg)"
    assert result["page-slug"] == "logo.jpg"
    mock_fetch_parse.assert_not_called()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: Selenium Fetch/Parse Fails (Updated)
# ========================================
@patch('src.orchestrator.no_semantic_base_html_tag') # Added
@patch('src.orchestrator.find_content_scope')      # Added
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.extract_meta_title') # Keep this mock as it's called before scope finding
def test_extract_metadata_selenium_fails(
    mock_extract_title, mock_extract_slug, mock_fetch_parse, mock_fetch_status,
    mock_find_scope, mock_no_scope_handler # Add new mocks to signature
    ):
    """Tests behavior when Selenium fetch/parse returns None."""
    test_url = "https://broken.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}

    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = None # Simulate failure
    mock_extract_slug.return_value = "broken_slug"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state)

    assert result["IA error"] == "Failed to fetch/parse HTML (Selenium)"
    assert result["page-slug"] == "broken_slug"
    mock_fetch_parse.assert_called_once()
    mock_find_scope.assert_not_called() # Should not be called if soup is None
    mock_no_scope_handler.assert_not_called()
    mock_extract_title.assert_not_called() # Should not be called if soup is None