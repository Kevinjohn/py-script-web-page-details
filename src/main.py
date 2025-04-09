#!/usr/bin/env python3
# src/main.py
import os
import logging
import time
import random
import math
import ssl # Import ssl for exception handling
from datetime import datetime
from typing import Optional, List, Dict, Any

# Third-party imports
import requests # Import requests for exception handling
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from colorama import init, Fore, Style

# --- Import project modules ---
init(autoreset=True)
from .config_loader import load_configuration, setup_logging, DEFAULT_SETTINGS
from .file_io import read_input_file, write_output_file, sanitise_domain
from .orchestrator import extract_metadata

# ========================================
# Function: main (Updated WebDriver Init)
# ========================================
def main() -> None:
    """Main script execution function with batch processing and format options."""
    # --- Load Configuration and Setup Logging ---
    settings = load_configuration("config.yaml")
    log_level_str = settings.get("log_level", DEFAULT_SETTINGS["log_level"])
    setup_logging(log_level_str)

    logging.info("Script starting.")
    # (Log settings...)
    logging.debug(f"Using settings (values might be truncated):")
    for key, value in settings.items():
         logging.debug(f"  {key}: {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}")


    # --- Get required settings ---
    # (Get other settings as before...)
    input_file = settings.get("input_file", DEFAULT_SETTINGS["input_file"])
    output_base_dir = settings.get("output_base_dir", DEFAULT_SETTINGS["output_base_dir"])
    output_subfolder = settings.get("output_subfolder", DEFAULT_SETTINGS["output_subfolder"])
    headless_mode = settings.get("headless", DEFAULT_SETTINGS["headless"])
    window_width = settings.get("window_width", DEFAULT_SETTINGS["window_width"])
    window_height = settings.get("window_height", DEFAULT_SETTINGS["window_height"])
    user_agents = settings.get("user_agents", DEFAULT_SETTINGS["user_agents"])
    inter_request_delay = settings.get("delay_between_requests_seconds", DEFAULT_SETTINGS["delay_between_requests_seconds"])
    output_format = settings.get("output_format", DEFAULT_SETTINGS["output_format"])
    run_in_batches = settings.get("run_in_batches", DEFAULT_SETTINGS["run_in_batches"])
    default_batch_size = settings.get("batch_size", DEFAULT_SETTINGS["batch_size"])
    chromedriver_manual_path = settings.get("chromedriver_path", DEFAULT_SETTINGS["chromedriver_path"]) # Get manual path


    # --- Read Input File ---
    # (Read input logic...)
    urls_all = read_input_file(input_file)
    if not urls_all:
        # ... (error handling) ...
        return

    total_urls_available = len(urls_all)
    logging.info(f"Total valid URLs available: {total_urls_available}")
    urls_to_process_all = urls_all
    # (Limit total URLs logic...)
    # ...

    total_urls_to_run = len(urls_to_process_all)
    processed_count_total = 0
    current_batch_num = 0
    urls_processed_in_run = 0
    base_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Configure Selenium Options (Done before driver init) ---
    options = Options()
    if headless_mode: options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--window-size={window_width},{window_height}')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    selected_ua = None
    if user_agents:
        selected_ua = random.choice(user_agents)
        options.add_argument(f'user-agent={selected_ua}')
        logging.info(f"Using User-Agent: {selected_ua}")

    driver: Optional[webdriver.Chrome] = None
    ssl_decision: Dict[str, bool] = {"skip_all": False}

    # --- Main Processing Section ---
    try:
        # --- Initialize WebDriver (with fallback) ---
        # Define driver outside the try blocks so it's accessible in finally
        driver = None

        # Attempt 1: Use webdriver-manager
        try:
            logging.info("Attempting to initialize WebDriver using webdriver-manager...")
            print(Fore.YELLOW + "Initializing WebDriver via manager (might check/download driver)...")
            # Pass driver version explicitly if needed (e.g., from config or detected)
            # driver_version = settings.get("chromedriver_version", None) # Example
            # manager = ChromeDriverManager(version=driver_version) if driver_version else ChromeDriverManager()
            manager = ChromeDriverManager() # Keep it simple for now
            driver_path_manager = manager.install()
            service = Service(driver_path_manager)
            driver = webdriver.Chrome(service=service, options=options)
            logging.info(f"WebDriver initialized successfully via manager using driver at: {driver_path_manager}")
            print(Fore.GREEN + "WebDriver initialized via manager.")

        # Catch specific errors known to cause webdriver-manager issues + general errors
        except (requests.exceptions.RequestException, # Covers ConnectionError, ProxyError, SSLError, Timeout etc.
                ssl.SSLError, # Explicitly catch SSL errors
                ValueError,   # Can happen with version parsing
                OSError,      # Filesystem/permission errors during install/cache
                Exception     # Catch-all for other unexpected manager issues
                ) as e_manager:

            logging.warning(f"Webdriver-manager failed: {type(e_manager).__name__}: {e_manager}")
            print(Fore.YELLOW + f"\nWebdriver-manager failed ({type(e_manager).__name__}). Trying specified chromedriver_path...")

            # Attempt 2: Use specified path from config
            if chromedriver_manual_path and isinstance(chromedriver_manual_path, str):
                 # Basic check if path exists and is a file
                 if os.path.exists(chromedriver_manual_path) and os.path.isfile(chromedriver_manual_path):
                      logging.info(f"Attempting to initialize WebDriver using specified path: {chromedriver_manual_path}")
                      print(Fore.YELLOW + f"Using specified chromedriver path: {chromedriver_manual_path}")
                      try:
                           service = Service(chromedriver_manual_path)
                           driver = webdriver.Chrome(service=service, options=options)
                           logging.info(f"WebDriver initialized successfully using specified path.")
                           print(Fore.GREEN + "WebDriver initialized using specified path.")
                      except Exception as e_manual:
                           logging.critical(f"Failed to initialize WebDriver using specified path '{chromedriver_manual_path}': {e_manual}", exc_info=True)
                           driver = None # Ensure driver is None if this fails
                 else:
                      logging.error(f"Specified chromedriver_path '{chromedriver_manual_path}' is not a valid file.")
                      driver = None # Ensure driver is None
            else:
                 logging.info("No valid chromedriver_path specified in config.")
                 driver = None # Ensure driver is None

            # If driver is still None after trying fallback, we must exit
            if driver is None:
                logging.critical(f"Failed to initialize WebDriver via manager and no valid fallback path worked.")
                print(Fore.RED + f"CRITICAL ERROR: Unable to initialize WebDriver.")
                print(Fore.RED + f"  Attempted manager -> FAILED ({type(e_manager).__name__}).")
                if chromedriver_manual_path:
                    print(Fore.RED + f"  Attempted specified path '{chromedriver_manual_path}' -> FAILED or INVALID.")
                else:
                    print(Fore.RED + f"  No alternative chromedriver_path was specified in config.")
                print(Fore.RED + f"  Please check network/firewall/proxy settings, SSL certificates (try REQUESTS_CA_BUNDLE or WDM_SSL_VERIFY=0),")
                print(Fore.RED + f"  or provide a valid path to a downloaded chromedriver executable in config.yaml.")
                return # Exit main function


        # --- If we get here, driver should be initialized ---
        logging.info("WebDriver initialization complete.")


        # --- Batch Loop ---
        # (Batch loop logic remains the same as previous version)
        while urls_processed_in_run < total_urls_to_run:
            current_batch_num += 1
            batch_start_index = urls_processed_in_run
            batch_size_this_run = default_batch_size

            # --- Determine Batch Size ---
            if run_in_batches:
                 # (Interactive prompt logic remains the same)
                 remaining_urls = total_urls_to_run - urls_processed_in_run
                 prompt_batch = (
                    f"{Fore.CYAN}\n--- Batch {current_batch_num} --- ({urls_processed_in_run}/{total_urls_to_run} processed)\n"
                    f"Process next batch? Max {remaining_urls} remaining.\n"
                    f"Enter number (or 0/blank for default {min(default_batch_size, remaining_urls)}), 'n' or 'q' to quit: {Style.RESET_ALL}"
                 )
                 try:
                     user_batch_input = input(prompt_batch).strip().lower()
                     if user_batch_input in ['n', 'q', 'no', 'quit']: break
                     elif not user_batch_input or user_batch_input == '0': batch_size_this_run = min(default_batch_size, remaining_urls)
                     else:
                         try:
                             requested_batch_size = int(user_batch_input)
                             if requested_batch_size <= 0: batch_size_this_run = min(default_batch_size, remaining_urls)
                             else: batch_size_this_run = min(requested_batch_size, remaining_urls)
                         except ValueError: batch_size_this_run = min(default_batch_size, remaining_urls)
                 except EOFError: break
            else:
                batch_size_this_run = total_urls_to_run - urls_processed_in_run

            if batch_size_this_run <= 0: break

            # --- Prepare & Process Batch ---
            batch_end_index = batch_start_index + batch_size_this_run
            urls_batch = urls_to_process_all[batch_start_index:batch_end_index]
            batch_metadata_list: List[Dict[str, Any]] = []
            print(Style.BRIGHT + Fore.MAGENTA + f"\nStarting Batch {current_batch_num} ({batch_size_this_run} URLs from index {batch_start_index+1} to {batch_end_index})...")

            for idx_in_batch, url in enumerate(urls_batch, start=1):
                global_idx = batch_start_index + idx_in_batch
                print(Style.BRIGHT + Fore.GREEN + f"\nProcessing URL {idx_in_batch}/{batch_size_this_run} (Overall: {global_idx}/{total_urls_to_run}): {url}" + Style.RESET_ALL)
                metadata = extract_metadata(url, driver, ssl_decision, settings)
                if metadata: batch_metadata_list.append(metadata) # Simplified append
                # (Console output...)
                if metadata.get("IA error"): print(Fore.YELLOW + f"  Warning/Error noted: {metadata['IA error']}")
                else: print(Fore.CYAN + f"  Successfully processed.")

                # --- Inter-Request Delay ---
                if idx_in_batch < batch_size_this_run and inter_request_delay > 0:
                     logging.debug(f"Waiting {inter_request_delay}s before next request...")
                     time.sleep(inter_request_delay)

            # --- Save Output for Batch ---
            if batch_metadata_list:
                # (Output path logic remains the same)
                output_dir = os.path.join(output_base_dir, output_subfolder)
                first_url_for_filename = urls_batch[0] if urls_batch else f"batch_{current_batch_num}"
                sanitised_domain = sanitise_domain(first_url_for_filename)
                file_ext = output_format.lower()
                batch_suffix = f"_batch_{current_batch_num}" if run_in_batches and total_urls_to_run > default_batch_size else ""
                output_filename = f"page_details_{sanitised_domain}_{base_timestamp}{batch_suffix}.{file_ext}"
                output_path = os.path.join(output_dir, output_filename)

                fieldnames = [ # Define headers consistently
                    "http-code", "http-type", "Page-URL", "page-slug", "Page-id", "Parent-ID",
                    "Title", "Description", "Keywords", "Opengraph type", "Opengraph image",
                    "Opengraph title", "Opengraph description", "Article H1", "Article Headings",
                    "Article Links Internal", "Article Links External", "Article Images", "Article Images NoAlt",
                    "content-count", "content-ratio", "Parent-URL", "IA error", ]

                if write_output_file(output_path, batch_metadata_list, fieldnames, output_format):
                    print(Fore.CYAN + Style.BRIGHT + f"\nBatch {current_batch_num} results saved to: {output_path}")
                else:
                    print(Fore.RED + Style.BRIGHT + f"\nFailed to save results for Batch {current_batch_num}.")
            else:
                print(Fore.YELLOW + f"\nNo metadata collected in Batch {current_batch_num} to write.")

            urls_processed_in_run += len(urls_batch)
            # End of while loop iteration

        logging.info(f"Finished processing. Total URLs processed in this run: {urls_processed_in_run}")
        print(Fore.GREEN + f"\nFinished processing. Total URLs processed in this run: {urls_processed_in_run}")

    except Exception as e:
        logging.critical(f"A critical error occurred outside the main processing loop: {e}", exc_info=True)
        print(Fore.RED + Style.BRIGHT + f"\n--- A critical error occurred ---")
        print(Fore.RED + f"Please check the log file for details. Error: {e}")

    finally:
        # --- Cleanup ---
        if driver:
            try:
                logging.info("Attempting to quit WebDriver...")
                driver.quit()
                logging.info("WebDriver quit successfully.")
                print(Fore.CYAN + "WebDriver closed.")
            except Exception as e:
                logging.error(f"Error quitting WebDriver: {e}")
                print(Fore.RED + f"Error trying to close WebDriver: {e}")
        print(Style.BRIGHT + Fore.MAGENTA + "\nScript finished.")


if __name__ == "__main__":
    main()