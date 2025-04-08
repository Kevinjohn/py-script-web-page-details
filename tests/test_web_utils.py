# tests/test_web_utils.py
import pytest
from unittest.mock import patch, MagicMock, call # Import 'call' for checking call args list
import requests # Need requests.exceptions for testing
from selenium.common.exceptions import TimeoutException, WebDriverException # Import WebDriverException

# Import functions to test
from src.web_utils import fetch_http_status_and_type, fetch_and_parse_html
# Import default settings to check against default values used in function signatures
from src.config_loader import DEFAULT_SETTINGS

# --- Tests for fetch_http_status_and_type ---

# ========================================
# Function: test_fetch_http_status_success
# Description: Tests successful HEAD request scenario.
# ========================================
@patch('requests.head') # Mock the requests.head function
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
# Description: Tests handling of generic RequestException with retry logic.
# ========================================
# Decorator order: sleep -> head
@patch('requests.head') # Passed as mock_head (second arg)
@patch('time.sleep') # Passed as mock_sleep (first arg)
def test_fetch_http_status_request_error_with_retry(mock_sleep, mock_head): # Correct argument order
    """Tests handling of RequestException including retry delays."""
    mock_head.side_effect = requests.exceptions.RequestException("Connection failed")
    max_retries_used = DEFAULT_SETTINGS["request_max_retries"] # e.g., 3

    status, content_type = fetch_http_status_and_type("https://example.com", {})

    assert status is None
    assert "Request Error (RequestException)" in content_type
    assert mock_head.call_count == max_retries_used
    # Check sleep calls with exponential backoff (1s, 2s for 3 retries)
    expected_sleep_calls = [call(2**i) for i in range(max_retries_used - 1)]
    assert mock_sleep.call_args_list == expected_sleep_calls
    assert mock_sleep.call_count == max_retries_used - 1


# ========================================
# Function: test_fetch_http_status_ssl_error_skip
# Description: Tests handling SSL error and user choosing to skip.
# ========================================
# Decorator order: sleep -> input -> head
@patch('requests.head') # Passed as mock_head (third arg)
@patch('builtins.input') # Passed as mock_input (second arg)
@patch('time.sleep') # Passed as mock_sleep (first arg)
def test_fetch_http_status_ssl_error_skip(mock_sleep, mock_input, mock_head): # Correct argument order
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
    assert mock_input.call_count == 1
    assert mock_head.call_count == 2
    assert mock_head.call_args_list[0].kwargs['verify'] is True
    assert mock_head.call_args_list[1].kwargs['verify'] is False
    assert ssl_decision == {"skip_all": True}
    mock_sleep.assert_not_called() # No sleep between SSL error -> retry


# ========================================
# Function: test_fetch_http_status_ssl_error_no_skip
# Description: Tests handling SSL error and user choosing *not* to skip.
# ========================================
# Decorator order: input -> head
@patch('requests.head') # Passed as mock_head (second arg)
@patch('builtins.input') # Passed as mock_input (first arg)
def test_fetch_http_status_ssl_error_no_skip(mock_input, mock_head): # Correct argument order
    """Tests SSL error and user input 'n'."""
    mock_head.side_effect = requests.exceptions.SSLError("Cert verify failed")
    mock_input.return_value = 'n'
    ssl_decision = {}

    status, content_type = fetch_http_status_and_type("https://example.com", ssl_decision)

    assert status is None
    assert content_type == "SSL Error (User Declined Skip)"
    assert mock_input.call_count == 1
    assert mock_head.call_count == 1


# --- Corrected Tests for HTTP Errors ---

# ========================================
# Function: test_fetch_http_status_404_error_with_retry
# Description: Tests handling of a 404 HTTP error including retries.
# ========================================
# Decorator order: sleep -> head
@patch('requests.head') # Passed as mock_head (second arg)
@patch('time.sleep') # Passed as mock_sleep (first arg)
def test_fetch_http_status_404_error_with_retry(mock_sleep, mock_head): # Corrected argument order
    """Tests handling of a 404 Not Found error including retries."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.headers = {"Content-Type": "text/html"}
    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = http_error
    # Make head return this failing response repeatedly
    mock_head.return_value = mock_response
    max_retries_used = DEFAULT_SETTINGS["request_max_retries"]

    status, content_type = fetch_http_status_and_type("https://example.com/notfound", {})

    assert status is None
    # The error message comes from the final RequestException catch block after retries
    assert "Request Error (HTTPError)" in content_type
    # Check that retries happened
    assert mock_head.call_count == max_retries_used
    # Check raise_for_status was called each time
    assert mock_response.raise_for_status.call_count == max_retries_used
    # Check sleep was called correctly
    expected_sleep_calls = [call(2**i) for i in range(max_retries_used - 1)]
    assert mock_sleep.call_args_list == expected_sleep_calls
    assert mock_sleep.call_count == max_retries_used - 1


# ========================================
# Function: test_fetch_http_status_500_error_with_retry
# Description: Tests handling of a 500 HTTP error including retries.
# ========================================
# Decorator order: sleep -> head
@patch('requests.head') # Passed as mock_head (second arg)
@patch('time.sleep') # Passed as mock_sleep (first arg)
def test_fetch_http_status_500_error_with_retry(mock_sleep, mock_head): # Corrected argument order
    """Tests handling of a 500 Internal Server Error with retries."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.headers = {}
    http_error = requests.exceptions.HTTPError(response=mock_response)
    mock_response.raise_for_status.side_effect = http_error
    mock_head.return_value = mock_response
    max_retries_used = DEFAULT_SETTINGS["request_max_retries"]

    status, content_type = fetch_http_status_and_type("https://example.com/servererror", {})

    assert status is None
    assert "Request Error (HTTPError)" in content_type
    assert mock_head.call_count == max_retries_used
    assert mock_response.raise_for_status.call_count == max_retries_used
    expected_sleep_calls = [call(2**i) for i in range(max_retries_used - 1)]
    assert mock_sleep.call_args_list == expected_sleep_calls
    assert mock_sleep.call_count == max_retries_used - 1


# ========================================
# Function: test_fetch_http_status_redirect_followed
# Description: Tests successful handling of a 301 redirect.
# ========================================
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
        "https://example.com/redirect",
        allow_redirects=True, # This is key
        timeout=pytest.approx(DEFAULT_SETTINGS["request_timeout"]),
        verify=True
    )

# --- Tests for fetch_and_parse_html ---

# ========================================
# Function: test_fetch_and_parse_success
# Description: Tests successful HTML fetching and parsing using mocked Selenium.
# ========================================
@patch('src.web_utils.WebDriverWait') # Mock WebDriverWait where it's looked up
def test_fetch_and_parse_success(mock_wait):
    """Tests successful fetch and parse with mocked Selenium driver."""
    mock_driver = MagicMock()
    mock_driver.page_source = "<html><head><title>Mock Page</title></head><body></body></html>"
    mock_wait_instance = MagicMock()
    mock_wait_instance.until.return_value = True
    mock_wait.return_value = mock_wait_instance

    soup = fetch_and_parse_html("https://example.com", mock_driver)

    assert soup is not None
    assert soup.title.string == "Mock Page"
    mock_driver.get.assert_called_once_with("https://example.com")
    mock_wait.assert_called_once()
    mock_wait_instance.until.assert_called_once()


# ========================================
# Function: test_fetch_and_parse_timeout
# Description: Tests handling of Selenium TimeoutException during page load wait.
# ========================================
@patch('src.web_utils.WebDriverWait') # Mock WebDriverWait where it's looked up
def test_fetch_and_parse_timeout(mock_wait):
    """Tests handling TimeoutException from WebDriverWait."""
    mock_driver = MagicMock()
    mock_wait_instance = MagicMock()
    mock_wait_instance.until.side_effect = TimeoutException("Page load timed out")
    mock_wait.return_value = mock_wait_instance

    soup = fetch_and_parse_html("https://example.com", mock_driver, page_load_timeout=5)

    assert soup is None
    mock_driver.get.assert_called_once_with("https://example.com")
    mock_wait.assert_called_once()
    mock_wait_instance.until.assert_called_once()


# ========================================
# Function: test_fetch_and_parse_driver_generic_error
# Description: Tests handling of a generic exception during driver.get().
# ========================================
def test_fetch_and_parse_driver_generic_error():
    """Tests handling a generic error during driver.get()."""
    mock_driver = MagicMock()
    mock_driver.get.side_effect = Exception("WebDriver crashed") # Simulate generic error

    soup = fetch_and_parse_html("https://example.com", mock_driver)

    assert soup is None
    mock_driver.get.assert_called_once_with("https://example.com")


# --- NEW Tests for fetch_and_parse_html ---

# ========================================
# Function: test_fetch_and_parse_webdriver_exception
# Description: Tests handling of WebDriverException during driver.get().
# ========================================
def test_fetch_and_parse_webdriver_exception():
    """Tests handling WebDriverException during driver.get()."""
    mock_driver = MagicMock()
    mock_driver.get.side_effect = WebDriverException("Cannot connect to browser")

    soup = fetch_and_parse_html("https://example.com", mock_driver)

    assert soup is None
    mock_driver.get.assert_called_once_with("https://example.com")


# ========================================
# Function: test_fetch_and_parse_empty_page_source
# Description: Tests handling when driver returns empty page source.
# ========================================
@patch('src.web_utils.WebDriverWait')
def test_fetch_and_parse_empty_page_source(mock_wait):
    """Tests handling of empty page source from driver."""
    mock_driver = MagicMock()
    mock_driver.page_source = "" # Empty source
    mock_wait_instance = MagicMock()
    mock_wait_instance.until.return_value = True
    mock_wait.return_value = mock_wait_instance

    soup = fetch_and_parse_html("https://example.com", mock_driver)

    assert soup is not None # BeautifulSoup usually handles empty string
    assert str(soup) == "" # Resulting soup object should be empty
    mock_driver.get.assert_called_once_with("https://example.com")
    mock_wait.assert_called_once()
    mock_wait_instance.until.assert_called_once()