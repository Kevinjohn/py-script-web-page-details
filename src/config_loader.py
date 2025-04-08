# src/config_loader.py
import logging
import yaml
from typing import Dict, Any, List # Added List

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

    # --- NEW Settings ---
    "scope_selectors_priority": ["main", "div[role='main']", "article"], # Configurable scope find order
    "user_agents": [ # List of User-Agents to rotate through (optional)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15"
    ],
    "wait_after_load_seconds": 0, # Optional fixed delay after page load state 'complete'
    "delay_between_requests_seconds": 1, # Optional delay between processing URLs
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
            # Basic type validation/casting could be added here if needed
            settings.update(loaded_settings) # Update defaults with loaded settings
        logging.debug(f"Configuration loaded successfully from {config_path}")
    except FileNotFoundError:
        logging.warning(f"{config_path} not found. Using default settings.")
    except yaml.YAMLError as e:
        logging.error(f"Error parsing {config_path}: {e}. Using default settings.")
    except Exception as e:
        logging.error(f"Error reading {config_path}: {e}. Using default settings.")

    # Ensure numeric values are appropriate types (or handle errors)
    for key in ["window_width", "window_height", "request_max_retries", "request_timeout", "wait_after_load_seconds", "delay_between_requests_seconds"]:
        try:
            if key in settings:
                settings[key] = int(settings[key])
        except (ValueError, TypeError):
            logging.warning(f"Invalid non-integer value for '{key}' in config. Using default: {DEFAULT_SETTINGS[key]}")
            settings[key] = DEFAULT_SETTINGS[key]
    # Ensure lists are lists
    for key in ["scope_selectors_priority", "user_agents"]:
         if key in settings and not isinstance(settings[key], list):
             logging.warning(f"Invalid non-list value for '{key}' in config. Using default.")
             settings[key] = DEFAULT_SETTINGS[key]


    logging.info(f"Final settings loaded (some values might be truncated):")
    for key, value in settings.items():
         logging.info(f"  {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")

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
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
    logging.info(f"Logging configured to level: {log_level_str.upper()}")