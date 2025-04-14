#!/usr/bin/env python3
# src/main.py
import os
import logging
import time
import random
import math
import ssl
from datetime import datetime
from typing import Optional, List, Dict, Any

# Third-party imports
import requests
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
# Function: main (Corrected Progress Message)
# ========================================
def main() -> None:
    """Main script execution function with batch processing and format options."""
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
    user_agents = settings.get("user_agents", DEFAULT_SETTINGS["user_agents"])
    inter_request_delay = settings.get("delay_between_requests_seconds", DEFAULT_SETTINGS["delay_between_requests_seconds"])
    output_format = settings.get("output_format", DEFAULT_SETTINGS["output_format"])
    run_in_batches = settings.get("run_in_batches", DEFAULT_SETTINGS["run_in_batches"])
    default_batch_size = settings.get("batch_size", DEFAULT_SETTINGS["batch_size"])
    chromedriver_manual_path = settings.get("chromedriver_path", DEFAULT_SETTINGS["chromedriver_path"])
    start_at_index = settings.get("start_at", DEFAULT_SETTINGS["start_at"]) # Get start_at value


    # --- Read Input File ---
    urls_all_from_file = read_input_file(input_file)
    if not urls_all_from_file:
        logging.critical("No valid URLs found or provided. Exiting.")
        print(Fore.RED + "Error: No valid URLs found.")
        return

    total_read_from_file = len(urls_all_from_file)
    logging.info(f"Read {total_read_from_file} valid URLs from file.")

    # --- Apply start_at logic ---
    urls_available = urls_all_from_file
    if start_at_index > 0:
        if start_at_index < total_read_from_file:
            logging.info(f"Applying start_at={start_at_index}. Skipping first {start_at_index} URLs.")
            urls_available = urls_available[start_at_index:] # Slice the list
            print(Fore.YELLOW + f"Starting processing from URL originally at index {start_at_index} (line {start_at_index + 1} approx)...")
        else:
            logging.warning(f"start_at value ({start_at_index}) is >= total URLs read ({total_read_from_file}). No URLs left to process.")
            urls_available = []

    total_urls_available = len(urls_available)
    logging.info(f"Total URLs available for processing run: {total_urls_available}")

    if total_urls_available == 0:
         print(Fore.YELLOW + "No URLs available to process after applying 'start_at' setting.")
         return

    # --- Determine Total URLs to Process (User limit prompt) ---
    urls_to_process_all = urls_available
    try:
        prompt = (f"{Fore.CYAN}Found {total_urls_available} URLs available to process (after 'start_at'). "
                  f"How many TOTAL do you want to run? (Enter 0 or leave blank for all): {Style.RESET_ALL}")
        num_to_process_str = input(prompt).strip()
        if num_to_process_str:
            num_to_process_limit = int(num_to_process_str)
            if 0 < num_to_process_limit < total_urls_available:
                 urls_to_process_all = urls_available[:num_to_process_limit]
                 logging.info(f"Limiting run to the first {len(urls_to_process_all)} URLs based on user input.")
            elif num_to_process_limit <= 0:
                 logging.info("Processing all available URLs (0 or negative entered for total limit).")
            else:
                 logging.info(f"Total limit entered >= available URLs. Processing all {total_urls_available} available URLs.")
        else:
             logging.info("Processing all available URLs (no total limit entered).")
    except ValueError:
        logging.warning("Invalid input for total number of URLs, processing all available.")
    except EOFError:
        logging.warning("Input stream closed during total limit prompt, processing all available.")

    total_urls_to_run = len(urls_to_process_all)
    processed_count_total = 0
    current_batch_num = 0
    urls_processed_in_run = 0
    base_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- Configure Selenium Options ---
    # (Remains the same)
    options = Options()
    if headless_mode: options.add_argument('--headless=new')
    options.add_argument('--disable-gpu'); options.add_argument('--no-sandbox'); options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'--window-size={window_width},{window_height}')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    if user_agents:
        selected_ua = random.choice(user_agents)
        options.add_argument(f'user-agent={selected_ua}')
        logging.info(f"Using User-Agent: {selected_ua}")

    driver: Optional[webdriver.Chrome] = None
    ssl_decision: Dict[str, bool] = {"skip_all": False}

    # --- Main Processing Section ---
    try:
        # --- Initialize WebDriver (with fallback) ---
        # (Remains the same)
        driver = None
        try:
            logging.info("Attempting WebDriver init via manager...")
            print(Fore.YELLOW + "Initializing WebDriver via manager...")
            manager = ChromeDriverManager()
            driver_path_manager = manager.install()
            service = Service(driver_path_manager)
            driver = webdriver.Chrome(service=service, options=options)
            logging.info(f"WebDriver initialized via manager.")
            print(Fore.GREEN + "WebDriver initialized via manager.")
        except (requests.exceptions.RequestException, ssl.SSLError, ValueError, OSError, Exception) as e_manager:
            logging.warning(f"Webdriver-manager failed: {type(e_manager).__name__}: {e_manager}")
            print(Fore.YELLOW + f"\nWebdriver-manager failed. Trying specified path...")
            if chromedriver_manual_path and isinstance(chromedriver_manual_path, str) and os.path.exists(chromedriver_manual_path) and os.path.isfile(chromedriver_manual_path):
                 logging.info(f"Attempting via specified path: {chromedriver_manual_path}")
                 print(Fore.YELLOW + f"Using specified path: {chromedriver_manual_path}")
                 try:
                      service = Service(chromedriver_manual_path)
                      driver = webdriver.Chrome(service=service, options=options)
                      logging.info(f"WebDriver initialized via specified path.")
                      print(Fore.GREEN + "WebDriver initialized using specified path.")
                 except Exception as e_manual:
                      logging.critical(f"Failed via specified path: {e_manual}", exc_info=True)
                      driver = None
            else: driver = None # Ensure driver is None if path invalid/missing
            if driver is None:
                 logging.critical(f"Failed WebDriver init via manager and fallback.")
                 print(Fore.RED + f"CRITICAL ERROR: Unable to initialize WebDriver.")
                 return # Exit main
        logging.info("WebDriver initialization complete.")


        # --- Batch Loop ---
        while urls_processed_in_run < total_urls_to_run:
            current_batch_num += 1
            # batch_start_index is relative to urls_to_process_all
            batch_start_index = urls_processed_in_run
            batch_size_this_run = default_batch_size

            # --- Determine Batch Size ---
            # (Remains the same)
            if run_in_batches and total_urls_to_run > default_batch_size:
                 remaining_urls = total_urls_to_run - urls_processed_in_run
                 prompt_default = min(default_batch_size, remaining_urls)
                 prompt_batch = ( f"{Fore.CYAN}\n--- Batch {current_batch_num} --- ({urls_processed_in_run}/{total_urls_to_run} processed)\n"
                    # ... rest of prompt ...
                    f"Enter number (or 0/blank for default {prompt_default}), 'n' or 'q' to quit: {Style.RESET_ALL}" )
                 try:
                     user_batch_input = input(prompt_batch).strip().lower()
                     if user_batch_input in ['n', 'q', 'no', 'quit']: break
                     elif not user_batch_input or user_batch_input == '0': batch_size_this_run = prompt_default
                     else:
                         try: requested_batch_size = int(user_batch_input); batch_size_this_run = min(requested_batch_size, remaining_urls) if requested_batch_size > 0 else prompt_default
                         except ValueError: batch_size_this_run = prompt_default
                 except EOFError: break
            else: batch_size_this_run = total_urls_to_run - urls_processed_in_run
            if batch_size_this_run <= 0: break

            # --- Prepare & Process Batch ---
            batch_end_index = batch_start_index + batch_size_this_run
            urls_batch = urls_to_process_all[batch_start_index:batch_end_index]
            batch_metadata_list: List[Dict[str, Any]] = []
            print(Style.BRIGHT + Fore.MAGENTA + f"\nStarting Batch {current_batch_num} ({batch_size_this_run} URLs)...")

            for idx_in_batch, url in enumerate(urls_batch, start=1):
                # *** Corrected Original Index Calculation for Progress Message ***
                # Calculate index relative to the original list read from file
                # It's the start_at offset + the index within the current run's list (urls_to_process_all)
                # The index within urls_to_process_all is batch_start_index + idx_in_batch - 1
                original_index_from_file = start_at_index + batch_start_index + idx_in_batch - 1

                print(Style.BRIGHT + Fore.GREEN +
                      # Use corrected original index calculation (+1 for 1-based display)
                      f"\nProcessing URL {idx_in_batch}/{batch_size_this_run} "
                      f"(Run total: {urls_processed_in_run + idx_in_batch}/{total_urls_to_run}, "
                      f"Original list #: {original_index_from_file + 1}): {url}" + Style.RESET_ALL)

                metadata = extract_metadata(url, driver, ssl_decision, settings)
                if metadata: batch_metadata_list.append(metadata)
                # (Console output...)
                if metadata.get("IA error"): print(Fore.YELLOW + f"  Warning/Error noted: {metadata['IA error']}")
                else: print(Fore.CYAN + f"  Successfully processed.")

                # --- Inter-Request Delay ---
                if idx_in_batch < batch_size_this_run and inter_request_delay > 0:
                     logging.debug(f"Waiting {inter_request_delay}s...")
                     time.sleep(inter_request_delay)

            # --- Save Output for Batch ---
            # (Remains the same)
            if batch_metadata_list:
                output_dir = os.path.join(output_base_dir, output_subfolder)
                first_url_for_filename = urls_batch[0] if urls_batch else f"batch_{current_batch_num}"
                sanitised_domain = sanitise_domain(first_url_for_filename)
                file_ext = output_format.lower()
                batch_suffix = f"_batch_{current_batch_num}" if run_in_batches and total_urls_to_run > default_batch_size else ""
                output_filename = f"page_details_{sanitised_domain}_{base_timestamp}{batch_suffix}.{file_ext}"
                output_path = os.path.join(output_dir, output_filename)
                fieldnames = [ # Keep consistent fieldnames
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

    # (Outer exception handling and finally block remain the same)
    except Exception as e:
        logging.critical(f"A critical error occurred: {e}", exc_info=True)
        print(Fore.RED + Style.BRIGHT + f"\n--- A critical error occurred ---")
        print(Fore.RED + f"Error: {e}")
    finally:
        if driver:
            try:
                logging.info("Attempting to quit WebDriver...")
                driver.quit()
                print(Fore.CYAN + "WebDriver closed.")
            except Exception as e:
                logging.error(f"Error quitting WebDriver: {e}")
                print(Fore.RED + f"Error quitting WebDriver: {e}")
        print(Style.BRIGHT + Fore.MAGENTA + "\nScript finished.")


if __name__ == "__main__":
    main()