import os
import re
import time

import pdfkit
import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://www.info.gov.hk"
OUTPUT_DIR = "Tai_Po_Fire_Press_Releases_Bilingual"

# Search Configuration
SEARCH_CONFIG = [{"lang": "ENG", "url_template": "https://www.info.gov.hk/gia/general/202512/{day}.htm", "keywords": ["tai po", "fire"]}, {"lang": "CHI", "url_template": "https://www.info.gov.hk/gia/general/202512/{day}c.htm", "keywords": ["大埔", "火"]}]

DATES_TO_CHECK = ["08", "09", "10"]


def setup_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def get_soup(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"
        if response.status_code == 200:
            return BeautifulSoup(response.text, "html.parser")
    except Exception:
        pass
    return None


def extract_time(soup_text):
    """
    Extracts time based on specific formats:
    English: "HKT 16:00"
    Chinese: "15時58分"
    Returns "0000" if not found.
    """
    # 1. Check English Format (HKT HH:MM)
    eng_match = re.search(r"HKT\s+(\d{2}):(\d{2})", soup_text)
    if eng_match:
        return f"{eng_match.group(1)}{eng_match.group(2)}"  # Returns HHMM

    # 2. Check Chinese Format (HH時MM分)
    chi_match = re.search(r"(\d{1,2})時(\d{1,2})分", soup_text)
    if chi_match:
        hour = chi_match.group(1).zfill(2)
        minute = chi_match.group(2).zfill(2)
        return f"{hour}{minute}"  # Returns HHMM

    # Fallback: Simple HH:MM anywhere
    fallback = re.search(r"(\d{2}):(\d{2})", soup_text)
    if fallback:
        return f"{fallback.group(1)}{fallback.group(2)}"

    return "0000"


def save_content(url, day, lang, title):
    # 1. Get content first to extract time
    soup = get_soup(url)
    if not soup:
        print(f"  [Error] Could not fetch {url}")
        return

    # 2. Extract Time
    page_text = soup.get_text()
    time_str = extract_time(page_text)

    # 3. Build Filename: 202511{day}_{HHMM}_{lang}_{title}
    safe_title = "".join([c if c.isalnum() else "_" for c in title])[:30]
    final_filename = f"202512{day}_{time_str}_{lang}_{safe_title}"

    pdf_path = os.path.join(OUTPUT_DIR, f"{final_filename}.pdf")
    html_path = os.path.join(OUTPUT_DIR, f"{final_filename}.html")

    try:
        # Add header
        header = soup.new_tag("div")
        header.string = f"Source: {url} | Time: {time_str} | Title: {title}"
        soup.body.insert(0, header)

        # Save HTML
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

        # --- PDF GENERATION ---
        try:
            path_to_wkhtmltopdf = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
            config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

            # Options optimized for Chinese characters
            options = {
                "encoding": "UTF-8",
                "no-outline": None,
                "enable-local-file-access": None,
                "quiet": "",  # Suppress non-fatal errors
                "disable-smart-shrinking": None,  # Better for Chinese rendering
                "print-media-type": None,  # Use print CSS
                "dpi": 96,  # Standard DPI
            }

            # Try to convert to PDF
            pdfkit.from_file(html_path, pdf_path, configuration=config, options=options)
            print(f"  [OK] Saved PDF: {final_filename}.pdf")

        except OSError:
            # Check if PDF was created despite error (common with wkhtmltopdf)
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                print(f"  [OK] Saved PDF: {final_filename}.pdf (warning ignored)")
            else:
                print(f"  [HTML Only] Saved: {final_filename}.html (wkhtmltopdf not available)")

        except Exception as e:
            # For Chinese PDFs, wkhtmltopdf often throws harmless errors
            # Check if file was created anyway
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                print(f"  [OK] Saved PDF: {final_filename}.pdf (warning suppressed)")
            else:
                print(f"  [HTML Only] Saved: {final_filename}.html (Error: {str(e)[:50]}...)")

    except Exception as e:
        print(f"  [Error] Failed to process {final_filename}: {e}")


def run_scraper():
    print("Starting Scraper with Corrected Time Format...\n")

    for day in DATES_TO_CHECK:
        print(f"--- Processing Date: 2025-12-{day} ---")

        for config in SEARCH_CONFIG:
            lang = config["lang"]
            keywords = config["keywords"]
            index_url = config["url_template"].format(day=day)

            soup = get_soup(index_url)
            if not soup:
                print(f"  {lang}: Could not access index")
                continue

            links = soup.find_all("a", href=True)
            found = 0

            for link in links:
                title = link.get_text().strip()
                href = link["href"]

                if all(k in title.lower() for k in keywords):
                    found += 1

                    if href.startswith("http"):
                        target_url = href
                    else:
                        target_url = BASE_URL + href

                    print(f"  {lang}: {title}")
                    save_content(target_url, day, lang, title)
                    time.sleep(0.2)

            if found == 0:
                print(f"  {lang}: No results")

        print()


if __name__ == "__main__":
    setup_dir()
    run_scraper()
