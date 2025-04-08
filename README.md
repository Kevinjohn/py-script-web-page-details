# Web Page Metadata Extractor

## Description

This Python script iterates through a list of URLs provided in an input file (`input_urls.txt`). For each URL, it fetches the page using Selenium, extracts various metadata elements (like title, meta description, headings, link counts, image counts), and saves the collected data into a timestamped CSV file.

The script is designed with modularity in mind, separating concerns like configuration, web interaction, HTML parsing, and file I/O into different modules within the `src` directory.

## Features

* Reads configuration from `config.yaml`.
* Fetches URLs listed in `input_urls.txt`.
* Uses Selenium (with Chrome) to render pages and extract data.
* Handles potential SSL certificate errors interactively.
* Extracts common metadata: Title, Description, Keywords, OpenGraph tags.
* Analyzes content within the `<article>` tag (configurable) for: H1, heading counts, internal/external links, images with/without alt text.
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
    *(This will install all libraries listed in `requirements.txt`)*

4.  **Configure `config.yaml`:**
    Create a file named `config.yaml` in the project root. This file controls the script's behavior. Here's an example configuration:
    ```yaml
    settings:
      input_file: "input_urls.txt"       # Path to the file containing URLs
      output_base_dir: "output"         # Base directory for output files
      output_subfolder: "metadata_reports" # Subfolder within output_base_dir
      log_level: "INFO"                 # Logging level (DEBUG, INFO, WARNING, ERROR)
      headless: true                    # Run Chrome in headless mode (true/false)
      window_width: 1440                # Browser window width if not headless
      window_height: 1080               # Browser window height if not headless
      request_max_retries: 3            # Max retries for initial HEAD request
      request_timeout: 10               # Timeout in seconds for HEAD request
      # skip_ssl_check_on_error: false  # Note: Interactive prompt overrides this
    ```

5.  **Prepare `input_urls.txt`:**
    Create a file named `input_urls.txt` (or whatever you specified in `config.yaml`) in the project root. List the URLs you want to process, one per line. Lines starting with `#` are ignored as comments.
    ```text
    # Example URLs
    * https://www.example.com/page1
    * https://www.example.org/another/page
    * *https://www.example.net/commented/out
    ```

## Running the Script

Ensure your virtual environment is activated. Navigate to the project's root directory in your terminal and run the script using the `-m` flag to treat `src` as a package:

```bash
python -m src.main
```

The script will:
* Read the configuration.
* Read the URLs from the input file.
* Optionally prompt you for how many URLs to process.
* Initialize the Selenium WebDriver (this might take a moment the first time as it downloads the driver if needed).
* Process each URL, printing progress to the console.
* Save the results upon completion.

## Output

The script will create a CSV file inside the directory specified by `output_base_dir` / `output_subfolder` in your `config.yaml` (default is `output/metadata_reports/`).

The filename will be in the format: `page_details_<sanitised_domain>_<YYYYMMDD_HHMMSS>.csv`.
`<sanitised_domain>` is derived from the first URL processed.

The CSV file contains columns for all the extracted metadata points (e.g., `http-code`, `Page-URL`, `Title`, `Description`, `Article H1`, `Article Links Internal`, etc.).

## Project Structure

```
your_project_root/
├── src/                  # Main source code
│   ├── __init__.py
│   ├── config_loader.py
│   ├── web_utils.py
│   ├── html_parser.py
│   ├── file_io.py
│   ├── orchestrator.py
│   └── main.py
├── venv/                 # Virtual environment directory (if created)
├── config.yaml           # Configuration file
├── input_urls.txt        # List of URLs to process
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── output/               # Output directory (created by the script)
    └── metadata_reports/ # Subdirectory for reports (created by the script)
```