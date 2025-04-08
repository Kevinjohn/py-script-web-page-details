# Web Page Metadata Extractor

## Description

This Python script iterates through a list of URLs provided in an input file (`input_urls.txt`). For each URL, it fetches the page using Selenium, extracts various metadata elements (like title, meta description, headings, link counts, image counts), and saves the collected data into a timestamped CSV file.

The script attempts to dynamically find the main content area based on a configurable priority list of CSS selectors (defaulting to `main`, `div[role='main']`, or a single `article`). It supports User-Agent rotation, configurable waits, and rate limiting.

It is designed with modularity in mind, separating concerns like configuration, web interaction, HTML parsing, and file I/O into different modules within the `src` directory.

## Features

* Reads configuration from `config.yaml`.
* Fetches URLs listed in `input_urls.txt`.
* Uses Selenium (with Chrome) to render pages and extract data.
* **Rotates User-Agents** randomly from a configured list.
* Handles potential SSL certificate errors interactively.
* **Dynamically finds main content scope** based on a configurable selector priority list.
* Extracts common metadata: Title, Description, Keywords, OpenGraph tags.
* Analyzes content within the determined scope for: H1, heading counts, internal/external links, images with/without alt text.
* Includes **configurable delays** after page load and between requests.
* Saves results to a CSV file in `output/metadata_reports/`.
* Provides console feedback during processing.
* Includes visual separators in the code for enhanced readability.

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
    Create a file named `config.yaml` in the project root. This file controls the script's behavior. Here's an example configuration including the new options:
    ```yaml
    settings:
      input_file: "input_urls.txt"
      output_base_dir: "output"
      output_subfolder: "metadata_reports"
      log_level: "INFO" # DEBUG, INFO, WARNING, ERROR
      headless: true
      window_width: 1440
      window_height: 1080
      request_max_retries: 3
      request_timeout: 10

      # --- Scope Finding ---
      scope_selectors_priority: # Order matters! Checks for these selectors. 'article' requires unique match.
        - "main"
        - "div[role='main']"
        # - "#content" # Example: Add custom selectors here
        - "article"

      # --- Web Interaction ---
      user_agents: # List of User-Agents to choose from randomly. Leave empty or remove for default Selenium UA.
        - "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        - "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15"
        - "Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0"
      wait_after_load_seconds: 1 # Wait 1 second after page load state 'complete' before parsing. Set to 0 to disable.
      delay_between_requests_seconds: 2 # Wait 2 seconds between processing each URL. Set to 0 to disable.

      # ssl_skip_decision_on_error: false # Interactive prompt usually overrides this
    ```

5.  **Prepare `input_urls.txt`:**
    Create a file named `input_urls.txt` (or whatever you specified in `config.yaml`) in the project root. List the URLs you want to process, one per line. Lines starting with `#` are ignored as comments.
    ```text
    # Example URLs
    [http://your-first-url.com/some/page](http://your-first-url.com/some/page)
    [https://another-domain.org/path/to/resource](https://another-domain.org/path/to/resource)
    # [https://www.example.net/commented/out](https://www.example.net/commented/out)
    ```

## Running the Script

Ensure your virtual environment is activated. Navigate to the project's root directory in your terminal and run the script using the `-m` flag to treat `src` as a package:

```bash
python -m src.main