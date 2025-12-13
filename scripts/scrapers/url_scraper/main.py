"""
Extract latest news url from sites into markdown and save to content repository
"""

import glob
import importlib
import os
import re
import sys

# Mapping of Scraper Source Title -> Directory Name in content/news/
# Directories must exist.
SOURCE_DIR_MAP = {
    "TVB News": "tvb",
    "TVB News (English)": "tvb",
    "香港電台": "rthk",
    "Guardian": "the-guardian",
    "DotDotNews": "dotdotnews",
    "DotDotNews (Chinese)": "dotdotnews",
    "HK01": "hk01",
    "明報": "mingpao",
    "有線新聞 (i-Cable)": "i-cable",
    "OnCC": "oriental-daily",
    "人民日報大湾区": "peoples-daily-gba",
    "Sky News": "sky",
    "信報財經新聞": "hkej",
    "晴報 (Sky Post)": "skypost",
    "The Sun": "the-sun",
    "TVBS News": "tvbs",
    "Points Media": "points-media",
    "CNN": "cnn",
    "CNN News": "cnn",
    "SBS News (Australia)": "sbs",
    "BBC 中文": "bbc-chinese",
    "商業電台": "commercial-radio",
    "NOW 新聞報導": "now-news",
    "Hong Kong Free Press": "hkfp",
    "Yahoo HK News": "yahoo-news-hk",
    "獨立媒體": "inmedia",
}


def main():
    """"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir not in sys.path:
        sys.path.append(script_dir)

    scrapers_dir = os.path.join(script_dir, "scrapers")
    scraper_files = glob.glob(os.path.join(scrapers_dir, "*.py"))

    scrapers = []
    for f in scraper_files:
        filename = os.path.basename(f)
        if filename == "__init__.py":
            continue

        module_name = f"scrapers.{filename[:-3]}"
        try:
            # print(f"Importing {module_name}...")
            scrapers.append(importlib.import_module(module_name))
        except Exception as e:
            print(f"Failed to import {module_name}: {e}")

    print(f"Found {len(scrapers)} scrapers. Starting scrape...")

    for scraper in scrapers:
        try:
            if hasattr(scraper, "scrape"):
                print(f"Running {scraper.__name__}...")
                source, content = scraper.scrape()
                save_to_repository(source, content)
            else:
                # print(f"Skipping {scraper.__name__}: No scrape() function.")
                pass
        except Exception as e:
            print(f"Error running {scraper.__name__}: {e}")


def save_to_repository(title: str, content: list[tuple[str, str, str]]) -> None:
    """
    Format string and save as markdown in the content repository.
    Appends new content to existing files, skipping duplicates.

    Args:
            title: title of the source (e.g. "TVB News")
            content: A list of tuple containing (date, article title, url)
    """
    if not content:
        print(f"No articles found for {title}. Skipping.")
        return

    # 1. Determine Target Path
    dir_name = SOURCE_DIR_MAP.get(title)
    if not dir_name:
        print(f"Warning: No directory mapping found for source '{title}'. Skipping save.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "../../.."))
    target_dir = os.path.join(repo_root, "content", "news", dir_name)
    target_file = os.path.join(target_dir, "README.md")

    if not os.path.exists(target_dir):
        print(f"Warning: Directory {target_dir} does not exist. Skipping.")
        return

    # 2. Read Existing Content & Deduplicate
    existing_content = ""
    existing_urls = set()

    if os.path.exists(target_file):
        with open(target_file, encoding="utf-8") as f:
            existing_content = f.read()
            found_urls = re.findall(r"\]\(([^)]+)\)", existing_content)
            existing_urls.update(found_urls)

    new_articles = []
    for date, article_title, url in content:
        if url not in existing_urls:
            if url not in existing_content:
                new_articles.append((date, article_title, url))
                existing_urls.add(url)

    if not new_articles:
        print(f"No new articles for {title}.")
        return

    print(f"Adding {len(new_articles)} new articles to {dir_name}/README.md...")

    # 3. Format New Content
    # Sort by date (ascending)
    new_articles.sort(key=lambda x: x[0])

    markdown_chunk = ""
    current_date = ""

    for date, article_title, url in new_articles:
        if date != current_date:
            current_date = date
            markdown_chunk += f"\n### {current_date}\n"
        markdown_chunk += f"- [{article_title}]({url})\n"

    # 4. Insert into File
    header_marker_single = f"# {title}"
    header_marker_double = f"## {title}"

    lines = existing_content.splitlines(keepends=True)

    insert_idx = -1
    section_found = False
    header_level = 1  # Track if it's # or ##

    header_line_idx = -1
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        # Check for exact match or prefix match (e.g. for Mingpao with date)
        if line_stripped == header_marker_single or line_stripped.startswith(header_marker_single + " "):
            section_found = True
            header_line_idx = i
            header_level = 1
            break
        elif line_stripped == header_marker_double or line_stripped.startswith(header_marker_double + " "):
            section_found = True
            header_line_idx = i
            header_level = 2
            break

    if section_found:
        insert_idx = len(lines)  # Default to end
        for j in range(header_line_idx + 1, len(lines)):
            line_stripped = lines[j].strip()
            if header_level == 1:
                # Looking for next # (not ##)
                if line_stripped.startswith("# ") and not line_stripped.startswith("##"):
                    insert_idx = j
                    break
            # Looking for next ## (not ###)
            elif line_stripped.startswith("## ") and not line_stripped.startswith("###"):
                insert_idx = j
                break

        to_insert = markdown_chunk
        if insert_idx > 0 and not lines[insert_idx - 1].strip() == "":
            to_insert = "\n" + to_insert
        if insert_idx < len(lines):
            to_insert = to_insert + "\n"

        lines.insert(insert_idx, to_insert)
        final_output = "".join(lines)

    else:
        # If section header not found, only add content if file is empty
        if existing_content.strip():
            print(f"Warning: Header '{title}' not found in {target_file}. Skipping to avoid duplication.")
            return

        final_output = existing_content
        if final_output and not final_output.endswith("\n"):
            final_output += "\n"
        final_output += f"# {title}\n" + markdown_chunk

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(final_output)


if __name__ == "__main__":
    main()
