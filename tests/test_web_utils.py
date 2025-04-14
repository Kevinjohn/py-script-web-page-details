# tests/test_web_utils.py
import pytest
from unittest.mock import patch, MagicMock, call # Import 'call'
import requests # Need requests.exceptions for testing
from selenium.common.exceptions import TimeoutException, WebDriverException

# Import functions to test
from src.web_utils import fetch_http_status_and_type, fetch_and_parse_html
# Import default settings
from src.config_loader import DEFAULT_SETTINGS

# --- Tests for fetch_http_status_and_type ---

# ========================================
# Function: test_fetch_http_status_success
# ========================================
@patch('requests.head')
def test_fetch_http_status_success(mock_head):
    """Tests successful fetch of status and type."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "text/html; charset=utf-8"}
    mock_response.raise_for_status.return_value = None
    mock_head.return_value = mock_response

    status, content_type = fetch_http_status_and_type("https://example.com", {})
    assert status == 200
    assert content_type == "text/html"
    mock_head.assert_called_once_with(
        "https://example.com",
        allow_redirects=True,
        timeout=pytest.approx(DEFAULT_SETTINGS["request_timeout"]),
        verify=True
    )

# ========================================
# Function: test_fetch_http_status_request_error_with_retry
# ========================================
@patch('requests.head')
@patch('time.sleep')
def test_fetch_http_status_request_error_with_retry(mock_sleep, mock_head):
    """Tests handling of RequestException including retry delays."""
    # Simulate non-HTTP RequestException (e.g., timeout before response)
    mock_head.side_effect = requests.exceptions.Timeout("Connection timed out")
    max_retries_used = DEFAULT_SETTINGS["request_max_retries"]

    status, content_type = fetch_http_status_and_type("https://example.com", {})

    # Non-HTTP errors should still return None for status
    assert status is None
    assert "Request Error (Timeout)" in content_type
    assert mock_head.call_count == max_retries_used
    expected_sleep_calls = [call(2**i) for i in range(max_retries_used - 1)]
    assert mock_sleep.call_args_list == expected_sleep_calls

# ========================================
# Function: test_fetch_http_status_ssl_error_skip
# ========================================
@patch('requests.head')
@patch('builtins.input')
@patch('time.sleep')
def test_fetch_http_status_ssl_error_skip(mock_sleep, mock_input, mock_head):
    """Tests SSL error, user input 'y', then success on retry."""
    mock_ssl_error = requests.exceptions.SSLError("Cert verify failed")
    mock_success_response = MagicMock()
    mock_success_response.status_code = 200
    mock_success_response.headers = {"Content-Type": "text/plain"}
    mock_success_response.raise_for_status.return_value = None
    mock_head.side_effect = [mock_ssl_error, mock_success_response]
    mock_input.return_value = 'y'
    ssl_decision = {}

    status, content_type = fetch_http_status_and_type("https://example.com", ssl_decision)

    assert status == 200
    assert content_type == "text/plain"
    # ... (rest of assertions unchanged) ...
    assert mock_input.call_count == 1
    assert mock_head.call_count == 2
    assert mock_head.call_args_list[0].kwargs['verify'] is True
    assert mock_head.call_args_list[1].kwargs['verify'] is False
    assert ssl_decision == {"skip_all": True}
    mock_sleep.assert_not_called()

# ========================================
# Function: test_fetch_http_status_ssl_error_no_skip
# ========================================
@patch('requests.head')
@patch('builtins.input')
def test_fetch_http_status_ssl_error_no_skip(mock_input, mock_head):
    """Tests SSL error and user input 'n'."""
    mock_head.side_effect = requests.exceptions.SSLError("Cert verify failed")
    mock_input.return_value = 'n'
    ssl_decision = {}

    status, content_type = fetch_http_status_and_type("https://example.com", ssl_decision)

    # SSL error declined by user should return None for status
    assert status is None
    assert content_type == "SSL Error (User Declined Skip)"
    # ... (rest of assertions unchanged) ...
    assert mock_input.call_count == 1
    assert mock_head.call_count == 1


# --- Corrected Tests for HTTP Errors ---

# ========================================
# Function: test_fetch_http_status_404_error_with_retry (Updated Assertion)
# ========================================
@patch('requests.head')
@patch('time.sleep')
def test_fetch_http_status_404_error_with_retry(mock_sleep, mock_head):
    """Tests handling of a 404 Not Found error including retries."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.headers = {"Content-Type": "text/html"}
    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = http_error
    mock_head.return_value = mock_response
    max_retries_used = DEFAULT_SETTINGS["request_max_retries"]

    status, content_type = fetch_http_status_and_type("https://example.com/notfound", {})

    # *** Assert that the specific HTTP error code is returned ***
    assert status == 404
    assert "Request Error (HTTPError)" in content_type
    # Check retries happened
    assert mock_head.call_count == max_retries_used
    assert mock_response.raise_for_status.call_count == max_retries_used
    expected_sleep_calls = [call(2**i) for i in range(max_retries_used - 1)]
    assert mock_sleep.call_args_list == expected_sleep_calls


# ========================================
# Function: test_fetch_http_status_500_error_with_retry (Updated Assertion)
# ========================================
@patch('requests.head')
@patch('time.sleep')
def test_fetch_http_status_500_error_with_retry(mock_sleep, mock_head):
    """Tests handling of a 500 Internal Server Error with retries."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}
    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = http_error
    mock_head.return_value = mock_response
    max_retries_used = DEFAULT_SETTINGS["request_max_retries"]

    status, content_type = fetch_http_status_and_type("https://example.com/servererror", {})

    # *** Assert that the specific HTTP error code is returned ***
    assert status == 500
    assert "Request Error (HTTPError)" in content_type
    # Check retries happened
    assert mock_head.call_count == max_retries_used
    assert mock_response.raise_for_status.call_count == max_retries_used
    expected_sleep_calls = [call(2**i) for i in range(max_retries_used - 1)]
    assert mock_sleep.call_args_list == expected_sleep_calls


# ========================================
# Function: test_fetch_http_status_redirect_followed
# ========================================
# (No changes needed here)
@patch('requests.head')
def test_fetch_http_status_redirect_followed(mock_head):
    """Tests that redirects are followed (mocked)."""
    mock_final_response = MagicMock()
    mock_final_response.status_code = 200
    mock_final_response.headers = {"Content-Type": "text/html"}
    mock_final_response.raise_for_status.return_value = None
    mock_head.return_value = mock_final_response

    status, content_type = fetch_http_status_and_type("https://example.com/redirect", {})

    assert status == 200
    assert content_type == "text/html"
    mock_head.assert_called_once_with(
        "https://example.com/redirect", allow_redirects=True,
        timeout=pytest.approx(DEFAULT_SETTINGS["request_timeout"]), verify=True
    )

# --- Tests for fetch_and_parse_html ---
# (No changes needed in these tests based on recent source code updates)
# ========================================
# Function: test_fetch_and_parse_success
# ========================================
@patch('src.web_utils.WebDriverWait')
def test_fetch_and_parse_success(mock_wait):
    # ... (test body) ...
    mock_driver = MagicMock()
    mock_driver.page_source = "<html><head><title>Mock Page</title></head><body></body></html>"
    mock_wait_instance = MagicMock()
    mock_wait_instance.until.return_value = True
    mock_wait.return_value = mock_wait_instance
    soup = fetch_and_parse_html("https://example.com", mock_driver)
    assert soup is not None
    assert soup.title.string == "Mock Page"
    mock_wait.assert_called_once()
    mock_wait_instance.until.assert_called_once()

# ========================================
# Function: test_fetch_and_parse_timeout
# ========================================
@patch('src.web_utils.WebDriverWait')
def test_fetch_and_parse_timeout(mock_wait):
    # ... (test body) ...
    mock_driver = MagicMock()
    mock_wait_instance = MagicMock()
    mock_wait_instance.until.side_effect = TimeoutException("Page load timed out")
    mock_wait.return_value = mock_wait_instance
    soup = fetch_and_parse_html("https://example.com", mock_driver, page_load_timeout=5)
    assert soup is None
    mock_wait.assert_called_once()
    mock_wait_instance.until.assert_called_once()

# ========================================
# Function: test_fetch_and_parse_driver_generic_error
# ========================================
def test_fetch_and_parse_driver_generic_error():
    # ... (test body) ...
    mock_driver = MagicMock()
    mock_driver.get.side_effect = Exception("WebDriver crashed")
    soup = fetch_and_parse_html("https://example.com", mock_driver)
    assert soup is None

# ========================================
# Function: test_fetch_and_parse_webdriver_exception
# ========================================
def test_fetch_and_parse_webdriver_exception():
    # ... (test body) ...
    mock_driver = MagicMock()
    mock_driver.get.side_effect = WebDriverException("Cannot connect to browser")
    soup = fetch_and_parse_html("https://example.com", mock_driver)
    assert soup is None

# ========================================
# Function: test_fetch_and_parse_empty_page_source
# ========================================
@patch('src.web_utils.WebDriverWait')
def test_fetch_and_parse_empty_page_source(mock_wait):
    # ... (test body) ...
    mock_driver = MagicMock()
    mock_driver.page_source = ""
    mock_wait_instance = MagicMock()
    mock_wait_instance.until.return_value = True
    mock_wait.return_value = mock_wait_instance
    soup = fetch_and_parse_html("https://example.com", mock_driver)
    assert soup is not None
    assert str(soup) == ""
    mock_wait.assert_called_once()
    mock_wait_instance.until.assert_called_once()

# ========================================
# Function: test_fetch_and_parse_with_wait_after_load (NEW Test for wait)
# ========================================
@patch('src.web_utils.WebDriverWait')
@patch('src.web_utils.time.sleep') # Mock sleep
def test_fetch_and_parse_with_wait_after_load(mock_sleep, mock_wait):
    """Tests that the wait_after_load delay is applied."""
    mock_driver = MagicMock()
    mock_driver.page_source = "<html></html>"
    mock_wait_instance = MagicMock()
    mock_wait_instance.until.return_value = True
    mock_wait.return_value = mock_wait_instance
    wait_duration = 2

    soup = fetch_and_parse_html("https://example.com", mock_driver, wait_after_load=wait_duration)

    assert soup is not None
    mock_wait.assert_called_once()
    mock_wait_instance.until.assert_called_once()
    # Check that time.sleep was called with the correct duration
    mock_sleep.assert_called_once_with(wait_duration)

@patch('src.web_utils.WebDriverWait')
@patch('src.web_utils.time.sleep') # Mock sleep
def test_fetch_and_parse_with_zero_wait_after_load(mock_sleep, mock_wait):
    """Tests that no sleep occurs if wait_after_load is 0."""
    mock_driver = MagicMock()
    mock_driver.page_source = "<html></html>"
    mock_wait_instance = MagicMock()
    mock_wait_instance.until.return_value = True
    mock_wait.return_value = mock_wait_instance

    soup = fetch_and_parse_html("https://example.com", mock_driver, wait_after_load=0) # Wait is 0

    assert soup is not None
    mock_wait.assert_called_once()
    mock_wait_instance.until.assert_called_once()
    # Check that time.sleep was NOT called
    mock_sleep.assert_not_called()