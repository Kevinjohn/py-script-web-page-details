# tests/test_file_io.py
import pytest
import os
import csv
import json # Import json for testing JSON output
from unittest.mock import patch, mock_open

# Import corrected function names
from src.file_io import read_input_file, sanitise_domain, write_output_file

# ========================================
# Function: test_sanitise_domain
# ========================================
@pytest.mark.parametrize("url, expected_sanitised", [
    ("http://www.example.com", "www_example_com"),
    ("https://sub.domain.co.uk/path?query=1", "sub_domain_co_uk"),
    ("http://127.0.0.1:8000", "127_0_0_1_8000"),
    ("invalid-url", "unknown_domain"),
    ("file:///path/to/file.html", "file_html"),
])
def test_sanitise_domain(url, expected_sanitised):
    """Tests sanitising domain names from URLs."""
    assert sanitise_domain(url) == expected_sanitised

# ========================================
# Function: test_read_input_file_txt_success
# Description: Tests reading URLs from a TXT file using mocking.
# ========================================
@patch("builtins.open", new_callable=mock_open, read_data="https://example.com\n#comment\nhttp://test.org/page\n\ninvalid-url")
@patch("os.path.exists")
def test_read_input_file_txt_success(mock_exists, mock_file_open):
    """Tests successfully reading valid URLs from TXT, skipping comments/invalid."""
    mock_exists.return_value = True
    # Assume TXT if extension isn't .csv
    urls = read_input_file("dummy_path.txt")
    assert urls == ["https://example.com", "http://test.org/page"]
    # Check it was opened without newline='' for TXT
    mock_file_open.assert_called_once_with("dummy_path.txt", "r", encoding="utf-8", newline=None)

# ========================================
# Function: test_read_input_file_csv_success
# Description: Tests reading URLs from a CSV file using mocking.
# ========================================
# Simulate CSV content (URL in first column)
csv_content = '"https://good.csv/url1","other_data"\n"http://another.csv/url2"\n"#comment url"\n"invalid-url"\n""\n"https://good.csv/url3"'
@patch("builtins.open", new_callable=mock_open, read_data=csv_content)
@patch("os.path.exists")
def test_read_input_file_csv_success(mock_exists, mock_file_open):
    """Tests successfully reading valid URLs from CSV (first column)."""
    mock_exists.return_value = True
    urls = read_input_file("dummy_path.csv") # Use .csv extension
    assert urls == ["https://good.csv/url1", "http://another.csv/url2", "https://good.csv/url3"]
    # Check it was opened with newline='' for CSV
    mock_file_open.assert_called_once_with("dummy_path.csv", "r", encoding="utf-8", newline='')

# ========================================
# Function: test_read_input_file_csv_header
# Description: Tests reading CSV, skipping header row.
# ========================================
csv_content_header = '"URL","Timestamp"\n"https://real.url/","somedate"'
@patch("builtins.open", new_callable=mock_open, read_data=csv_content_header)
@patch("os.path.exists")
def test_read_input_file_csv_header(mock_exists, mock_file_open):
    """Tests reading CSV skips a common header row."""
    mock_exists.return_value = True
    urls = read_input_file("header.csv")
    assert urls == ["https://real.url/"]
    mock_file_open.assert_called_once_with("header.csv", "r", encoding="utf-8", newline='')


# ========================================
# Function: test_read_input_file_not_found_then_found
# ========================================
# (This test remains the same, assuming the found file is TXT for simplicity)
@patch("builtins.input")
@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open, read_data="https://final.com")
def test_read_input_file_not_found_then_found(mock_file_open, mock_exists, mock_input):
    """Tests the file not found prompt, then finding the file."""
    mock_exists.side_effect = [False, True]
    mock_input.return_value = "correct_path.txt" # Assume TXT found
    urls = read_input_file("wrong_path.txt")
    assert urls == ["https://final.com"]
    assert mock_exists.call_count == 2
    mock_input.assert_called_once()
    # Should be opened as TXT (newline=None)
    mock_file_open.assert_called_once_with("correct_path.txt", "r", encoding="utf-8", newline=None)


# ========================================
# Function: test_read_input_file_not_found_exit
# ========================================
# (This test remains the same)
@patch("builtins.input")
@patch("os.path.exists")
def test_read_input_file_not_found_exit(mock_exists, mock_input):
    """Tests exiting when the user enters nothing at the prompt."""
    mock_exists.return_value = False
    mock_input.return_value = ""
    urls = read_input_file("wrong_path.txt")
    assert urls == []
    mock_input.assert_called_once()


# ========================================
# Function: test_write_output_file_csv_success (Renamed)
# Description: Tests writing data to CSV using pytest's tmp_path fixture.
# ========================================
def test_write_output_file_csv_success(tmp_path): # Use tmp_path fixture
    """Tests successfully writing data to a CSV file."""
    output_dir = tmp_path / "output"
    file_path = output_dir / "test_output.csv" # Use .csv extension
    data = [
        {"col1": "a", "col2": 1, "extra": True},
        {"col1": "b", "col2": 2}
    ]
    fieldnames = ["col1", "col2"]

    # Call the renamed function with CSV format
    success = write_output_file(str(file_path), data, fieldnames, output_format="CSV")

    assert success is True
    assert file_path.is_file() # Check file created

    # Verify content
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ["col1", "col2"]
        rows = list(reader)
        assert rows == [["a", "1"], ["b", "2"]]

# ========================================
# Function: test_write_output_file_json_success (NEW Test)
# Description: Tests writing data to JSON using pytest's tmp_path fixture.
# ========================================
def test_write_output_file_json_success(tmp_path):
    """Tests successfully writing data to a JSON file."""
    output_dir = tmp_path / "output"
    file_path = output_dir / "test_output.json" # Use .json extension
    data = [
        {"col1": "a", "col2": 1, "extra": True},
        {"col1": "b", "col2": 2, "col3": None}
    ]
    # Fieldnames are ignored for JSON, but still required by function signature
    fieldnames = ["col1", "col2", "col3", "extra"]

    # Call the renamed function with JSON format
    success = write_output_file(str(file_path), data, fieldnames, output_format="JSON")

    assert success is True
    assert file_path.is_file()

    # Verify content
    with open(file_path, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    # JSON dump preserves all keys from the dictionaries
    assert loaded_data == [
        {"col1": "a", "col2": 1, "extra": True},
        {"col1": "b", "col2": 2, "col3": None}
    ]


# ========================================
# Function: test_write_output_file_empty_data (Renamed)
# Description: Tests that writing empty data returns False.
# ========================================
def test_write_output_file_empty_data(tmp_path):
    """Tests that write_output_file handles empty data correctly for CSV."""
    file_path_csv = tmp_path / "empty.csv"
    success_csv = write_output_file(str(file_path_csv), [], ["col1"], output_format="CSV")
    assert success_csv is False
    assert not file_path_csv.exists() # File should not be created

    file_path_json = tmp_path / "empty.json"
    success_json = write_output_file(str(file_path_json), [], ["col1"], output_format="JSON")
    assert success_json is False
    assert not file_path_json.exists() # File should not be created


# ========================================
# Function: test_write_output_file_unsupported_format
# Description: Tests handling of unsupported output format.
# ========================================
def test_write_output_file_unsupported_format(tmp_path):
    """Tests that an unsupported format returns False."""
    file_path = tmp_path / "output.txt"
    data = [{"col1": "a"}]
    fieldnames = ["col1"]
    success = write_output_file(str(file_path), data, fieldnames, output_format="TXT")
    assert success is False
    assert not file_path.exists() # File should not be created