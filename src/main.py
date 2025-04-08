#!/usr/bin/env python3
# src/main.py
import os
import logging
import time # Import time for delay
import random # Import random for User-Agent
from datetime import datetime
from typing import Optional, List, Dict, Any

# Third-party imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from colorama import init, Fore, Style

# --- Import project modules ---
init(autoreset=True)
from .config_loader import load_configuration, setup_logging, DEFAULT_SETTINGS
from .file_io import read_input_file, write_to_csv, sanitise_domain
from .orchestrator import extract_metadata

# ========================================
# Function: main (Updated)
# Description: Main script execution function.
# ========================================
def main() -> None:
    """Main script execution function."""
    # --- Load Configuration and Setup Logging ---
    settings = load_configuration("config.yaml")
    log_level_str = settings.get("log_level", DEFAULT_SETTINGS["log_level"])
    setup_logging(log_level_str)

    logging.info("Script starting.")
    logging.debug(f"Using settings (values might be truncated):")
    for key, value in settings.items():
         logging.debug(f"  {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")


    # --- Get required settings ---
    input_file = settings.get("input_file", DEFAULT_SETTINGS["input_file"])
    output_base_dir = settings.get("output_base_dir", DEFAULT_SETTINGS["output_base_dir"])
    output_subfolder = settings.get("output_subfolder", DEFAULT_SETTINGS["output_subfolder"])
    headless_mode = settings.get("headless", DEFAULT_SETTINGS["headless"])
    window_width = settings.get("window_width", DEFAULT_SETTINGS["window_width"])
    window_height = settings.get("window_height", DEFAULT_SETTINGS["window_height"])
    user_agents = settings.get("user_agents", DEFAULT_SETTINGS["user_agents"]) # Get UA list
    inter_request_delay = settings.get("delay_between_requests_seconds", DEFAULT_SETTINGS["delay_between_requests_seconds"]) # Get delay

    # --- Read Input File ---
    urls = read_input_file(input_file)
    if not urls:
        logging.critical("No valid URLs found or provided. Exiting.")
        print(Fore.RED + "Error: No valid URLs found.")
        return

    # --- User prompt for number of URLs ---
    # (Existing prompt logic...)
    num_to_process = 0
    try:
        prompt = (f"{Fore.CYAN}Found {len(urls)} URLs. "
                  f"How many do you want to process? (Enter 0 or leave blank for all): {Style.RESET_ALL}")
        num_to_process_str = input(prompt).strip()
        if num_to_process_str:
            num_to_process = int(num_to_process_str)
            if 0 < num_to_process < len(urls):
                 urls = urls[:num_to_process]
                 logging.info(f"Processing the first {len(urls)} URLs as requested.")
            elif num_to_process <= 0:
                 logging.info("Processing all URLs (0 or negative entered).")
            else: # num_to_process >= len(urls)
                 logging.info(f"Number entered >= available URLs. Processing all {len(urls)} URLs.")
        else:
             logging.info("Processing all URLs (no number entered).")
    except ValueError:
        logging.warning("Invalid input for number of URLs, processing all.")
    except EOFError:
        logging.warning("Input stream closed during prompt, processing all URLs.")


    # --- Setup Output Path ---
    # (Existing output path logic...)
    output_dir = os.path.join(output_base_dir, output_subfolder)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    first_url_for_filename = urls[0] if urls else "no_urls_processed"
    sanitised_domain = sanitise_domain(first_url_for_filename)
    output_csv_file = f"page_details_{sanitised_domain}_{timestamp}.csv"
    output_path = os.path.join(output_dir, output_csv_file)
    logging.info(f"Output CSV will be saved to: {output_path}")


    # --- Configure Selenium WebDriver ---
    options = Options()
    if headless_mode:
        options.add_argument('--headless=new')
        logging.info("Running WebDriver in headless mode.")
    else:
        logging.info("Running WebDriver in headed mode.")
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--window-size={window_width},{window_height}')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # --- NEW: Add User-Agent Rotation ---
    selected_ua = None
    if user_agents: # Check if list is not empty
        selected_ua = random.choice(user_agents)
        options.add_argument(f'user-agent={selected_ua}')
        logging.info(f"Using User-Agent: {selected_ua}")
    else:
        logging.info("No User-Agents configured, using default.")
    # --- End NEW ---

    driver: Optional[webdriver.Chrome] = None
    metadata_list: List[Dict[str, Any]] = []
    ssl_decision: Dict[str, bool] = {"skip_all": False}

    try:
        logging.info("Initializing WebDriver...")
        print(Fore.YELLOW + "Initializing WebDriver (this might take a moment)...")
        try:
             driver_path = ChromeDriverManager().install()
             service = Service(driver_path)
             driver = webdriver.Chrome(service=service, options=options)
             logging.info(f"WebDriver initialized successfully using driver at: {driver_path}")
             print(Fore.GREEN + "WebDriver initialized.")
        except Exception as wd_init_error:
             logging.critical(f"Failed to initialize WebDriver: {wd_init_error}", exc_info=True)
             print(Fore.RED + f"CRITICAL ERROR: Failed to initialize WebDriver: {wd_init_error}")
             return


        # --- Process URLs ---
        total_urls = len(urls)
        for idx, url in enumerate(urls, start=1):
            print(Style.BRIGHT + Fore.GREEN + f"\nProcessing ({idx}/{total_urls}): {url}" + Style.RESET_ALL)
            # --- Pass the full settings dictionary to the orchestrator ---
            metadata = extract_metadata(url, driver, ssl_decision, settings)
            if metadata:
                 metadata_list.append(metadata)
                 if metadata.get("IA error"):
                     print(Fore.YELLOW + f"  Warning/Error noted for {url}: {metadata['IA error']}")
                 else:
                     print(Fore.CYAN + f"  Successfully processed {url}")
            else:
                 # Should ideally not happen if extract_metadata always returns dict
                 logging.error(f"Critical failure processing {url} - extract_metadata returned None.")
                 metadata_list.append({"Page-URL": url, "IA error": "Critical extraction failure (None returned)"})
                 print(Fore.RED + f"  Critical error processing {url}. Check logs.")

            # --- NEW: Add Inter-Request Delay ---
            if idx < total_urls and inter_request_delay > 0: # Apply delay after processing, before the next loop iteration (if any)
                 logging.debug(f"Waiting {inter_request_delay}s before next request...")
                 time.sleep(inter_request_delay)
            # --- End NEW ---


        # --- Define CSV Headers ---
        # (Keep existing fieldnames definition...)
        fieldnames = [
            "http-code", "http-type", "Page-URL", "page-slug", "Page-id", "Parent-ID",
            "Title", "Description", "Keywords",
            "Opengraph type", "Opengraph image", "Opengraph title", "Opengraph description",
            "Article H1", "Article Headings", "Article Links Internal", "Article Links External",
            "Article Images", "Article Images NoAlt",
            "content-count", "content-ratio",
            "Parent-URL", "IA error",
        ]


        # --- Write Results ---
        # (Keep existing write logic...)
        if metadata_list:
             if write_to_csv(output_path, metadata_list, fieldnames):
                 print(Fore.CYAN + Style.BRIGHT + f"\nMetadata successfully saved to: {output_path}")
             else:
                 print(Fore.RED + Style.BRIGHT + f"\nFailed to save metadata to CSV. Check logs.")
        else:
             print(Fore.YELLOW + "\nNo metadata was collected to write to CSV.")


    except Exception as e:
        logging.critical(f"A critical error occurred in the main script execution: {e}", exc_info=True)
        print(Fore.RED + Style.BRIGHT + f"\n--- A critical error occurred ---")
        print(Fore.RED + f"Please check the log file for details. Error: {e}")

    finally:
        # --- Cleanup ---
        # (Keep existing cleanup logic...)
        if driver:
            try:
                logging.info("Attempting to quit WebDriver...")
                driver.quit()
                logging.info("WebDriver quit successfully.")
                print(Fore.CYAN + "WebDriver closed.")
            except Exception as e:
                logging.error(f"Error quitting WebDriver: {e}", exc_info=True)
                print(Fore.RED + f"Error trying to close WebDriver: {e}")
        print(Style.BRIGHT + Fore.MAGENTA + "\nScript finished.")


if __name__ == "__main__":
    main()