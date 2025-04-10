# Web Page Metadata Extractor

## Description

This Python script iterates through a list of URLs provided in an input file (`input_urls.txt` or `.csv`). For each URL, it fetches the page using Selenium, extracts various metadata elements (like title, meta description, headings, link counts, image counts), and saves the collected data into a timestamped CSV or JSON file.

The script attempts to dynamically find the main content area based on a configurable priority list of CSS selectors (defaulting to `main`, `div[role='main']`, or a single `article`). It supports User-Agent rotation, configurable waits, rate limiting between requests, optional starting offset, batch processing, and fallback to a manually specified ChromeDriver path.

It is designed with modularity in mind, separating concerns like configuration, URL utilities, web interaction, HTML parsing (scope finding, metadata, content, page attributes), and file I/O into different modules.

## Features

* Reads configuration from `config.yaml`.
* Reads URLs from `.txt` or `.csv` files (auto-detects format).
* **Optional `start_at`** setting to skip initial URLs.
* Uses Selenium (with Chrome) to render pages and extract data.
* **Optional fallback** to manually specified `chromedriver_path` if `webdriver-manager` fails.
* Rotates User-Agents randomly from a configured list.
* Handles potential SSL certificate errors interactively (during initial HEAD request).
* Dynamically finds main content scope based on a configurable selector priority list (falls back to `<body>`).
* Extracts common metadata: Title, Description, Keywords, OpenGraph tags.
* Analyzes content within the determined scope for: H1, heading counts, internal/external links, images with/without alt text.
* Includes configurable delays after page load and between requests (rate limiting).
* **Optional interactive batch processing** with configurable default batch size.
* Saves results to **CSV or JSON** format (configurable).
* Creates timestamped output files (one per run, or per batch if batching is active).
* Provides console feedback during processing.
* Includes visual separators in the source code for enhanced readability.

## Setup and Installation

1.  **Clone the Repository (Example):**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-directory>
    ```

2.  **Create and Activate Virtual Environment (Recommended):**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(This will install all libraries listed in `requirements.txt`, including `pytest-mock` if you are running tests)*

4.  **Configure `config.yaml`:**
    Create a file named `config.yaml` in the project root. This file controls the script's behavior. Here's an example configuration including all current options:
    ```yaml
    # Example configuration for the Web Page Metadata Extractor script
    settings:
      # --- Input/Output ---
      input_file: "input_urls.txt"         # Path to file with URLs (TXT or CSV auto-detected)
      output_base_dir: "output"          # Base directory for output files
      output_subfolder: "metadata_reports" # Subfolder within output_base_dir
      output_format: "CSV"               # Output format: "CSV" or "JSON"

      # --- Logging ---
      log_level: "INFO"                  # DEBUG, INFO, WARNING, ERROR, CRITICAL

      # --- Browser/Fetching ---
      headless: true                     # Run Chrome in headless mode (true/false)
      window_width: 1440                 # Browser window width if not headless
      window_height: 1080                # Browser window height if not headless
      request_max_retries: 3             # Max retries for initial HEAD request if connection fails
      request_timeout: 10                # Timeout in seconds for initial HEAD request
      user_agents: # List of User-Agents to choose from randomly. Leave empty or comment out for default.
        - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15"
        - "Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0"
      # skip_ssl_check_on_error: false   # Usually handled by interactive HEAD request prompt if applicable
      chromedriver_path: ""              # Optional: FULL path to specific chromedriver executable if webdriver-manager fails or is bypassed. Leave empty to rely on manager first.

      # --- Parsing & Timing ---
      scope_selectors_priority:          # Order matters! Checks for these selectors for main content. 'article' requires unique match.
        - "main"
        - "div[role='main']"
        # - "#content"                   # Example: Add custom selectors here if needed
        - "article"
      wait_after_load_seconds: 0         # Wait N seconds after page load state 'complete' before parsing. Set to 0 to disable.
      delay_between_requests_seconds: 1  # Wait N seconds between processing each URL. Set to 0 to disable.

      # --- Processing Control ---
      start_at: 0                        # Optional: Skip the first N URLs (0-based index, e.g., 0 starts from first, 5 skips first 5)
      run_in_batches: false              # Set to true to enable interactive batch processing
      batch_size: 50                     # Default number of URLs per batch if batching is enabled

    ```

5.  **Prepare Input File (`input_urls.txt` or `input_urls.csv`):**
    * Create the input file specified in `config.yaml`.
    * **TXT Format:** List URLs one per line. Lines starting with `#` are ignored.
    * **CSV Format:** List URLs in the *first column*. The script will attempt to skip a header row if the first cell doesn't look like a URL (doesn't start with `http`). Other columns are ignored. Lines where the first column starts with `#` are ignored.
    ```text
    # --- Example input.txt ---
    # Comment line
    [https://example.com/page1](https://example.com/page1)
    [https://example.org/page2](https://example.org/page2)

    # --- Example input.csv ---
    # URL,Optional Info Column
    # [https://example.com/page1,Some](https://example.com/page1,Some) info
    # [https://example.org/page2,More](https://example.org/page2,More) info
    ```


## Running the Script

Ensure your virtual environment is activated. Navigate to the project's root directory in your terminal and run the script using the `-m` flag to treat `src` as a package:

```bash
python -m src.main