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

    # Check that the returned settings ARE the defaults
    assert settings == DEFAULT_SETTINGS
    # Explicitly check a few key defaults, including new ones
    assert settings['input_file'] == "input_urls.txt"
    assert settings['log_level'] == "INFO"
    assert settings['output_format'] == "CSV"
    assert settings['run_in_batches'] is False
    assert settings['batch_size'] == 50
    assert settings['scope_selectors_priority'] == ["main", "div[role='main']", "article"]

    # Check interactions
    mock_op.assert_called_once_with("nonexistent_config.yaml", "r")
    mock_log.warning.assert_called_once_with("nonexistent_config.yaml not found. Using default settings.")
    mock_log.error.assert_not_called()

# ========================================
# Function: test_load_config_override_defaults (using mocker)
# Description: Tests that settings from config file correctly override defaults.
# ========================================
# Include new settings in the mock YAML content
mock_yaml_content_override = """
settings:
  input_file: "my_urls.txt"
  headless: false
  log_level: "DEBUG"
  new_setting: 123 # Add a new setting not in defaults
  output_format: "JSON"
  run_in_batches: true
  batch_size: 99
  scope_selectors_priority: ["#main-content", "article"]
  user_agents: ["MyCustomUA/1.0"]
"""
def test_load_config_override_defaults(mocker): # Pass mocker fixture
    """Tests that loaded settings override defaults correctly."""
    mock_log = mocker.patch('src.config_loader.logging')
    # Use mock_open helper for read_data with mocker.patch
    mock_op = mocker.patch('src.config_loader.open', mock_open(read_data=mock_yaml_content_override))

    settings = load_configuration("dummy_path.yaml")

    # Check overridden values (including new ones)
    assert settings["input_file"] == "my_urls.txt"
    assert settings["headless"] is False
    assert settings["log_level"] == "DEBUG"
    assert settings["output_format"] == "JSON"
    assert settings["run_in_batches"] is True
    assert settings["batch_size"] == 99
    assert settings["scope_selectors_priority"] == ["#main-content", "article"]
    assert settings["user_agents"] == ["MyCustomUA/1.0"]

    # Check default value that wasn't overridden
    assert settings["output_base_dir"] == DEFAULT_SETTINGS["output_base_dir"]
    # Check the new setting added by the file
    assert settings["new_setting"] == 123
    # Check file was opened
    mock_op.assert_called_once_with("dummy_path.yaml", "r")
    mock_log.warning.assert_not_called() # No warning on success


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

    # Should return defaults on error
    assert settings == DEFAULT_SETTINGS
    # Check file was opened and safe_load was attempted
    mock_op.assert_called_once_with("bad_format.yaml", "r")
    mock_yaml.assert_called_once()
    # Check error was logged
    mock_log.error.assert_called_once()
    assert "Error parsing bad_format.yaml" in mock_log.error.call_args[0][0]
    mock_log.warning.assert_not_called()


# --- NEW Tests for Validation Logic ---

# ========================================
# Function: test_load_config_invalid_output_format (using mocker)
# Description: Tests validation fallback for output_format.
# ========================================
mock_yaml_invalid_format = """
settings:
  output_format: "XML" # Invalid format
"""
def test_load_config_invalid_output_format(mocker):
    """Tests that output_format defaults to CSV if invalid value is provided."""
    mock_log = mocker.patch('src.config_loader.logging')
    mock_op = mocker.patch('src.config_loader.open', mock_open(read_data=mock_yaml_invalid_format))

    settings = load_configuration("invalid_format.yaml")

    assert settings["output_format"] == "CSV" # Check it defaulted
    mock_log.warning.assert_called_with("Invalid output_format 'XML'. Defaulting to 'CSV'.")

# ========================================
# Function: test_load_config_invalid_batch_size (using mocker)
# Description: Tests validation fallback for non-integer batch_size.
# ========================================
mock_yaml_invalid_batch = """
settings:
  batch_size: "fifty" # Invalid integer
"""
def test_load_config_invalid_batch_size(mocker):
    """Tests that batch_size uses default if non-integer provided."""
    mock_log = mocker.patch('src.config_loader.logging')
    mock_op = mocker.patch('src.config_loader.open', mock_open(read_data=mock_yaml_invalid_batch))

    settings = load_configuration("invalid_batch.yaml")

    assert settings["batch_size"] == DEFAULT_SETTINGS["batch_size"] # Check it used default
    mock_log.warning.assert_called_with(f"Invalid non-integer value for 'batch_size' in config. Using default: {DEFAULT_SETTINGS['batch_size']}")

# ========================================
# Function: test_load_config_invalid_run_in_batches (using mocker)
# Description: Tests validation fallback for non-boolean run_in_batches.
# ========================================
mock_yaml_invalid_bool = """
settings:
  run_in_batches: "maybe" # Invalid boolean
"""
def test_load_config_invalid_run_in_batches(mocker):
    """Tests that run_in_batches uses default if non-boolean provided."""
    mock_log = mocker.patch('src.config_loader.logging')
    mock_op = mocker.patch('src.config_loader.open', mock_open(read_data=mock_yaml_invalid_bool))

    settings = load_configuration("invalid_bool.yaml")

    assert settings["run_in_batches"] == DEFAULT_SETTINGS["run_in_batches"] # Check it used default
    mock_log.warning.assert_called_with(f"Invalid boolean value for 'run_in_batches' in config. Using default: {DEFAULT_SETTINGS['run_in_batches']}")

# ========================================
# Function: test_load_config_valid_boolean_strings (using mocker)
# Description: Tests valid string representations for boolean conversion.
# ========================================
@pytest.mark.parametrize("bool_str, expected_val", [
    ("true", True), ("Yes", True), ("1", True),
    ("FALSE", False), ("no", False), ("0", False),
])
def test_load_config_valid_boolean_strings(mocker, bool_str, expected_val):
    """Tests that valid string representations are converted to booleans."""
    mock_yaml_content = f"""
settings:
  run_in_batches: "{bool_str}"
"""
    mock_log = mocker.patch('src.config_loader.logging')
    mock_op = mocker.patch('src.config_loader.open', mock_open(read_data=mock_yaml_content))

    settings = load_configuration("valid_bool_str.yaml")

    assert settings["run_in_batches"] is expected_val
    mock_log.warning.assert_not_called() # No warning for valid conversions


# --- Test for setup_logging (remains the same) ---

# ========================================
# Function: test_setup_logging
# Description: Basic test for the logging setup function.
# ========================================
@patch('src.config_loader.logging') # Using @patch decorator here
def test_setup_logging(mock_logging_module): # Name represents the mocked module
    """Tests that setup_logging calls basicConfig with appropriate level."""

    # --- Pre-configure mock attributes to return actual integer levels ---
    mock_logging_module.DEBUG = logging.DEBUG
    mock_logging_module.INFO = logging.INFO

    # --- Test DEBUG level ---
    setup_logging("DEBUG")
    mock_logging_module.basicConfig.assert_called_once()
    args, kwargs = mock_logging_module.basicConfig.call_args
    assert kwargs.get("level") == logging.DEBUG
    mock_logging_module.info.assert_called_with("Logging configured to level: DEBUG")

    mock_logging_module.reset_mock()

    # --- Re-configure mock attributes after reset ---
    mock_logging_module.DEBUG = logging.DEBUG
    mock_logging_module.INFO = logging.INFO

    # --- Test INFO level ---
    setup_logging("INFO")
    mock_logging_module.basicConfig.assert_called_once()
    args, kwargs = mock_logging_module.basicConfig.call_args
    assert kwargs.get("level") == logging.INFO
    mock_logging_module.info.assert_called_with("Logging configured to level: INFO")

    mock_logging_module.reset_mock()

    # --- Re-configure mock attributes after reset ---
    mock_logging_module.DEBUG = logging.DEBUG
    mock_logging_module.INFO = logging.INFO
    if hasattr(mock_logging_module, 'INVALID_LEVEL'):
        del mock_logging_module.INVALID_LEVEL

    # --- Test fallback for invalid level ---
    setup_logging("INVALID_LEVEL")
    mock_logging_module.basicConfig.assert_called_once()
    args, kwargs = mock_logging_module.basicConfig.call_args
    assert kwargs.get("level") == logging.INFO
    mock_logging_module.info.assert_called_with("Logging configured to level: INVALID_LEVEL")