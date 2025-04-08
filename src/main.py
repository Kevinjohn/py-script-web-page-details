#!/usr/bin/env python3
# src/main.py
import os
import logging
import time
import random
import math # For ceiling division in batching
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
# Updated function name below
from .file_io import read_input_file, write_output_file, sanitise_domain
from .orchestrator import extract_metadata

# ========================================
# Function: main (Updated for Batching, Output Format)
# ========================================
def main() -> None:
    """Main script execution function with batch processing and format options."""
    # --- Load Configuration and Setup Logging ---
    settings = load_configuration("config.yaml")
    log_level_str = settings.get("log_level", DEFAULT_SETTINGS["log_level"])
    setup_logging(log_level_str)

    logging.info("Script starting.")
    logging.debug(f"Using settings (values might be truncated):")
    # (logging loop kept from previous version)
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
    output_format = settings.get("output_format", DEFAULT_SETTINGS["output_format"]) # Get output format
    run_in_batches = settings.get("run_in_batches", DEFAULT_SETTINGS["run_in_batches"]) # Get batch setting
    default_batch_size = settings.get("batch_size", DEFAULT_SETTINGS["batch_size"]) # Get batch size

    # --- Read Input File ---
    urls_all = read_input_file(input_file)
    if not urls_all:
        logging.critical("No valid URLs found or provided. Exiting.")
        print(Fore.RED + "Error: No valid URLs found.")
        return

    total_urls_available = len(urls_all)
    logging.info(f"Total valid URLs available: {total_urls_available}")

    # --- Determine Total URLs to Process (Initial Limit) ---
    urls_to_process_all = urls_all # Start with all URLs
    try:
        prompt = (f"{Fore.CYAN}Found {total_urls_available} URLs. "
                  f"How many TOTAL do you want to process? (Enter 0 or leave blank for all): {Style.RESET_ALL}")
        num_to_process_str = input(prompt).strip()
        if num_to_process_str:
            num_to_process_limit = int(num_to_process_str)
            if 0 < num_to_process_limit < total_urls_available:
                 urls_to_process_all = urls_all[:num_to_process_limit]
                 logging.info(f"Limiting run to the first {len(urls_to_process_all)} URLs based on user input.")
            elif num_to_process_limit <= 0:
                 logging.info("Processing all available URLs (0 or negative entered for total limit).")
            else: # num_to_process >= available
                 logging.info(f"Total limit entered >= available URLs. Processing all {total_urls_available} URLs.")
        else:
             logging.info("Processing all available URLs (no total limit entered).")
    except ValueError:
        logging.warning("Invalid input for total number of URLs, processing all available.")
    except EOFError:
        logging.warning("Input stream closed during total limit prompt, processing all available.")

    total_urls_to_run = len(urls_to_process_all)
    processed_count_total = 0 # Track total processed across batches

    # --- Configure Selenium WebDriver ---
    # (Keep existing setup logic)
    options = Options()
    if headless_mode: options.add_argument('--headless=new')
    # ... other options ...
    options.add_argument(f'--window-size={window_width},{window_height}')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    selected_ua = None
    if user_agents:
        selected_ua = random.choice(user_agents)
        options.add_argument(f'user-agent={selected_ua}')
        logging.info(f"Using User-Agent: {selected_ua}")

    driver: Optional[webdriver.Chrome] = None
    ssl_decision: Dict[str, bool] = {"skip_all": False}

    # --- Main Processing Loop (With Batch Logic) ---
    current_batch_num = 0
    urls_processed_in_run = 0
    base_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") # Timestamp for the whole run

    try:
        # --- Initialize WebDriver (once per run) ---
        logging.info("Initializing WebDriver...")
        print(Fore.YELLOW + "Initializing WebDriver (this might take a moment)...")
        try:
             driver_path = ChromeDriverManager().install()
             service = Service(driver_path)
             driver = webdriver.Chrome(service=service, options=options)
             logging.info(f"WebDriver initialized successfully.")
             print(Fore.GREEN + "WebDriver initialized.")
        except Exception as wd_init_error:
             logging.critical(f"Failed to initialize WebDriver: {wd_init_error}", exc_info=True)
             print(Fore.RED + f"CRITICAL ERROR: Failed to initialize WebDriver.")
             return # Cannot proceed

        # --- Batch Loop ---
        while urls_processed_in_run < total_urls_to_run:
            current_batch_num += 1
            batch_start_index = urls_processed_in_run
            batch_size_this_run = default_batch_size # Start with default

            # --- Determine Batch Size (Interactive if batching enabled) ---
            if run_in_batches:
                remaining_urls = total_urls_to_run - urls_processed_in_run
                prompt_batch = (
                    f"{Fore.CYAN}\n--- Batch {current_batch_num} --- ({urls_processed_in_run}/{total_urls_to_run} processed)\n"
                    f"Process next batch? Max {remaining_urls} remaining.\n"
                    f"Enter number (or 0/blank for default {min(default_batch_size, remaining_urls)}), 'n' or 'q' to quit: {Style.RESET_ALL}"
                )
                try:
                    user_batch_input = input(prompt_batch).strip().lower()
                    if user_batch_input in ['n', 'q', 'no', 'quit']:
                        logging.info("User chose to quit processing batches.")
                        print(Fore.YELLOW + "Exiting batch processing.")
                        break # Exit the while loop
                    elif not user_batch_input or user_batch_input == '0':
                         batch_size_this_run = min(default_batch_size, remaining_urls)
                         logging.info(f"Processing default batch size: {batch_size_this_run}")
                    else:
                         try:
                             requested_batch_size = int(user_batch_input)
                             if requested_batch_size <= 0:
                                 logging.warning("Invalid batch size <= 0 entered, using default.")
                                 batch_size_this_run = min(default_batch_size, remaining_urls)
                             else:
                                 batch_size_this_run = min(requested_batch_size, remaining_urls)
                                 logging.info(f"Processing user-specified batch size: {batch_size_this_run}")
                         except ValueError:
                             logging.warning(f"Invalid batch size input '{user_batch_input}', using default.")
                             batch_size_this_run = min(default_batch_size, remaining_urls)
                except EOFError:
                     logging.warning("Input stream closed during batch prompt, exiting.")
                     print(Fore.YELLOW + "\nInput stream closed, exiting batch processing.")
                     break

            else: # Not running in batches, process all remaining in one go
                batch_size_this_run = total_urls_to_run - urls_processed_in_run
                logging.info(f"Batch processing disabled. Processing all remaining {batch_size_this_run} URLs.")

            if batch_size_this_run <= 0:
                 logging.info("No URLs remaining or selected for this batch. Exiting.")
                 break # Exit if batch size becomes zero

            # --- Prepare Batch ---
            batch_end_index = batch_start_index + batch_size_this_run
            urls_batch = urls_to_process_all[batch_start_index:batch_end_index]
            batch_metadata_list: List[Dict[str, Any]] = []
            print(Style.BRIGHT + Fore.MAGENTA + f"\nStarting Batch {current_batch_num} ({batch_size_this_run} URLs from index {batch_start_index+1} to {batch_end_index})...")


            # --- Process URLs in Batch ---
            for idx_in_batch, url in enumerate(urls_batch, start=1):
                global_idx = batch_start_index + idx_in_batch
                print(Style.BRIGHT + Fore.GREEN +
                      f"\nProcessing URL {idx_in_batch}/{batch_size_this_run} (Overall: {global_idx}/{total_urls_to_run}): {url}" + Style.RESET_ALL)

                metadata = extract_metadata(url, driver, ssl_decision, settings) # Pass settings
                if metadata:
                     batch_metadata_list.append(metadata)
                     if metadata.get("IA error"):
                         print(Fore.YELLOW + f"  Warning/Error noted: {metadata['IA error']}")
                     else:
                         print(Fore.CYAN + f"  Successfully processed.")
                else:
                     logging.error(f"Critical failure processing {url} - extract_metadata returned None.")
                     batch_metadata_list.append({"Page-URL": url, "IA error": "Critical extraction failure (None returned)"})
                     print(Fore.RED + f"  Critical error processing. Check logs.")

                # Inter-Request Delay (apply between URLs within the batch too)
                if idx_in_batch < batch_size_this_run and inter_request_delay > 0:
                     logging.debug(f"Waiting {inter_request_delay}s before next request...")
                     time.sleep(inter_request_delay)

            # --- Save Output for Batch ---
            if batch_metadata_list:
                # Define output path based on batch number
                output_dir = os.path.join(output_base_dir, output_subfolder)
                first_url_for_filename = urls_batch[0] if urls_batch else f"batch_{current_batch_num}"
                sanitised_domain = sanitise_domain(first_url_for_filename)
                file_ext = output_format.lower()
                # Add batch number to filename if batching is enabled
                batch_suffix = f"_batch_{current_batch_num}" if run_in_batches and total_urls_to_run > default_batch_size else "" # Only add suffix if actually batching
                output_filename = f"page_details_{sanitised_domain}_{base_timestamp}{batch_suffix}.{file_ext}"
                output_path = os.path.join(output_dir, output_filename)

                # Define CSV headers (needed even for JSON if we decide to filter later)
                fieldnames = list(EXPECTED_KEYS) # Use keys from orchestrator? Or define here? Define here for now.
                fieldnames = [
                    "http-code", "http-type", "Page-URL", "page-slug", "Page-id", "Parent-ID",
                    "Title", "Description", "Keywords",
                    "Opengraph type", "Opengraph image", "Opengraph title", "Opengraph description",
                    "Article H1", "Article Headings", "Article Links Internal", "Article Links External",
                    "Article Images", "Article Images NoAlt",
                    "content-count", "content-ratio",
                    "Parent-URL", "IA error",
                ]

                # Write using the selected format
                if write_output_file(output_path, batch_metadata_list, fieldnames, output_format):
                    print(Fore.CYAN + Style.BRIGHT + f"\nBatch {current_batch_num} results ({len(batch_metadata_list)} records) saved to: {output_path}")
                else:
                    print(Fore.RED + Style.BRIGHT + f"\nFailed to save results for Batch {current_batch_num}. Check logs.")
            else:
                print(Fore.YELLOW + f"\nNo metadata collected in Batch {current_batch_num} to write.")

            # Update total processed count
            urls_processed_in_run += len(urls_batch)

            # End of batch loop iteration

        # --- End of while loop (all batches done or user quit) ---
        logging.info(f"Finished processing. Total URLs processed in this run: {urls_processed_in_run}")
        print(Fore.GREEN + f"\nFinished processing. Total URLs processed in this run: {urls_processed_in_run}")


    except Exception as e:
        logging.critical(f"A critical error occurred in the main script execution: {e}", exc_info=True)
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