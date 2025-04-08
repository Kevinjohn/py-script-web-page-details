# src/file_io.py
import os
import csv
import json
import logging
from urllib.parse import urlparse, ParseResult
from typing import List, Dict, Any, Optional
from colorama import Fore, Style

# ========================================
# Function: read_input_file (Updated Header Logic)
# Description: Reads URLs from TXT or CSV file, auto-detecting format.
# ========================================
def read_input_file(input_file_path: str) -> List[str]:
    """
    Reads URLs from a specified input file (TXT or CSV), auto-detecting format.
    If the initial path is invalid, prompts the user for a correct path.
    For CSV, assumes URL is in the first column. Skips suspected header rows in CSV.
    For TXT, reads one URL per line, ignoring lines starting with '#'.

    Args:
        input_file_path: The initial path to the input file.

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
                 return []
            current_path = new_path
        except EOFError:
            print(Fore.RED + "\nInput stream closed. Exiting.")
            return []

    urls: List[str] = []
    file_extension = os.path.splitext(current_path)[1].lower()
    is_csv = file_extension == ".csv"
    logging.info(f"Attempting to read URLs from '{current_path}' (Detected format: {'CSV' if is_csv else 'TXT'}).")

    try:
        with open(current_path, "r", encoding="utf-8", newline=('') if is_csv else None) as file:
            if is_csv:
                reader = csv.reader(file)
                for i, row in enumerate(reader):
                    # --- Updated Header Detection Logic ---
                    # Skip if it's the first row (i==0) AND the first cell doesn't look like a URL
                    if row: # Ensure row is not empty first
                         first_cell_lower = str(row[0]).strip().lower()
                         is_potential_header = not (first_cell_lower.startswith('http://') or first_cell_lower.startswith('https://'))
                         if i == 0 and is_potential_header:
                              logging.debug(f"Skipping potential header row in CSV: {row}")
                              continue
                    # --- End Updated Header Detection Logic ---

                    if row: # Check again if row is not empty (might be needed if header logic changes)
                        url = row[0].strip() # Assume URL is in the first column
                        if url and not url.startswith('#'): # Allow comments in CSV too
                            try:
                                parsed = urlparse(url)
                                if parsed.scheme in ["http", "https"]:
                                    urls.append(url)
                                else:
                                    logging.warning(f"Skipping invalid/non-HTTP(S) URL in CSV row {i+1}: {url}")
                            except ValueError:
                                 logging.warning(f"Skipping malformed URL in CSV row {i+1}: {url}")
            else: # Treat as TXT file
                for i, line in enumerate(file):
                    url = line.strip()
                    if url and not url.startswith('#'):
                        try:
                             parsed = urlparse(url)
                             if parsed.scheme in ["http", "https"]:
                                 urls.append(url)
                             else:
                                 logging.warning(f"Skipping invalid/non-HTTP(S) line {i+1} in input file: {url}")
                        except ValueError:
                            logging.warning(f"Skipping malformed URL on line {i+1} in input file: {url}")
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
    except csv.Error as e: # Catch potential CSV specific errors
         logging.error(f"Error reading CSV file {current_path}: {e}")
         print(Fore.RED + f"Error reading CSV data: {e}")
         return []
    except Exception as e:
        logging.error(f"Unexpected error reading input file {current_path}: {e}", exc_info=True)
        print(Fore.RED + f"An unexpected error occurred reading the file: {e}")
        return []

# ========================================
# Function: sanitise_domain
# ========================================
# (No changes from previous version)
def sanitise_domain(url: str) -> str:
    """
    Extracts and sanitises the domain name from a URL for use in filenames.
    Handles http/https URLs and file URLs appropriately.

    Args:
        url: The URL string.

    Returns:
        A sanitised domain name (e.g., 'www_example_com'), a sanitised filename
        for file URLs (e.g., 'file_html'), or 'unknown_domain' for other cases.
    """
    if not isinstance(url, str): return "unknown_domain"
    try:
        parsed_url: ParseResult = urlparse(url)
        domain: Optional[str] = parsed_url.netloc

        if not domain:
            if parsed_url.scheme == 'file':
                path_part = os.path.basename(parsed_url.path)
                sanitised = path_part.replace(".", "_").replace(":", "_").replace("/", "_").replace("\\", "_")
                sanitised = "".join(c for c in sanitised if c.isalnum() or c in ['_', '-']).strip('_')
                return sanitised if sanitised else "unknown_file"
            else:
                return "unknown_domain"
        else:
            sanitised = domain.replace(".", "_").replace(":", "_").replace("/", "_").replace("\\", "_")
            sanitised = "".join(c for c in sanitised if c.isalnum() or c in ['_', '-']).strip('_')
            return sanitised if sanitised else "unknown_domain"

    except Exception as e:
        logging.warning(f"Error sanitising domain for {url}: {e}", exc_info=True)
        return "unknown_domain"

# ========================================
# Function: write_output_file (Replaces write_to_csv)
# Description: Writes data to CSV or JSON file based on specified format.
# ========================================
# (No changes from previous version)
def write_output_file(
    file_path: str,
    data: List[Dict[str, Any]],
    fieldnames: List[str],
    output_format: str
    ) -> bool:
    """
    Writes a list of dictionaries to a file in CSV or JSON format.
    Creates the output directory if it doesn't exist.

    Args:
        file_path: The full path to the output file (extension should match format).
        data: A list of dictionaries, where each dictionary represents a row/object.
        fieldnames: A list of strings defining CSV header or key order (used for CSV only).
        output_format: The desired format ("CSV" or "JSON", case-insensitive).

    Returns:
        True if writing was successful, False otherwise.
    """
    if not data:
        logging.warning("No data provided to write to output file.")
        print(Fore.YELLOW + "No data was extracted to write to the output file.")
        return False

    try:
        output_dir = os.path.dirname(file_path)
        if output_dir and not os.path.exists(output_dir):
             logging.info(f"Creating output directory: {output_dir}")
             os.makedirs(output_dir, exist_ok=True)

        normalized_format = output_format.upper()
        logging.info(f"Attempting to write {len(data)} records to {file_path} in {normalized_format} format.")

        if normalized_format == "CSV":
            with open(file_path, "w", newline="", encoding="utf-8") as outfile:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames, extrasaction='ignore', restval='')
                writer.writeheader()
                writer.writerows(data)
            logging.info(f"Successfully wrote {len(data)} rows to CSV: {file_path}")
            return True

        elif normalized_format == "JSON":
            with open(file_path, "w", encoding="utf-8") as outfile:
                json.dump(data, outfile, indent=4, ensure_ascii=False)
            logging.info(f"Successfully wrote {len(data)} records to JSON: {file_path}")
            return True

        else:
            logging.error(f"Unsupported output format requested: {output_format}")
            print(Fore.RED + f"Error: Unsupported output format specified '{output_format}'. Please use CSV or JSON.")
            return False

    except IOError as e:
        logging.error(f"Error writing to output file {file_path}: {e}", exc_info=True)
        print(Fore.RED + f"Error writing to file {file_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error writing output file {file_path}: {e}", exc_info=True)
        print(Fore.RED + f"An unexpected error occurred writing the output file: {e}")
        return False