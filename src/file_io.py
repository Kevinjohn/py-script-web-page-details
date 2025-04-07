# src/file_io.py
import os
import csv
import logging
from urllib.parse import urlparse
from typing import List, Dict, Any
from colorama import Fore, Style # For prompts

def read_input_file(input_file_path: str) -> List[str]:
    """
    Reads URLs from a specified input file, one URL per line.
    If the initial path is invalid, prompts the user for a correct path.

    Args:
        input_file_path: The initial path to the input file (from config).

    Returns:
        A list of valid URLs found in the file. Returns empty list on critical error or if user enters no path.
    """
    current_path = input_file_path
    while not os.path.exists(current_path):
        logging.warning(f"Input file specified not found: {current_path}")
        print(Fore.YELLOW + f"Input file specified ('{current_path}') not found.")
        try:
            new_path = input(Fore.CYAN + "Please enter the correct path to the input URL file (or press Enter to exit): " + Style.RESET_ALL).strip()
            if not new_path:
                 print(Fore.RED + "No path entered. Exiting.")
                 return [] # Exit if user provides no path
            current_path = new_path
        except EOFError: # Handle case where input stream is closed (e.g., piping)
            print(Fore.RED + "\nInput stream closed. Exiting.")
            return []


    urls: List[str] = []
    try:
        with open(current_path, "r", encoding="utf-8") as file:
            for i, line in enumerate(file):
                url = line.strip()
                if url and not url.startswith('#'): # Skip empty lines and comments
                    parsed = urlparse(url)
                    if parsed.scheme in ["http", "https"]: # Basic URL validation
                        urls.append(url)
                    else:
                        logging.warning(f"Skipping invalid or non-HTTP(S) line {i+1} in input file: {url}")
                elif url.startswith('#'):
                     logging.debug(f"Skipping comment line {i+1} in input file: {url}")

        logging.info(f"Read {len(urls)} valid URLs from {current_path}")
        if not urls:
            logging.warning(f"No valid URLs found in {current_path}.")
            print(Fore.YELLOW + f"Warning: No valid URLs found in the input file: {current_path}")
        return urls
    except IOError as e:
        logging.error(f"Error reading input file {current_path}: {e}")
        print(Fore.RED + f"Error reading file: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error reading input file {current_path}: {e}", exc_info=True)
        print(Fore.RED + f"An unexpected error occurred reading the file: {e}")
        return []


def sanitise_domain(url: str) -> str:
    """
    Extracts and sanitises the domain name from a URL for use in filenames.

    Args:
        url: The URL string.

    Returns:
        A sanitised domain name (e.g., 'www_example_com') or 'unknown_domain'.
    """
    try:
        domain = urlparse(url).netloc
        if not domain:
             # Fallback for file:/// URLs or invalid URLs
             path_part = os.path.basename(urlparse(url).path)
             domain = path_part if path_part else "unknown_domain"

        # Replace common invalid filename characters (add more if needed)
        sanitised = domain.replace(".", "_").replace(":", "_").replace("/", "_").replace("\\", "_")
        # Remove any remaining potentially problematic chars (example: keep only alphanum, underscore, hyphen)
        sanitised = "".join(c for c in sanitised if c.isalnum() or c in ['_', '-']).strip('_')

        return sanitised if sanitised else "unknown_domain"
    except Exception as e:
        logging.warning(f"Error sanitising domain for {url}: {e}")
        return "unknown_domain"


def write_to_csv(file_path: str, data: List[Dict[str, Any]], fieldnames: List[str]) -> bool:
    """
    Writes a list of dictionaries to a CSV file. Creates directory if needed.

    Args:
        file_path: The full path to the output CSV file.
        data: A list of dictionaries, where each dictionary represents a row.
        fieldnames: A list of strings defining the header row and column order.

    Returns:
        True if writing was successful, False otherwise.
    """
    if not data:
        logging.warning("No data provided to write to CSV.")
        print(Fore.YELLOW + "No data was extracted to write to the CSV file.")
        return False # Indicate nothing was written
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(file_path)
        if not os.path.exists(output_dir):
             logging.info(f"Creating output directory: {output_dir}")
             os.makedirs(output_dir, exist_ok=True)

        logging.info(f"Attempting to write {len(data)} rows to {file_path} with headers: {fieldnames}")
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            # Use extrasaction='ignore' to prevent errors if data dicts have extra keys
            # Use restval='' to write empty string for missing fields
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore', restval='')
            writer.writeheader()
            writer.writerows(data)
        logging.info(f"Successfully wrote {len(data)} rows to {file_path}")
        return True
    except IOError as e:
        logging.error(f"Error writing to CSV file {file_path}: {e}", exc_info=True)
        print(Fore.RED + f"Error writing to CSV file {file_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error writing CSV {file_path}: {e}", exc_info=True)
        print(Fore.RED + f"An unexpected error occurred writing the CSV: {e}")
        return False