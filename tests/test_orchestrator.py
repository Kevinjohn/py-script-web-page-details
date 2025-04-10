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
# (Keep this test as it was in the last correct version)
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
def test_extract_metadata_success_flow(
    mock_no_scope_handler, mock_find_scope, mock_extract_body_class,
    mock_count_images_no_alt, mock_count_links, mock_count_tags, mock_extract_h1,
    mock_extract_meta_content, mock_extract_meta_title, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests the normal successful flow when a content scope is found."""
    # --- Mock Setup ---
    test_url = "https://good.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = create_mock_soup()
    found_scope_selector = "main"
    test_settings = create_test_settings(wait_after_load_seconds=1) # Example wait
    wait_seconds = test_settings["wait_after_load_seconds"]
    scope_priority = test_settings["scope_selectors_priority"]
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_find_scope.return_value = found_scope_selector
    mock_extract_page_slug.return_value = "good_slug"
    mock_extract_meta_title.return_value = "Good Title"
    mock_extract_meta_content.side_effect = ["Desc", "Keys", "website", "img.jpg", "OG Title", "OG Desc"]
    mock_extract_h1.return_value = "Good H1"
    mock_count_tags.side_effect = [5, 10] # Headings, Images
    mock_count_links.side_effect = [3, 2] # Internal, External
    mock_count_images_no_alt.return_value = 1
    mock_extract_body_class.side_effect = ["page-1", "parent-0"]

    # --- Call function ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    # --- Assertions ---
    assert result["IA error"] == ""
    assert result["Article H1"] == "Good H1"
    assert result["Article Headings"] == 5
    assert result["Article Images"] == 10
    assert result["Article Links Internal"] == 3
    assert result["Article Links External"] == 2
    assert result["Article Images NoAlt"] == 1
    # ... check other fields ...
    mock_no_scope_handler.assert_not_called()
    mock_find_scope.assert_called_once_with(mock_soup, priority_list=scope_priority)
    mock_extract_h1.assert_called_once_with(mock_soup, scope_selector=found_scope_selector)
    # ... check other calls ...


# ========================================
# Test: No Content Scope Found (Corrected Logic)
# ========================================
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
def test_extract_metadata_no_scope_found(
    mock_no_scope_handler, mock_find_scope, mock_extract_body_class,
    mock_count_images_no_alt, mock_count_links, mock_count_tags, mock_extract_h1,
    mock_extract_meta_content, mock_extract_meta_title, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests behavior when find_content_scope returns None, using body fallback."""
    # --- Mock Setup ---
    test_url = "https://no-scope.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = create_mock_soup()
    test_settings = create_test_settings()
    scope_priority = test_settings["scope_selectors_priority"]
    wait_seconds = test_settings["wait_after_load_seconds"]

    # Configure ALL mocks BEFORE the single call
    mock_find_scope.return_value = None # Simulate no scope found
    mock_no_scope_handler.return_value = "body" # Fallback returns "body" selector
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_extract_page_slug.return_value = "no_scope_slug"
    mock_extract_meta_title.return_value = "No Scope Title"
    mock_extract_meta_content.side_effect = ["Desc", "Keys", "website", "img.jpg", "OG Title", "OG Desc"] # Full side effect list
    mock_extract_body_class.side_effect = ["page-2", "parent-1"]
    # Configure mocks for parser functions being called with "body" scope
    mock_extract_h1.return_value = "Body H1?"
    mock_count_tags.side_effect = [99, 66] # Headings, Images
    mock_count_links.side_effect = [88, 55] # Internal, External
    mock_count_images_no_alt.return_value = 77

    # --- Call function ONCE ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    # --- Assertions ---
    assert "No primary semantic tag found; analysis performed on <body>" in result["IA error"]
    assert result["Title"] == "No Scope Title"
    # Check scoped fields have values returned by mocks called with "body"
    assert result["Article H1"] == "Body H1?"
    assert result["Article Headings"] == 99
    assert result["Article Links Internal"] == 88
    assert result["Article Links External"] == 55
    assert result["Article Images"] == 66
    assert result["Article Images NoAlt"] == 77

    # Check calls
    mock_fetch_status.assert_called_once()
    mock_fetch_parse.assert_called_once_with(test_url, mock_driver, wait_after_load=wait_seconds)
    mock_find_scope.assert_called_once_with(mock_soup, priority_list=scope_priority)
    mock_no_scope_handler.assert_called_once_with(test_url)
    # Check scoped parsers WERE called, with scope_selector="body"
    mock_extract_h1.assert_called_once_with(mock_soup, scope_selector="body")
    mock_count_tags.assert_any_call(mock_soup, ["h1", "h2", "h3", "h4", "h5", "h6"], scope_selector="body")
    mock_count_tags.assert_any_call(mock_soup, ["img"], scope_selector="body")
    mock_count_links.assert_any_call(mock_soup, test_url, internal=True, scope_selector="body")
    mock_count_links.assert_any_call(mock_soup, test_url, internal=False, scope_selector="body")
    mock_count_images_no_alt.assert_called_once_with(mock_soup, scope_selector="body")
    assert mock_extract_meta_content.call_count == 6 # Ensure meta content mock was fully used


# ========================================
# Test: HEAD Request Fails (Check mocks)
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
def test_extract_metadata_head_fails(
    mock_no_scope_handler, mock_find_scope, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    # ... (rest of test unchanged, passes settings) ...
    test_url = "https://timeout.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    test_settings = create_test_settings()
    mock_fetch_status.return_value = (None, "Timeout Error")
    mock_extract_page_slug.return_value = "timeout_slug"
    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)
    assert result["http-code"] is None
    assert result["IA error"] == "Timeout Error"
    mock_fetch_parse.assert_not_called()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: Non-HTML Content Type (Check mocks)
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
def test_extract_metadata_non_html(
    mock_no_scope_handler, mock_find_scope, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    # ... (rest of test unchanged, passes settings) ...
    test_url = "https://image.example.com/logo.jpg"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    test_settings = create_test_settings()
    mock_fetch_status.return_value = (200, "image/jpeg")
    mock_extract_page_slug.return_value = "logo.jpg"
    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)
    assert result["IA error"] == "Non-HTML content (image/jpeg)"
    mock_fetch_parse.assert_not_called()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: Selenium Fetch/Parse Fails (Check mocks)
# ========================================
@patch('src.orchestrator.fetch_http_status_and_type')
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')
@patch('src.orchestrator.extract_meta_title')
@patch('src.orchestrator.extract_meta_content')
@patch('src.orchestrator.extract_body_class')
@patch('src.orchestrator.find_content_scope')
@patch('src.orchestrator.no_semantic_base_html_tag')
@patch('src.orchestrator.extract_placeholder_data') # Added placeholder mock
def test_extract_metadata_selenium_fails(
    mock_extract_placeholder, # Added arg
    mock_no_scope_handler, mock_find_scope, mock_extract_body_class,
    mock_extract_meta_content, mock_extract_meta_title, mock_extract_page_slug,
    mock_fetch_parse, mock_fetch_status
    ):
    """Tests behavior when Selenium fetch/parse returns None."""
    # ... (rest of test setup unchanged, passes settings) ...
    test_url = "https://broken.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    test_settings = create_test_settings()
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = None
    mock_extract_page_slug.return_value = "broken_slug"

    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    assert result["IA error"] == "Failed to fetch/parse HTML (Selenium)"
    mock_fetch_parse.assert_called_once()
    mock_extract_meta_title.assert_not_called()
    mock_extract_meta_content.assert_not_called()
    mock_extract_body_class.assert_not_called()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()
    mock_extract_placeholder.assert_not_called()