# src/config_loader.py
import logging
import yaml
from typing import Dict, Any

# --- Load Configuration ---
# Default settings in case config file is missing parts
DEFAULT_SETTINGS: Dict[str, Any] = {
    "input_file": "input_urls.txt",
    "output_base_dir": "output",
    "output_subfolder": "metadata_reports",
    "log_level": "INFO",
    "headless": True,
    "window_width": 1440,
    "window_height": 1080,
    "request_max_retries": 3,
    "request_timeout": 10, # seconds
    "skip_ssl_check_on_error": False, # Note: The interactive skip logic overrides this
}

settings: Dict[str, Any] = DEFAULT_SETTINGS.copy() # Start with defaults

try:
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
        loaded_settings = config.get("settings", {}) if config else {}
        settings.update(loaded_settings) # Update defaults with loaded settings
except FileNotFoundError:
    logging.warning("config.yaml not found. Using default settings.")
    # No exit here, allow running with defaults
except yaml.YAMLError as e:
    logging.error(f"CRITICAL: Error parsing config.yaml: {e}. Using default settings.")
    # No exit here, allow running with defaults, but log critical error

# --- Configuration Variables (Derived from settings dict) ---
INPUT_FILE: str = settings["input_file"]
OUTPUT_BASE_DIR: str = settings["output_base_dir"]
OUTPUT_SUBFOLDER: str = settings["output_subfolder"]
LOG_LEVEL_STR: str = settings["log_level"]
HEADLESS: bool = settings["headless"]
WINDOW_WIDTH: int = settings["window_width"]
WINDOW_HEIGHT: int = settings["window_height"]
REQUEST_MAX_RETRIES: int = settings["request_max_retries"]
REQUEST_TIMEOUT: int = settings["request_timeout"]
SKIP_SSL_CHECK_ON_ERROR: bool = settings["skip_ssl_check_on_error"] # Retained for potential future non-interactive use

# --- Configure logging ---
def setup_logging():
    """Configures the root logger based on settings."""
    log_level: int = getattr(logging, LOG_LEVEL_STR.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f"Logging configured to level: {LOG_LEVEL_STR.upper()}")
    logging.info(f"Loaded settings: {settings}") # Log the actual settings being used

# Call setup_logging() immediately when this module is imported
# setup_logging() # Commented out - Better to call explicitly in main.py after colorama init