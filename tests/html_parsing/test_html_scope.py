# tests/html_parsing/test_html_scope.py
import pytest
from bs4 import BeautifulSoup
from unittest.mock import patch # Import patch for mocking logging
import logging # Import logging for verification if needed

# Import functions to test
from src.html_parsing.html_scope import find_content_scope, no_semantic_base_html_tag
# Import DEFAULT_SETTINGS for default priority list
from src.config_loader import DEFAULT_SETTINGS

# --- Test Data for Scope Testing ---
HTML_WITH_MAIN = "<body><header></header><main><h1>Main Content</h1></main><footer></footer></body>"
HTML_WITH_DIV_ROLE = '<body><header></header><div role="main"><h1>Div Role Main</h1></div><footer></footer></body>'
HTML_WITH_SINGLE_ARTICLE = "<body><article>Single</article></body>" # Simplified
HTML_WITH_MULTI_ARTICLE = "<body><article>One</article><article>Two</article></body>"
HTML_WITH_MAIN_AND_ARTICLE = "<body><main><h1>Main</h1><article>Sub</article></main></body>"
HTML_WITH_DIV_AND_ARTICLE = '<body><div role="main"><h1>Main</h1><article>Sub</article></div></body>'
HTML_WITH_NONE = "<body><header></header><div>Just a div</div><footer></footer></body>"


# Use the default priority list for most scope tests
DEFAULT_PRIORITY = DEFAULT_SETTINGS["scope_selectors_priority"]

# --- Tests for find_content_scope ---
# (These tests remain unchanged as the function logic didn't change for success cases)

def test_find_content_scope_main():
    """Tests that <main> tag is preferred."""
    soup = BeautifulSoup(HTML_WITH_MAIN, 'html.parser')
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "main"

def test_find_content_scope_div_role():
    """Tests that <div role='main'> is found if <main> is not present."""
    soup = BeautifulSoup(HTML_WITH_DIV_ROLE, 'html.parser')
    # Check with single quotes
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "div[role='main']"

def test_find_content_scope_single_article():
    """Tests finding a single <article> if <main> and div[role=main] absent."""
    soup = BeautifulSoup(HTML_WITH_SINGLE_ARTICLE, 'html.parser')
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "article"

def test_find_content_scope_multiple_articles():
    """Tests that multiple <article> tags result in no scope found."""
    soup = BeautifulSoup(HTML_WITH_MULTI_ARTICLE, 'html.parser')
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) is None

def test_find_content_scope_main_preferred():
    """Tests that <main> is chosen even if <article> is present."""
    soup = BeautifulSoup(HTML_WITH_MAIN_AND_ARTICLE, 'html.parser')
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "main"

def test_find_content_scope_div_role_preferred():
    """Tests that <div role='main'> is chosen over <article>."""
    soup = BeautifulSoup(HTML_WITH_DIV_AND_ARTICLE, 'html.parser')
    # Check with single quotes
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) == "div[role='main']"

def test_find_content_scope_none_found():
    """Tests returning None when no suitable tags are present."""
    soup = BeautifulSoup(HTML_WITH_NONE, 'html.parser')
    assert find_content_scope(soup, priority_list=DEFAULT_PRIORITY) is None

def test_find_content_scope_custom_priority():
    """Tests using a custom priority list."""
    soup = BeautifulSoup(HTML_WITH_MAIN_AND_ARTICLE, 'html.parser')
    custom_priority = ["article", "main"] # Article first
    assert find_content_scope(soup, priority_list=custom_priority) == "article"

@patch('src.html_parsing.html_scope.logging') # Use patch from unittest.mock
def test_find_content_scope_invalid_selector_in_list(mock_log): # Renamed arg
    """Tests that invalid CSS selectors in priority list are skipped."""
    soup = BeautifulSoup(HTML_WITH_MAIN, 'html.parser')
    priority = ["!invalid", "main"]
    assert find_content_scope(soup, priority_list=priority) == "main"
    # Check that a warning was logged for the invalid selector attempt
    mock_log.warning.assert_called_once()
    assert "Error applying selector '!invalid'" in mock_log.warning.call_args[0][0]


# --- Updated Test for no_semantic_base_html_tag ---

# ========================================
# Function: test_no_semantic_base_html_tag (Updated)
# Description: Tests the fallback function logs warning and returns 'body'.
# ========================================
@patch('src.html_parsing.html_scope.logging') # Patch logging for this test
def test_no_semantic_base_html_tag(mock_scope_logging):
    """Tests the fallback function logs warning and returns 'body'."""
    test_url = "http://example.com/no-scope"
    result = no_semantic_base_html_tag(test_url)

    # Assert it returns the string 'body'
    assert isinstance(result, str)
    assert result == "body"

    # Assert that the warning was logged correctly
    mock_scope_logging.warning.assert_called_once()
    # Check the content of the log message
    log_message = mock_scope_logging.warning.call_args[0][0] # Get first positional arg passed to warning()
    assert "No primary semantic content tag found" in log_message
    assert "Falling back to <body> scope" in log_message
    assert test_url in log_message