# tests/test_file_io.py
import pytest
import os
import csv
from unittest.mock import patch, mock_open

from src.file_io import read_input_file, sanitise_domain, write_to_csv

# ========================================
# Function: test_sanitise_domain
# Description: Tests sanitising domain names for use in filenames.
# ========================================
@pytest.mark.parametrize("url, expected_sanitised", [
    ("http://www.example.com", "www_example_com"),
    ("https://sub.domain.co.uk/path?query=1", "sub_domain_co_uk"),
    ("http://127.0.0.1:8000", "127_0_0_1_8000"),
    ("invalid-url", "unknown_domain"), # Assuming urlparse fails gracefully or returns no netloc
    ("file:///path/to/file.html", "file_html"), # Example fallback behavior test
])
def test_sanitise_domain(url, expected_sanitised):
    """Tests sanitising domain names from URLs."""
    assert sanitise_domain(url) == expected_sanitised

# ========================================
# Function: test_read_input_file_success
# Description: Tests reading URLs from a file using mocking.
# ========================================
@patch("builtins.open", new_callable=mock_open, read_data="https://example.com\n#comment\nhttp://test.org/page\n\ninvalid-url")
@patch("os.path.exists") # Mock os.path.exists as well
def test_read_input_file_success(mock_exists, mock_file_open):
    """Tests successfully reading valid URLs, skipping comments/invalid."""
    mock_exists.return_value = True # Simulate file exists
    urls = read_input_file("dummy_path.txt")
    assert urls == ["https://example.com", "http://test.org/page"]
    mock_file_open.assert_called_once_with("dummy_path.txt", "r", encoding="utf-8")

# ========================================
# Function: test_read_input_file_not_found_then_found
# Description: Tests the interactive prompt when a file isn't found initially (using mocking).
# ========================================
# This test is more complex due to mocking input() and multiple exists() calls
@patch("builtins.input")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open, read_data="https://final.com")
def test_read_input_file_not_found_then_found(mock_file_open, mock_exists, mock_input):
    """Tests the file not found prompt, then finding the file."""
    # Simulate file not existing, then existing after prompt
    mock_exists.side_effect = [False, True]
    # Simulate user entering a new path
    mock_input.return_value = "correct_path.txt"

    urls = read_input_file("wrong_path.txt")

    assert urls == ["https://final.com"]
    assert mock_exists.call_count == 2
    mock_input.assert_called_once() # Check that input() was called
    mock_file_open.assert_called_once_with("correct_path.txt", "r", encoding="utf-8")


# ========================================
# Function: test_read_input_file_not_found_exit
# Description: Tests exiting if user provides no path at the prompt.
# ========================================
@patch("builtins.input")
@patch("os.path.exists")
def test_read_input_file_not_found_exit(mock_exists, mock_input):
    """Tests exiting when the user enters nothing at the prompt."""
    mock_exists.return_value = False # File doesn't exist
    mock_input.return_value = ""    # User hits Enter

    urls = read_input_file("wrong_path.txt")
    assert urls == []
    mock_input.assert_called_once()


# ========================================
# Function: test_write_to_csv_success
# Description: Tests writing data to CSV using pytest's tmp_path fixture.
# ========================================
def test_write_to_csv_success(tmp_path):
    """Tests successfully writing data to a CSV file."""
    output_dir = tmp_path / "output"
    # Note: write_to_csv creates the directory, so we don't need os.makedirs here
    file_path = output_dir / "test.csv"
    data = [
        {"col1": "a", "col2": 1, "extra": True},
        {"col1": "b", "col2": 2}
    ]
    fieldnames = ["col1", "col2"] # Note 'extra' field is ignored

    success = write_to_csv(str(file_path), data, fieldnames)

    assert success is True
    assert file_path.is_file() # Check if file was created

    # Verify content
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ["col1", "col2"]
        rows = list(reader)
        assert rows == [["a", "1"], ["b", "2"]]

# ========================================
# Function: test_write_to_csv_empty_data
# Description: Tests that writing empty data returns False and doesn't create a file.
# ========================================
def test_write_to_csv_empty_data(tmp_path):
    """Tests that write_to_csv handles empty data correctly."""
    file_path = tmp_path / "empty.csv"
    success = write_to_csv(str(file_path), [], ["col1"])
    assert success is False
    assert not file_path.exists() # File should not be created for empty data