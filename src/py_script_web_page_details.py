import os
import time
import csv
import logging
from datetime import datetime
from urllib.parse import urlparse
import requests
from requests.exceptions import RequestException, SSLError
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from colorama import init, Fore, Style
import yaml  # Import PyYAML

# Initialise Colorama
init(autoreset=True)

# Load Configuration
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

# Configuration Variables
INPUT_FILE = config["settings"]["input_file"]
OUTPUT_BASE_DIR = config["settings"]["output_base_dir"]
OUTPUT_SUBFOLDER = config["settings"]["output_subfolder"]


# Configure logging
log_level_str = config["settings"]["log_level"]
log_level = getattr(logging, log_level_str.upper(), logging.ERROR)  # Default to ERROR
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')



SKIP_SSL_CHECK = False  # Global flag


def fetch_http_status_and_type(url, max_retries=3):
    """Fetch the HTTP status code and content type using requests with retries and SSL error handling."""
    global SKIP_SSL_CHECK
    for attempt in range(max_retries):
        try:
            response = requests.head(url, allow_redirects=True, timeout=10,
                                     verify=not SKIP_SSL_CHECK)  # Use global flag
            http_code = response.status_code
            content_type = response.headers.get("Content-Type", "Unknown")
            return http_code, content_type.split(";")[0]
        except SSLError as ssl_err:
            logging.error(f"SSL error for {url}: {ssl_err}")
            if not SKIP_SSL_CHECK:
                answer = input(
                    Fore.YELLOW + "SSL error encountered. Do you want to skip SSL verification for all future URLs? (y/n): ").strip().lower()
                if answer == 'y':
                    SKIP_SSL_CHECK = True
                else:
                    return "SSL Error", "Unknown"  # Or raise an exception
        except RequestException as e:
            logging.error(f"Request error for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retrying
            else:
                return "Unknown", "Unknown"  # Return a default or raise an exception
    return "Unknown", "Unknown"  # Return after all retries fail


def extract_content_count(soup):
    """Placeholder function to calculate content count."""
    try:
        # Implementation to be added later
        return None
    except Exception as e:
        logging.error(f"Error in extract_content_count: {e}")
        return None


def extract_content_ratio(soup):
    """Placeholder function to calculate content ratio."""
    try:
        # Implementation to be added later
        return None
    except Exception as e:
        logging.error(f"Error in extract_content_ratio: {e}")
        return None


def fetch_and_parse_html(url, driver):
    """Fetches the HTML content of a URL and parses it with BeautifulSoup."""
    try:
        driver.get(url)
        time.sleep(7)  # Allow page to load
        return BeautifulSoup(driver.page_source, "html.parser")
    except Exception as e:
        logging.error(f"Error fetching or parsing {url}: {e}")
        return None


def extract_meta_data(soup):
    """Extracts meta tags from the BeautifulSoup object."""
    try:
        title = extract_meta_title(soup)
        meta_description = extract_meta_content(soup, "description")
        meta_keywords = extract_meta_content(soup, "keywords")
        og_type = extract_meta_content(soup, "og:type")
        og_image = extract_meta_content(soup, "og:image")
        og_title = extract_meta_content(soup, "og:title")
        og_description = extract_meta_content(soup, "og:description")
        return {
            "Title": title,
            "Description": meta_description,
            "Keywords": meta_keywords,
            "Opengraph type": og_type,
            "Opengraph image": og_image,
            "Opengraph title": og_title,
            "Opengraph description": og_description,
        }
    except Exception as e:
        logging.error(f"Error extracting meta data: {e}")
        return {}


def extract_article_data(soup, url):
    """Extracts article-specific data (headings, links, images) from the BeautifulSoup object."""
    try:
        article_h1 = extract_h1(soup)
        article_headings = count_headings(soup)
        article_links_internal = count_internal_links(soup, url)
        article_links_external = count_external_links(soup, url)
        article_images = count_images(soup)
        article_images_no_alt = count_images_no_alt(soup)
        return {
            "Article H1": article_h1,
            "Article Headings": article_headings,
            "Article Links Internal": article_links_internal,
            "Article Links External": article_links_external,
            "Article Images": article_images,
            "Article Images NoAlt": article_images_no_alt,
        }
    except Exception as e:
        logging.error(f"Error extracting article data: {e}")
        return {}


def extract_metadata(url, driver):
    """Orchestrates the extraction of all metadata."""
    try:
        http_code, http_type = fetch_http_status_and_type(url)
        page_slug = extract_page_slug(url)

        if "html" not in http_type.lower():
            return {
                "http-code": http_code,
                "http-type": http_type,
                "Page-URL": url,
                "Page-id": "",
                "page-slug": page_slug,
                "content-count": "",
                "content-ratio": "",
                "Parent-ID": "",
                "Parent-URL": "",
                "IA error": "",
            }

        soup = fetch_and_parse_html(url, driver)
        if not soup:
            return None  # Or return a default dict with error info

        meta_data = extract_meta_data(soup)
        article_data = extract_article_data(soup, url)
        page_id = extract_body_class(soup, "page-id-")
        parent_id = extract_body_class(soup, "parent-pageid-", default="0")
        content_count = extract_content_count(soup)
        content_ratio = extract_content_ratio(soup)

        return {
            "http-code": http_code,
            "http-type": http_type,
            "Page-URL": url,
            "Page-id": page_id,
            "page-slug": page_slug,
            "content-count": content_count,
            "content-ratio": content_ratio,
            "Parent-ID": parent_id,
            "Parent-URL": "",
            "IA error": "",
            **meta_data,
            **article_data,
        }
    except Exception as e:
        logging.error(f"Error in extract_metadata: {e}")
        return None


def extract_page_slug(url):
    """Extract the page slug from the URL."""
    try:
        path = urlparse(url).path  # Extract the path from the URL
        slug = path.rstrip("/").split("/")[-1]  # Get the last part of the path
        return slug if slug else "homepage"  # Return 'homepage' if the slug is empty
    except Exception as e:
        logging.error(f"Error in extract_page_slug: {e}")
        return "unknown"


def extract_body_class(soup, prefix, default=None):
    """Extract specific class value from the body tag."""
    try:
        body = soup.body
        if body and body.has_attr("class"):
            for cls in body["class"]:
                if cls.startswith(prefix):
                    return cls.replace(prefix, "")
        return default
    except Exception as e:
        logging.error(f"Error in extract_body_class: {e}")
        return default


def extract_meta_content(soup, meta_name):
    """Extract content from a meta tag."""
    try:
        tag = soup.find("meta", attrs={"name": meta_name}) or soup.find(
            "meta", attrs={"property": meta_name})
        return tag["content"] if tag and "content" in tag.attrs else ""
    except Exception as e:
        logging.error(f"Error in extract_meta_content: {e}")
        return ""


def extract_meta_title(soup):
    """Extract the title from the <title> tag."""
    try:
        return soup.title.string.strip() if soup.title else ""
    except Exception as e:
        logging.error(f"Error in extract_meta_title: {e}")
        return ""


def extract_h1(soup):
    """Extract the text of the first H1 tag inside an article."""
    try:
        article = soup.find("article")
        if article:
            h1 = article.find("h1")
            return h1.text.strip() if h1 else ""
        return ""
    except Exception as e:
        logging.error(f"Error in extract_h1: {e}")
        return ""


def count_headings(soup):
    """Count the number of headings (H1-H6) within an article."""
    try:
        article = soup.find("article")
        if article:
            return len(article.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]))
        return 0
    except Exception as e:
        logging.error(f"Error in count_headings: {e}")
        return 0


def count_internal_links(soup, base_url):
    """Count the number of internal links within an article."""
    try:
        article = soup.find("article")
        if article:
            base_domain = urlparse(base_url).netloc  # Extract domain
            links = article.find_all("a", href=True)
            return sum(1 for link in links if base_domain in link["href"])
        return 0
    except Exception as e:
        logging.error(f"Error in count_internal_links: {e}")
        return 0


def count_external_links(soup, base_url):
    """Count the number of external links within an article."""
    try:
        article = soup.find("article")
        if article:
            base_domain = urlparse(base_url).netloc  # Extract domain
            links = article.find_all("a", href=True)
            return sum(1 for link in links if base_domain not in link["href"])
        return 0
    except Exception as e:
        logging.error(f"Error in count_external_links: {e}")
        return 0


def count_images(soup):
    """Count the number of images within an article."""
    try:
        article = soup.find("article")
        if article:
            return len(article.find_all("img"))
        return 0
    except Exception as e:
        logging.error(f"Error in count_images: {e}")
        return 0


def count_images_no_alt(soup):
    """Count the number of images within an article without alt text."""
    try:
        article = soup.find("article")
        if article:
            images = article.find_all("img")
            return sum(1 for img in images if not img.get("alt"))
        return 0
    except Exception as e:
        logging.error(f"Error in count_images_no_alt: {e}")
        return 0


def read_input_file(input_file):
    """Read URLs from a file."""
    try:
        if not os.path.exists(input_file):
            input_file = input(
                f"{Fore.YELLOW}Default file '{DEFAULT_INPUT_FILE}' not found. Please provide a valid input file path: ").strip()
            while not os.path.exists(input_file):
                input_file = input(Fore.RED + "File not found. Please enter a valid path: ").strip()
        with open(input_file, "r") as file:
            return [url.strip() for url in file if url.strip()]
    except Exception as e:
        logging.error(f"Error in read_input_file: {e}")
        return []


def sanitise_domain(url):
    """Sanitise the domain name from the URL."""
    try:
        domain = urlparse(url).netloc
        return domain.replace(".", "_")
    except Exception as e:
        logging.error(f"Error in sanitise_domain: {e}")
        return "unknown_domain"


def write_to_csv(file_path, data, fieldnames):
    """Write data to a CSV file."""
    try:
        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    except Exception as e:
        logging.error(f"Error in write_to_csv: {e}")


def main():
    """Main script to extract metadata from URLs and save it to a CSV file."""

    try:
        urls = read_input_file(DEFAULT_INPUT_FILE)

        num_to_process = input(
            f"{Fore.CYAN}How many URLs to process? (0 or Enter for all, max {len(urls)}): ").strip()
        num_to_process = int(num_to_process) if num_to_process.isdigit() else 0
        if num_to_process > 0:
            urls = urls[:num_to_process]

        output_dir = os.path.join(OUTPUT_BASE_DIR, OUTPUT_SUBFOLDER)
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        sanitised_domain = sanitise_domain(urls[0]) if urls else "unknown_domain"
        output_csv_file = f"page_details_{sanitised_domain}_{timestamp}.csv"
        output_path = os.path.join(output_dir, output_csv_file)

        options = Options()
        options.add_argument('--headless')  # use old headless
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1440,1080')

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),
                                  options=options)  # Dynamic driver

        metadata_list = []

        for idx, url in enumerate(urls, start=1):
            print(Fore.GREEN + f"Processing ({idx}/{len(urls)}): {url}")
            metadata = extract_metadata(url, driver)
            if metadata:
                metadata_list.append(metadata)

        fieldnames = [
            "http-code", "http-type", "Page-URL", "Page-id", "page-slug", "Title", "Description",
            "Keywords",
            "Opengraph type", "Opengraph image", "Opengraph title", "Opengraph description",
            "Article H1", "Article Headings", "Article Links Internal", "Article Links External",
            "Article Images", "Article ImagesNoAlt", "content-count", "content-ratio",
            "Parent-ID", "Parent-URL", "IA error",
        ]
        write_to_csv(output_path, metadata_list, fieldnames)
        print(Fore.CYAN + f"Metadata saved to {output_path}")

    except Exception as e:
        logging.error(f"An error occurred in the main script: {e}")

    finally:
        if 'driver' in locals():
            driver.quit()
        print(Style.BRIGHT + Fore.CYAN + "Script finished.")


if __name__ == "__main__":
    main()