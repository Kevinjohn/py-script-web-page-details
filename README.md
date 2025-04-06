# py-script-web-page-details


# Web Page Metadata Extractor

This Python script extracts metadata from web pages. It uses libraries like `requests`, `BeautifulSoup4`, and `Selenium` to fetch web pages, parse their HTML, and extract information such as titles, descriptions, headings, links, and more.

## Table of Contents

1.  [Project Description](#project-description)
2.  [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Installation](#installation)
3.  [Configuration](#configuration)
4.  [Usage](#usage)
5.  [File Structure](#file-structure)
6.  [Running Tests](#running-tests)
7.  [Contributing](#contributing)
8.  [License](#license)

## 1. Project Description <a name="project-description"></a>

This project provides a Python script to automate the extraction of metadata from a list of URLs. Metadata is "data about data," and in the context of web pages, it includes information embedded in the HTML that describes the page's content. This script can be useful for:

* SEO analysis: Gathering data about page titles, descriptions, and keywords.
* Content analysis: Counting headings, links, and images on a page.
* Data collection: Building a dataset of web page information.

The script takes a list of URLs as input, processes each URL, and saves the extracted metadata to a CSV (Comma Separated Values) file. CSV files can be easily opened in spreadsheet applications like Excel or Google Sheets.

## 2. Getting Started <a name="getting-started"></a>

### 2.1 Prerequisites <a name="prerequisites"></a>

Before you can run this script, you need to make sure you have the following software installed on your computer:

* **Python:** This script is written in Python. You'll need Python 3.x installed. You can download Python from the official website: \[https://www.python.org/downloads/\](https://www.python.org/downloads/)

    * To check if you have Python installed, open your terminal or command prompt and type:

        ```bash
        python --version
        ```

        or

        ```bash
        python3 --version
        ```

    * This should display the Python version. If you get an error, Python is not installed or not added to your system's PATH.

* **pip:** Python comes with `pip`, which is a package installer. We'll use `pip` to install the necessary Python libraries.

    * To check if you have pip installed, type in your terminal:

        ```bash
        pip --version
        ```

        or

        ```bash
        pip3 --version
        ```

* **Google Chrome:** This script uses Selenium to automate web browser actions, and it's currently configured to use Google Chrome. Please ensure you have Google Chrome installed. You can download it from: \[https://www.google.com/chrome/\](https://www.google.com/chrome/)

### 2.2 Installation <a name="installation"></a>

Follow these steps to set up the project:

1.  **Clone the Repository (Download the Code):**

    * If you're familiar with Git, you can clone the repository to your local machine. Open your terminal, navigate to the directory where you want to save the project, and type:

        ```bash
        git clone [repository URL]  # Replace [repository URL] with the actual URL
        ```

    * If you don't use Git, you can download the project as a ZIP file from the repository hosting service (e.g., GitHub, GitLab) and extract it to a folder on your computer.

2.  **Navigate to the Project Directory:**

    * Use the `cd` command in your terminal to go into the project's main folder. For example, if the folder is named `web-metadata-extractor`, type:

        ```bash
        cd web-metadata-extractor
        ```

3.  **Create a Virtual Environment (Recommended):**

    * A virtual environment creates an isolated Python environment for your project. This helps to avoid conflicts with other Python projects on your system.
    * To create a virtual environment, type:

        ```bash
        python -m venv venv  # This creates a folder named "venv" (you can name it differently)
        ```

    * Activate the virtual environment:
        * On macOS and Linux:

            ```bash
            source venv/bin/activate
            ```

        * On Windows:

            ```bash
            venv\Scripts\activate
            ```

    * Once activated, you'll see the virtual environment's name (e.g., `(venv)`) at the beginning of your terminal prompt.

4.  **Install the Required Libraries:**

    * We'll use `pip` to install the libraries that the script needs. The list of libraries is specified in the `requirements.txt` file.
    * Make sure your virtual environment is activated (if you created one), and then type:

        ```bash
        pip install -r requirements.txt
        ```

    * This will install libraries like:
        * `selenium`: For automating web browsers.
        * `webdriver_manager`: To automatically manage the ChromeDriver (used by Selenium).
        * `beautifulsoup4`: For parsing HTML.
        * `requests`: For making HTTP requests.
        * `colorama`: For adding color to terminal output.
        * `PyYAML`: For reading the configuration file.

## 3. Configuration <a name="configuration"></a>

The script's settings are managed in a `config.yaml` file. This makes it easy to change parameters without modifying the code directly.

* **`config.yaml`:**

    ```yaml
    settings:
      input_file: "ask-for-input.txt"       # Default file containing URLs
      output_base_dir: "E:\\python_output"   # Base directory for output CSV files
      output_subfolder: "_output"           # Subfolder within the base directory
      log_level: "ERROR"                   # Logging level (e.g., DEBUG, INFO, ERROR)
      headless: True                       # Run Chrome in headless mode (no GUI)
      window_width: 1440                   # Browser window width
      window_height: 1080                  # Browser window height
    ```

    * **`input_file`:** The name of the text file containing the list of URLs to process (one URL per line). If this file is not found, the script will prompt you to enter a valid file path.
    * **`output_base_dir`:** The main directory where the output CSV files will be saved.
    * **`output_subfolder`:** A subdirectory within `output_base_dir` to organize the output files.
    * **`log_level`:** Controls the verbosity of logging messages.  `ERROR` means only error messages are shown.  Other options include `DEBUG`, `INFO`, `WARNING`, and `CRITICAL`.
    * **`headless`:** If set to `True`, Chrome will run in "headless" mode, meaning it won't open a visible browser window. This is useful for running the script in the background. If set to `False`, you will see the Chrome browser window open and navigate to the pages.
    * **`window_width`** and **`window_height`:** Sets the size of the Chrome browser window. This can be important for how websites render.

**Important:** Update the `output_base_dir` in `config.yaml` to a directory that exists on your system.

## 4. Usage <a name="usage"></a>

1.  **Prepare the Input File:**

    * Create a text file (e.g., `urls.txt`) with one URL per line. For example:

        ```text
        [https://www.example.com/page1](https://www.example.com/page1)
        [https://www.example.com/page2](https://www.google.com/search?q=https://www.example.com/page2)
        [https://www.example.org/blog](https://www.google.com/search?q=https://www.example.org/blog)
        ```

    * Make sure the file name matches the `input_file` setting in `config.yaml` (or be prepared to provide the correct file path when prompted).

2.  **Run the Script:**

    * Open your terminal or command prompt.
    * Navigate to the project's root directory.
    * Make sure your virtual environment is activated (if you created one).
    * Execute the script using the following command:

        ```bash
        python -m src.py_script_web_page_details
        ```

    * The script will start processing the URLs. It will display progress messages in the terminal.
    * You'll be prompted to enter how many URLs you want to process. Enter 0 or leave it blank to process all URLs in the input file.

3.  **Find the Output:**

    * The extracted metadata will be saved in a CSV file.
    * The location of the CSV file will be:
        * The directory specified in `output_base_dir` in the `config.yaml` file.
        * Within a subdirectory named as specified in `output_subfolder` in the `config.yaml` file.
    * The CSV file will be named something like `page_details_example_com_2023-10-27_101530.csv` (it will include the domain name and a timestamp).

## 5. File Structure <a name="file-structure"></a>

Here's a breakdown of the project's file structure: