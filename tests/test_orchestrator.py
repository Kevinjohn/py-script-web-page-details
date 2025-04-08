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
# Decorators applied bottom-up. Arguments passed inner-first (left-to-right).
# Corrected patch targets to point to names *within* src.orchestrator's namespace
@patch('src.orchestrator.fetch_http_status_and_type')         # 12th (Last arg)
@patch('src.orchestrator.fetch_and_parse_html')            # 11th
@patch('src.orchestrator.extract_page_slug')               # 10th << CORRECTED TARGET
@patch('src.orchestrator.extract_meta_title')              # 9th  << CORRECTED TARGET
@patch('src.orchestrator.extract_meta_content')            # 8th  << CORRECTED TARGET
@patch('src.orchestrator.extract_h1')                      # 7th  << CORRECTED TARGET
@patch('src.orchestrator.count_tags')                      # 6th  << CORRECTED TARGET
@patch('src.orchestrator.count_links')                     # 5th  << CORRECTED TARGET
@patch('src.orchestrator.count_images_no_alt')             # 4th  << CORRECTED TARGET
@patch('src.orchestrator.extract_body_class')              # 3rd  << CORRECTED TARGET
@patch('src.orchestrator.find_content_scope')              # 2nd  << CORRECTED TARGET
@patch('src.orchestrator.no_semantic_base_html_tag')       # 1st (Innermost, First arg) << CORRECTED TARGET
def test_extract_metadata_success_flow(
    mock_no_scope_handler,      # 1
    mock_find_scope,            # 2
    mock_extract_body_class,    # 3
    mock_count_images_no_alt,   # 4
    mock_count_links,           # 5
    mock_count_tags,            # 6
    mock_extract_h1,            # 7
    mock_extract_meta_content,  # 8
    mock_extract_meta_title,    # 9
    mock_extract_page_slug,     # 10 - Argument name matches function name
    mock_fetch_parse,           # 11
    mock_fetch_status           # 12 - Argument order correct
    ):
    """Tests the normal successful flow when a content scope is found."""
    # --- Mock Setup ---
    test_url = "https://good.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = create_mock_soup()
    found_scope_selector = "main"
    test_settings = create_test_settings(
        wait_after_load_seconds=1,
        scope_selectors_priority=["main", "article"]
    )
    wait_seconds = test_settings["wait_after_load_seconds"]
    scope_priority = test_settings["scope_selectors_priority"]

    # Configure mocks
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_find_scope.return_value = found_scope_selector
    mock_extract_page_slug.return_value = "good_slug"
    mock_extract_meta_title.return_value = "Good Title"
    mock_extract_meta_content.side_effect = ["Desc", "Keys", "website", "img.jpg", "OG Title", "OG Desc"]
    mock_extract_h1.return_value = "Good H1"
    mock_count_tags.side_effect = [5, 10]
    mock_count_links.side_effect = [3, 2]
    mock_count_images_no_alt.return_value = 1
    mock_extract_body_class.side_effect = ["page-1", "parent-0"]

    # --- Call function ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    # --- Assertions ---
    assert result["IA error"] == ""
    assert result["Article H1"] == "Good H1"
    # ... (check other fields) ...

    # Check calls
    mock_fetch_status.assert_called_once()
    mock_fetch_parse.assert_called_once_with(test_url, mock_driver, wait_after_load=wait_seconds)
    mock_find_scope.assert_called_once_with(mock_soup, priority_list=scope_priority)
    mock_extract_h1.assert_called_once_with(mock_soup, scope_selector=found_scope_selector)
    # ... (check other mock calls) ...
    mock_no_scope_handler.assert_not_called()


# ========================================
# Test: No Content Scope Found
# ========================================
# Corrected patch targets
@patch('src.orchestrator.fetch_http_status_and_type')         # Last arg
@patch('src.orchestrator.fetch_and_parse_html')            # ...
@patch('src.orchestrator.extract_page_slug')               # ... << CORRECTED
@patch('src.orchestrator.extract_meta_title')              # ... << CORRECTED
@patch('src.orchestrator.extract_meta_content')            # ... << CORRECTED
@patch('src.orchestrator.extract_h1')                      # Scoped - Not called << CORRECTED
@patch('src.orchestrator.count_tags')                      # Scoped - Not called << CORRECTED
@patch('src.orchestrator.count_links')                     # Scoped - Not called << CORRECTED
@patch('src.orchestrator.count_images_no_alt')             # Scoped - Not called << CORRECTED
@patch('src.orchestrator.extract_body_class')              # << CORRECTED
@patch('src.orchestrator.find_content_scope')              # << CORRECTED
@patch('src.orchestrator.no_semantic_base_html_tag')       # Innermost -> first arg << CORRECTED
def test_extract_metadata_no_scope_found(
    mock_no_scope_handler,      # 1
    mock_find_scope,            # 2
    mock_extract_body_class,    # 3
    mock_count_images_no_alt,   # 4
    mock_count_links,           # 5
    mock_count_tags,            # 6
    mock_extract_h1,            # 7
    mock_extract_meta_content,  # 8
    mock_extract_meta_title,    # 9
    mock_extract_page_slug,     # 10 - Arg name and order correct
    mock_fetch_parse,           # 11
    mock_fetch_status           # 12 - Arg name and order correct
    ):
    """Tests behavior when find_content_scope returns None."""
    # --- Mock Setup ---
    test_url = "https://no-scope.example.com"
    mock_driver = MagicMock()
    ssl_decision_state = {}
    mock_soup = create_mock_soup()
    test_settings = create_test_settings()
    scope_priority = test_settings["scope_selectors_priority"]
    wait_seconds = test_settings["wait_after_load_seconds"]
    mock_find_scope.return_value = None # Simulate no scope found
    fallback_data = {
        "Article H1": "FB_H1", "Article Headings": -1,
        "IA error": "No primary semantic content tag found (...)"
    }
    mock_no_scope_handler.return_value = fallback_data
    mock_fetch_status.return_value = (200, "text/html")
    mock_fetch_parse.return_value = mock_soup
    mock_extract_page_slug.return_value = "no_scope_slug"
    mock_extract_meta_title.return_value = "No Scope Title"
    mock_extract_meta_content.side_effect = ["Desc", "Keys", "website", "img.jpg", "OG Title", "OG Desc"]
    mock_extract_body_class.side_effect = ["page-2", "parent-1"]

    # --- Call function ---
    result = extract_metadata(test_url, mock_driver, ssl_decision_state, settings=test_settings)

    # --- Assertions ---
    assert result["IA error"] == fallback_data["IA error"]
    assert result["Article H1"] == fallback_data["Article H1"]
    assert result["Title"] == "No Scope Title"

    # Check calls
    mock_fetch_status.assert_called_once()
    mock_fetch_parse.assert_called_once_with(test_url, mock_driver, wait_after_load=wait_seconds)
    mock_find_scope.assert_called_once_with(mock_soup, priority_list=scope_priority)
    mock_no_scope_handler.assert_called_once_with(test_url)
    # Check scoped parsers NOT called
    mock_extract_h1.assert_not_called()
    mock_count_tags.assert_not_called()
    mock_count_links.assert_not_called()
    mock_count_images_no_alt.assert_not_called()


# ========================================
# Test: HEAD Request Fails (Updated)
# ========================================
# Corrected patch targets
@patch('src.orchestrator.fetch_http_status_and_type') # Outermost -> last arg
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')        # << CORRECTED
@patch('src.orchestrator.find_content_scope')       # << CORRECTED
@patch('src.orchestrator.no_semantic_base_html_tag')# Innermost -> first arg << CORRECTED
def test_extract_metadata_head_fails(
    mock_no_scope_handler,      # 1
    mock_find_scope,            # 2
    mock_extract_page_slug,     # 3 - Corrected name & order
    mock_fetch_parse,           # 4
    mock_fetch_status           # 5 - Corrected order
    ):
    """Tests behavior when the initial HEAD request fails."""
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
# Test: Non-HTML Content Type (Updated)
# ========================================
# Corrected patch targets
@patch('src.orchestrator.fetch_http_status_and_type') # Outermost -> last arg
@patch('src.orchestrator.fetch_and_parse_html')
@patch('src.orchestrator.extract_page_slug')        # << CORRECTED
@patch('src.orchestrator.find_content_scope')       # << CORRECTED
@patch('src.orchestrator.no_semantic_base_html_tag')# Innermost -> first arg << CORRECTED
def test_extract_metadata_non_html(
    mock_no_scope_handler,      # 1
    mock_find_scope,            # 2
    mock_extract_page_slug,     # 3 - Corrected name & order
    mock_fetch_parse,           # 4
    mock_fetch_status           # 5 - Corrected order
    ):
    """Tests behavior for non-HTML content types."""
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
# Test: Selenium Fetch/Parse Fails (Updated)
# ========================================
# Corrected patch targets
@patch('src.orchestrator.fetch_http_status_and_type')     # Outermost -> last arg
@patch('src.orchestrator.fetch_and_parse_html')        # ...
@patch('src.orchestrator.extract_page_slug')           # ... << CORRECTED
@patch('src.orchestrator.extract_meta_title')          # ... << CORRECTED
@patch('src.orchestrator.extract_meta_content')        # ... << CORRECTED
@patch('src.orchestrator.extract_body_class')          # ... << CORRECTED
@patch('src.orchestrator.find_content_scope')          # ... << CORRECTED
@patch('src.orchestrator.no_semantic_base_html_tag')   # Innermost -> first arg << CORRECTED
def test_extract_metadata_selenium_fails(
    mock_no_scope_handler,      # 1
    mock_find_scope,            # 2
    mock_extract_body_class,    # 3
    mock_extract_meta_content,  # 4
    mock_extract_meta_title,    # 5 - Arg name and order correct
    mock_extract_page_slug,     # 6 - Arg name and order correct
    mock_fetch_parse,           # 7
    mock_fetch_status           # 8 - Arg name and order correct
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
    mock_fetch_parse.assert_called_once()
    mock_find_scope.assert_not_called()
    mock_no_scope_handler.assert_not_called()
    mock_extract_meta_title.assert_not_called()
    mock_extract_meta_content.assert_not_called()
    mock_extract_body_class.assert_not_called()