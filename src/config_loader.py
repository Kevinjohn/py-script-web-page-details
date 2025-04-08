# src/config_loader.py
import logging
import yaml
from typing import Dict, Any

# Default settings remain as a constant
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
    "skip_ssl_check_on_error": False,
}

# ========================================
# Function: load_configuration
# Description: Loads settings from a YAML file, merges with defaults.
# ========================================
def load_configuration(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Loads settings from a YAML file, merges with defaults.

    Args:
        config_path: Path to the configuration file.

    Returns:
        A dictionary containing the final configuration settings.
    """
    settings = DEFAULT_SETTINGS.copy() # Start with defaults
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
            loaded_settings = config.get("settings", {}) if config else {}
            settings.update(loaded_settings) # Update defaults with loaded settings
        logging.debug(f"Configuration loaded successfully from {config_path}")
    except FileNotFoundError:
        # Log the warning here during the load attempt
        logging.warning(f"{config_path} not found. Using default settings.")
    except yaml.YAMLError as e:
        # Log the error here during the load attempt
        logging.error(f"Error parsing {config_path}: {e}. Using default settings.")
    except Exception as e:
        # Catch other potential file reading errors
        logging.error(f"Error reading {config_path}: {e}. Using default settings.")

    logging.info(f"Final settings loaded: {settings}") # Log the actual settings being used
    return settings

# ========================================
# Function: setup_logging
# Description: Configures the root logger based on the provided level string.
# ========================================
def setup_logging(log_level_str: str):
    """
    Configures the root logger based on the provided level string.

    Args:
        log_level_str: The desired logging level (e.g., "INFO", "DEBUG").
    """
    log_level: int = getattr(logging, log_level_str.upper(), logging.INFO)
    # Ensure basicConfig is only called once if possible, or configure root logger properties
    # For simplicity here, we'll keep basicConfig, but in complex apps, might get logger and set level/handlers
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', force=True) # Use force=True if re-configuring
    logging.info(f"Logging configured to level: {log_level_str.upper()}")

# Note: Global variables like INPUT_FILE, HEADLESS etc. are removed.
# They will be accessed from the settings dictionary returned by load_configuration()
# in the main script where they are needed.