# tests/test_orchestrator.py
import pytest
from unittest.mock import patch, MagicMock, call
from bs4 import BeautifulSoup

# Import the function to test
from src.orchestrator import extract_metadata
# Import DEFAULT_SETTINGS to use for creating test settings dict
from src.config_loader import DEFAULT_SETTINGS

# Define standard expected keys
EXPECTED_KEYS = [
    "http-code", "http-type", "Page-URL", "page-slug", "Page-id", "Parent-ID",
    "Title", "Description", "Keywords", "Opengraph type", "Opengraph image",
    "Opengraph title", "Opengraph description", "Article H1", "Article Headings",
    "Article Links Internal", "Article Links External", "Article Images",
    "Article Images NoAlt", "content-count", "content-ratio", "Parent-URL", "IA error",
]

# --- Helper Function to Create Mock Soup ---
def create_mock_soup():
    return MagicMock(spec=BeautifulSoup)

# --- Helper to create default test settings ---
def create_test_settings(**overrides):
    """Creates a settings dict based on defaults, allowing overrides."""
    settings = DEFAULT_SETTINGS.copy()
    settings.update(overrides)
    return settings

# ========================================
# Test: Happy Path Success Flow (with scope found)
# ========================================
# (No changes needed in this test's logic from previous version)
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.extract_meta_title')
@patch('src.orchestrator.extract_meta_content')
@patch('src.orchestrator.extract_h1')
@patch('src.orchestrator.count_tags')
@patch('src.orchestrator.count_links')
@patch('src.orchestrator.count_images_no_alt')
@patch('src.orchestrator.extract_body_class')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
@patch('src.orchestrator.extract_placeholder_data') # Added placeholder mock
def test_extract_metadata_success_flow(
    mock_extract_placeholder, # Added arg
    mock_no_scope_handler, mock_find_scope, mock_extract_body_class,
    mock_count_images_no_alt, mock_count_links, mock_count_tags, mock_extract_h1,
    mock_extract_meta_content, mock_extract_meta_title, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests the normal successful flow when a content scope is found."""
    # --- Setup ---
    test_url = "https://good.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = create_mock_soup()
    found_scope_selector = "main"
    test_settings = create_test_settings(wait_after_load_seconds=1)
    wait_seconds = test_settings["wait_after_load_seconds"]
    scope_priority = test_settings["scope_selectors_priority"]
    # Configure mocks for success path
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_find_scope.return_value = found_scope_selector
    mock_extract_page_slug.return_value = "good_slug"
    mock_extract_meta_title.return_value = "Good Title"
    # ... configure other mocks ...
    mock_extract_meta_content.side_effect = ["Desc", "Keys", "website", "img.jpg", "OG Title", "OG Desc"]
    mock_extract_h1.return_value = "Good H1"
    mock_count_tags.side_effect = [5, 10]
    mock_count_links.side_effect = [3, 2]
    mock_count_images_no_alt.return_value = 1
    mock_extract_body_class.side_effect = ["page-1", "parent-0"]
    mock_extract_placeholder.return_value = None # For content-count/ratio

    # --- Call ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    # --- Assert ---
    assert result["http-code"] == 200
    assert result["IA error"] == ""
    assert result["Article H1"] == "Good H1"
    # ... (check other results) ...
    mock_fetch_parse.assert_called_once_with(test_url, mock_driver, wait_after_load=wait_seconds)
    mock_find_scope.assert_called_once_with(mock_soup, priority_list=scope_priority)
    mock_extract_h1.assert_called_once_with(mock_soup, scope_selector=found_scope_selector)
    assert mock_extract_placeholder.call_count == 2 # Called twice
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: No Content Scope Found (Using Body Fallback)
# ========================================
# (No changes needed in this test's logic from previous version)
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.extract_meta_title')
@patch('src.orchestrator.extract_meta_content')
@patch('src.orchestrator.extract_h1')
@patch('src.orchestrator.count_tags')
@patch('src.orchestrator.count_links')
@patch('src.orchestrator.count_images_no_alt')
@patch('src.orchestrator.extract_body_class')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
@patch('src.orchestrator.extract_placeholder_data') # Added placeholder mock
def test_extract_metadata_no_scope_found(
    mock_extract_placeholder, # Added arg
    mock_no_scope_handler, mock_find_scope, mock_extract_body_class,
    mock_count_images_no_alt, mock_count_links, mock_count_tags, mock_extract_h1,
    mock_extract_meta_content, mock_extract_meta_title, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests behavior when find_content_scope returns None, using body fallback."""
    # --- Setup ---
    test_url = "https://no-scope.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = create_mock_soup()
    test_settings = create_test_settings()
    scope_priority = test_settings["scope_selectors_priority"]
    wait_seconds = test_settings["wait_after_load_seconds"]
    # Configure mocks for this path
    mock_find_scope.return_value = None # No scope found
    mock_no_scope_handler.return_value = "body" # Fallback returns "body"
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_extract_page_slug.return_value = "no_scope_slug"
    mock_extract_meta_title.return_value = "No Scope Title"
    mock_extract_meta_content.side_effect = ["Desc", "Keys", "website", "img.jpg", "OG Title", "OG Desc"]
    mock_extract_body_class.side_effect = ["page-2", "parent-1"]
    mock_extract_h1.return_value = "Body H1?" # Dummy values for body scope call
    mock_count_tags.side_effect = [99, 66]
    mock_count_links.side_effect = [88, 55]
    mock_count_images_no_alt.return_value = 77
    mock_extract_placeholder.return_value = None

    # --- Call ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    # --- Assert ---
    assert "No primary semantic tag found; analysis performed on <body>" in result["IA error"]
    assert result["Title"] == "No Scope Title"
    assert result["Article H1"] == "Body H1?"
    assert result["Article Headings"] == 99
    # ... (check other results) ...
    mock_find_scope.assert_called_once_with(mock_soup, priority_list=scope_priority)
    mock_no_scope_handler.assert_called_once_with(test_url)
    # Check parsers WERE called with "body" scope
    mock_extract_h1.assert_called_once_with(mock_soup, scope_selector="body")
    mock_count_tags.assert_any_call(mock_soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector="body")
    # ... (check other parser calls with scope="body") ...
    assert mock_extract_placeholder.call_count == 2


# ========================================
# Test: HEAD Request Fails (Fundamental failure, code is None)
# ========================================
# (No changes needed in this test's logic from previous version)
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
def test_extract_metadata_head_fails(
    mock_no_scope_handler, mock_find_scope, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests behavior when the initial HEAD request fails before getting status (code=None)."""
    test_url = "https://timeout.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    test_settings = create_test_settings()
    mock_fetch_status.return_value = (None, "Timeout Error") # Code is None
    mock_extract_page_slug.return_value = "timeout_slug"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    assert result["http-code"] is None
    assert result["http-type"] == "Timeout Error"
    assert result["IA error"] == "Timeout Error"
    mock_fetch_parse.assert_not_called()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: Non-HTML Content Type
# ========================================
# (No changes needed in this test's logic from previous version)
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
def test_extract_metadata_non_html(
    mock_no_scope_handler, mock_find_scope, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests behavior for non-HTML content types."""
    test_url = "https://image.example.com/logo.jpg"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    test_settings = create_test_settings()
    mock_fetch_status.return_value = (200, "image/jpeg") # Non-HTML type
    mock_extract_page_slug.return_value = "logo.jpg"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    assert result["http-code"] == 200
    assert result["http-type"] == "image/jpeg"
    assert result["IA error"] == "Non-HTML content (image/jpeg)"
    mock_fetch_parse.assert_not_called()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: Selenium Fetch/Parse Fails
# ========================================
# (No changes needed in this test's logic from previous version)
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.extract_meta_title')
@patch('src.orchestrator.extract_meta_content')
@patch('src.orchestrator.extract_body_class')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
@patch('src.orchestrator.extract_placeholder_data')
def test_extract_metadata_selenium_fails(
    mock_extract_placeholder, mock_no_scope_handler, mock_find_scope,
    mock_extract_body_class, mock_extract_meta_content, mock_extract_meta_title,
    mock_extract_page_slug, mock_fetch_parse, mock_fetch_status
    ):
    """Tests behavior when Selenium fetch/parse returns None."""
    test_url = "https://broken.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    test_settings = create_test_settings()
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = None # Simulate failure
    mock_extract_page_slug.return_value = "broken_slug"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    assert result["IA error"] == "Failed to fetch/parse HTML (Selenium)"
    assert result["http-code"] == 200 # Check previous steps succeeded
    assert result["http-type"] == "text/html"
    mock_fetch_parse.assert_called_once()
    # Ensure parsing functions *after* fetch were not called
    mock_extract_meta_title.assert_not_called()
    mock_extract_meta_content.assert_not_called()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: HTTP Error Code Received (NEW Test)
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
def test_extract_metadata_http_error_no_parse(
    mock_no_scope_handler, mock_find_scope, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests behavior when HEAD request returns an HTTP error code (e.g., 404)."""
    test_url = "https://notfound.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    test_settings = create_test_settings()

    # Simulate fetch function returning HTTP error code and error message type
    mock_fetch_status.return_value = (404, "Request Error (HTTPError)")
    mock_extract_page_slug.return_value = "notfound_slug"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    # Check HTTP info is recorded
    assert result["http-code"] == 404
    assert result["http-type"] == "Request Error (HTTPError)"
    # Check IA error is set based on the error type string
    assert result["IA error"] == "Request Error (HTTPError)"
    # Check page slug still extracted
    assert result["page-slug"] == "notfound_slug"
    # Check that Selenium/parsing was NOT attempted
    mock_fetch_parse.assert_not_called()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()