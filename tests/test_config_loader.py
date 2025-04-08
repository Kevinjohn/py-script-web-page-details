# tests/test_config_loader.py
import pytest
from unittest.mock import patch, mock_open
import yaml # Required for YAMLError testing
import logging # Import logging module itself for constants

# Import the functions/constants to test
from src.config_loader import load_configuration, setup_logging, DEFAULT_SETTINGS

# NOTE: Using pytest-mock's 'mocker' fixture for patching for first tests

# ========================================
# Function: test_load_config_file_not_found (using mocker)
# Description: Tests that defaults are returned when config file is missing.
# ========================================
def test_load_config_file_not_found(mocker): # Pass mocker fixture
    """Tests load_configuration returns defaults if file not found."""
    mock_log = mocker.patch('src.config_loader.logging')
    mock_op = mocker.patch('src.config_loader.open', side_effect=FileNotFoundError)

    settings = load_configuration("nonexistent_config.yaml")

    assert settings == DEFAULT_SETTINGS
    mock_op.assert_called_once_with("nonexistent_config.yaml", "r")
    mock_log.warning.assert_called_once_with("nonexistent_config.yaml not found. Using default settings.")
    mock_log.error.assert_not_called()

# ========================================
# Function: test_load_config_override_defaults (using mocker)
# Description: Tests that settings from config file correctly override defaults.
# ========================================
mock_yaml_content = """
settings:
  input_file: "my_urls.txt"
  headless: false
  log_level: "DEBUG"
  new_setting: 123
"""
def test_load_config_override_defaults(mocker): # Pass mocker fixture
    """Tests that loaded settings override defaults correctly."""
    mock_log = mocker.patch('src.config_loader.logging')
    mock_op = mocker.patch('src.config_loader.open', mock_open(read_data=mock_yaml_content))

    settings = load_configuration("dummy_path.yaml")

    assert settings["input_file"] == "my_urls.txt"
    assert settings["headless"] is False
    assert settings["log_level"] == "DEBUG"
    assert settings["output_base_dir"] == DEFAULT_SETTINGS["output_base_dir"]
    assert settings["new_setting"] == 123
    mock_op.assert_called_once_with("dummy_path.yaml", "r")
    mock_log.warning.assert_not_called()

# ========================================
# Function: test_load_config_yaml_error (using mocker)
# Description: Tests handling of invalid YAML format.
# ========================================
def test_load_config_yaml_error(mocker): # Pass mocker fixture
    """Tests that defaults are returned and error logged on YAMLError."""
    mock_log = mocker.patch('src.config_loader.logging')
    mock_yaml = mocker.patch('src.config_loader.yaml.safe_load', side_effect=yaml.YAMLError("Bad YAML Format"))
    mock_op = mocker.patch('src.config_loader.open', mock_open(read_data="invalid: yaml: file"))

    settings = load_configuration("bad_format.yaml")

    assert settings == DEFAULT_SETTINGS
    mock_op.assert_called_once_with("bad_format.yaml", "r")
    mock_yaml.assert_called_once()
    mock_log.error.assert_called_once()
    assert "Error parsing bad_format.yaml" in mock_log.error.call_args[0][0]
    mock_log.warning.assert_not_called()

# ========================================
# Function: test_setup_logging
# Description: Basic test for the logging setup function.
# ========================================
@patch('src.config_loader.logging') # Using @patch decorator here
def test_setup_logging(mock_logging_module): # Name represents the mocked module
    """Tests that setup_logging calls basicConfig with appropriate level."""

    # --- Pre-configure mock attributes to return actual integer levels ---
    # This ensures getattr inside setup_logging finds these integer values
    mock_logging_module.DEBUG = logging.DEBUG # e.g., 10
    mock_logging_module.INFO = logging.INFO   # e.g., 20
    # Configure how the mock handles unknown attributes if needed (optional)
    # For this case, getattr's default handling should suffice if INFO is set.

    # Test DEBUG level
    setup_logging("DEBUG")
    mock_logging_module.basicConfig.assert_called_once()
    args, kwargs = mock_logging_module.basicConfig.call_args
    # *** Assert against the expected integer value ***
    assert kwargs.get("level") == logging.DEBUG # Check if 10 was passed
    mock_logging_module.info.assert_called_with("Logging configured to level: DEBUG")

    mock_logging_module.reset_mock() # Reset mock before next call

    # --- Re-configure mock attributes after reset if necessary ---
    # reset_mock might clear explicitly set attributes depending on version/config
    # It's safer to re-set them before the next distinct test case within the function.
    mock_logging_module.DEBUG = logging.DEBUG
    mock_logging_module.INFO = logging.INFO

    # Test INFO level
    setup_logging("INFO")
    mock_logging_module.basicConfig.assert_called_once()
    args, kwargs = mock_logging_module.basicConfig.call_args
    # *** Assert against the expected integer value ***
    assert kwargs.get("level") == logging.INFO # Check if 20 was passed
    mock_logging_module.info.assert_called_with("Logging configured to level: INFO")

    mock_logging_module.reset_mock() # Reset mock before next call

    # --- Re-configure mock attributes after reset ---
    mock_logging_module.DEBUG = logging.DEBUG
    mock_logging_module.INFO = logging.INFO
    # Ensure INFO exists for the default value in getattr
    # If an invalid level is passed, getattr should not find it.
    # We need to ensure it *doesn't* have an INVALID_LEVEL attribute if we want getattr to use the default.
    # If INVALID_LEVEL exists on the mock from a previous test or auto-creation, getattr might return it.
    # Let's explicitly delete it to be safe before the invalid test.
    if hasattr(mock_logging_module, 'INVALID_LEVEL'):
        del mock_logging_module.INVALID_LEVEL

    # Test fallback for invalid level
    setup_logging("INVALID_LEVEL")
    mock_logging_module.basicConfig.assert_called_once()
    args, kwargs = mock_logging_module.basicConfig.call_args
    # *** Assert against the expected integer value (defaults to INFO) ***
    assert kwargs.get("level") == logging.INFO # Check if 20 was passed (default)
    mock_logging_module.info.assert_called_with("Logging configured to level: INVALID_LEVEL")