# src/config_loader.py
import logging
import yaml
from typing import Dict, Any, List

# Default settings remain as a constant
DEFAULT_SETTINGS: Dict[str, Any] = {
    # Existing settings...
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
    "scope_selectors_priority": ["main", "div[role='main']", "article"],
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15"
    ],
    "wait_after_load_seconds": 0,
    "delay_between_requests_seconds": 1,

    # --- NEW Settings ---
    "output_format": "CSV", # Output format ("CSV" or "JSON")
    "run_in_batches": False, # Process URLs in batches interactively
    "batch_size": 50,      # Default number of URLs per batch if batching enabled
    "chromedriver_path": "", # Optional: Full path to manually downloaded chromedriver executable
    
}

# ========================================
# Function: load_configuration
# ========================================
def load_configuration(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Loads settings from a YAML file, merges with defaults, validates types.

    Args:
        config_path: Path to the configuration file.

    Returns:
        A dictionary containing the final configuration settings.
    """
    settings = DEFAULT_SETTINGS.copy()
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
            loaded_settings = config.get("settings", {}) if config else {}
            settings.update(loaded_settings)
        logging.debug(f"Configuration loaded successfully from {config_path}")
    except FileNotFoundError:
        logging.warning(f"{config_path} not found. Using default settings.")
    except yaml.YAMLError as e:
        logging.error(f"Error parsing {config_path}: {e}. Using default settings.")
    except Exception as e:
        logging.error(f"Error reading {config_path}: {e}. Using default settings.")

    # --- Type and Value Validation ---
    # Numeric settings
    numeric_keys = ["window_width", "window_height", "request_max_retries",
                    "request_timeout", "wait_after_load_seconds",
                    "delay_between_requests_seconds", "batch_size"]
    for key in numeric_keys:
        try:
            if key in settings:
                settings[key] = int(settings[key])
                if settings[key] < 0: # Ensure non-negative where applicable
                     logging.warning(f"Negative value for '{key}' not recommended. Using absolute value.")
                     settings[key] = abs(settings[key]) # Or fallback to default? abs seems reasonable.
        except (ValueError, TypeError):
            logging.warning(f"Invalid non-integer value for '{key}' in config. Using default: {DEFAULT_SETTINGS[key]}")
            settings[key] = DEFAULT_SETTINGS[key]

    # Boolean settings
    boolean_keys = ["headless", "skip_ssl_check_on_error", "run_in_batches"]
    for key in boolean_keys:
         if key in settings and not isinstance(settings[key], bool):
             # Attempt common string conversions, default to False on failure
             if str(settings[key]).lower() in ['true', 'yes', '1']:
                 settings[key] = True
             elif str(settings[key]).lower() in ['false', 'no', '0']:
                  settings[key] = False
             else:
                  logging.warning(f"Invalid boolean value for '{key}' in config. Using default: {DEFAULT_SETTINGS[key]}")
                  settings[key] = DEFAULT_SETTINGS[key]

    # List settings
    list_keys = ["scope_selectors_priority", "user_agents"]
    for key in list_keys:
         if key in settings and not isinstance(settings[key], list):
             logging.warning(f"Invalid non-list value for '{key}' in config. Using default.")
             settings[key] = DEFAULT_SETTINGS[key]

    # String choice settings
    output_format = settings.get("output_format", DEFAULT_SETTINGS["output_format"])
    if str(output_format).upper() not in ["CSV", "JSON"]:
        logging.warning(f"Invalid output_format '{output_format}'. Defaulting to 'CSV'.")
        settings["output_format"] = "CSV"
    else:
        settings["output_format"] = str(output_format).upper() # Standardize case

    # chromedriver_path just needs to be a string (or empty/None)
    if "chromedriver_path" in settings and not isinstance(settings["chromedriver_path"], str):
         logging.warning(f"Invalid non-string value for 'chromedriver_path'. Using default.")
         settings["chromedriver_path"] = DEFAULT_SETTINGS["chromedriver_path"]

    # --- Logging Final Settings ---
    logging.info(f"Final settings loaded (some values might be truncated):")
    for key, value in settings.items():
         logging.info(f"  {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")

    return settings

# ========================================
# Function: setup_logging
# ========================================
# (No changes needed here)
def setup_logging(log_level_str: str):
    """
    Configures the root logger based on the provided level string.

    Args:
        log_level_str: The desired logging level (e.g., "INFO", "DEBUG").
    """
    log_level: int = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
    logging.info(f"Logging configured to level: {log_level_str.upper()}")