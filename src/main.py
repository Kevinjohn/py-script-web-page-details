#!/usr/bin/env python3
# src/main.py
import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# Third-party imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from colorama import init, Fore, Style

# --- Import project modules ---
# Initialize colorama *before* other modules that might use it (like file_io for prompts)
init(autoreset=True)

# Now import other modules
from . import config_loader # Import config first to load settings
from .file_io import read_input_file, write_to_csv, sanitise_domain
from .orchestrator import extract_metadata
# Import config variables directly from the loaded config_loader module
from .config_loader import (
    INPUT_FILE, OUTPUT_BASE_DIR, OUTPUT_SUBFOLDER, HEADLESS,
    WINDOW_WIDTH, WINDOW_HEIGHT, setup_logging
)

# --- Main Execution ---

def main() -> None:
    """Main script execution function."""
    # Setup logging after colorama init
    setup_logging() # Explicitly call logging setup
    logging.info("Script starting.")

    # --- Read Input File (includes interactive prompt if needed) ---
    urls = read_input_file(INPUT_FILE)
    if not urls:
        logging.critical("No valid URLs found or provided. Exiting.")
        print(Fore.RED + "Error: No valid URLs found. Check input file and logs, or provide path when prompted.")
        return # Exit if no URLs

    # --- User prompt for number of URLs (optional) ---
    num_to_process = 0 # Default to all
    try:
        prompt = (f"{Fore.CYAN}Found {len(urls)} URLs. "
                  f"How many do you want to process? (Enter 0 or leave blank for all): {Style.RESET_ALL}")
        num_to_process_str = input(prompt).strip()

        if num_to_process_str: # Only parse if input is not empty
            num_to_process = int(num_to_process_str)
            if num_to_process < 0:
                 logging.warning("Negative number entered, processing all URLs.")
                 num_to_process = 0 # Treat negative as 0 (all)
            elif num_to_process == 0:
                 logging.info("Processing all URLs as requested (0 entered).")
            elif num_to_process > len(urls):
                 logging.warning(f"Number entered ({num_to_process}) is more than available URLs ({len(urls)}). Processing all.")
                 num_to_process = 0 # Process all if number > available
            else:
                 urls = urls[:num_to_process]
                 logging.info(f"Processing the first {len(urls)} URLs as requested.")
        else:
             logging.info("Processing all URLs (no number entered).")
             num_to_process = 0 # Explicitly set to 0 for clarity

    except ValueError:
        logging.warning("Invalid input for number of URLs, processing all.")
        num_to_process = 0 # Process all if input is not a valid integer
    except EOFError:
        logging.warning("Input stream closed during prompt, processing all URLs.")
        num_to_process = 0 # Process all if input stream closes


    # --- Setup Output Path ---
    output_dir = os.path.join(OUTPUT_BASE_DIR, OUTPUT_SUBFOLDER)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Use first URL for filename base, handle case where urls might be empty after filtering
    first_url_for_filename = urls[0] if urls else "no_urls_processed"
    sanitised_domain = sanitise_domain(first_url_for_filename)
    output_csv_file = f"page_details_{sanitised_domain}_{timestamp}.csv"
    output_path = os.path.join(output_dir, output_csv_file)
    logging.info(f"Output CSV will be saved to: {output_path}")

    # --- Configure Selenium WebDriver ---
    options = Options()
    if HEADLESS:
        options.add_argument('--headless=new') # Use modern headless
        logging.info("Running WebDriver in headless mode.")
    else:
        logging.info("Running WebDriver in headed mode.")
    options.add_argument('--disable-gpu') # Often needed for headless
    options.add_argument('--no-sandbox') # Often needed in containerized/CI environments
    options.add_argument('--disable-dev-shm-usage') # Overcomes limited resource problems
    options.add_argument(f'--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}')
    # Suppress DevTools listening message (can clutter logs)
    options.add_experimental_option('excludeSwitches', ['enable-logging'])


    driver: Optional[webdriver.Chrome] = None # Initialize driver variable
    metadata_list: List[Dict[str, Any]] = []
    # --- Initialize SSL decision state ---
    # This dictionary will be passed around and potentially modified by fetch_http_status_and_type
    ssl_decision: Dict[str, bool] = {"skip_all": False}

    try:
        logging.info("Initializing WebDriver...")
        print(Fore.YELLOW + "Initializing WebDriver (this might take a moment)...")
        # Ensure the driver is downloaded/updated
        try:
             driver_path = ChromeDriverManager().install()
             service = Service(driver_path)
             driver = webdriver.Chrome(service=service, options=options)
             logging.info(f"WebDriver initialized successfully using driver at: {driver_path}")
             print(Fore.GREEN + "WebDriver initialized.")
        except Exception as wd_init_error:
             logging.critical(f"Failed to initialize WebDriver: {wd_init_error}", exc_info=True)
             print(Fore.RED + f"CRITICAL ERROR: Failed to initialize WebDriver. Check internet connection and ChromeDriver compatibility.")
             print(Fore.RED + f"Error details: {wd_init_error}")
             return # Cannot proceed without driver


        # --- Process URLs ---
        total_urls = len(urls)
        for idx, url in enumerate(urls, start=1):
            print(Style.BRIGHT + Fore.GREEN + f"\nProcessing ({idx}/{total_urls}): {url}" + Style.RESET_ALL)
            # Pass the ssl_decision dictionary down - it might be modified inside
            metadata = extract_metadata(url, driver, ssl_decision)
            if metadata:
                 metadata_list.append(metadata)
                 if metadata.get("IA error"):
                     print(Fore.YELLOW + f"  Warning/Error noted for {url}: {metadata['IA error']}")
                 else:
                     print(Fore.CYAN + f"  Successfully processed {url}")
            else:
                 # Should not happen if extract_metadata always returns a dict, but handle defensively
                 logging.error(f"Critical failure processing {url} - extract_metadata returned None.")
                 metadata_list.append({"Page-URL": url, "IA error": "Critical extraction failure (None returned)"})
                 print(Fore.RED + f"  Critical error processing {url}. Check logs.")


        # --- Define CSV Headers (ensure all keys from result_data in orchestrator are here) ---
        # It's good practice to define this explicitly based on what extract_metadata produces
        fieldnames = [
            "http-code", "http-type", "Page-URL", "page-slug", "Page-id", "Parent-ID",
            "Title", "Description", "Keywords",
            "Opengraph type", "Opengraph image", "Opengraph title", "Opengraph description",
            "Article H1", "Article Headings", "Article Links Internal", "Article Links External",
            "Article Images", "Article Images NoAlt",
            "content-count", "content-ratio",
            "Parent-URL", # Keep if planning to use later
            "IA error", # Important for diagnostics
        ]

        # --- Write Results ---
        if metadata_list:
             if write_to_csv(output_path, metadata_list, fieldnames):
                 print(Fore.CYAN + Style.BRIGHT + f"\nMetadata successfully saved to: {output_path}")
             else:
                 print(Fore.RED + Style.BRIGHT + f"\nFailed to save metadata to CSV. Check logs for file path: {output_path}")
        else:
             print(Fore.YELLOW + "\nNo metadata was collected to write to CSV.")


    except Exception as e:
        # Catch broad exceptions in main loop to log them
        logging.critical(f"A critical error occurred in the main script execution: {e}", exc_info=True)
        print(Fore.RED + Style.BRIGHT + f"\n--- A critical error occurred ---")
        print(Fore.RED + f"Please check the log file for details.")
        print(Fore.RED + f"Error: {e}")

    finally:
        # --- Cleanup ---
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