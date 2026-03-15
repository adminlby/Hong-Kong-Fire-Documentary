#!/usr/bin/env python3
"""
News Scraper for Hong Kong Fire Documentary
Extracts URLs from markdown files, deduplicates, and archives HTML content.
Now with PARALLEL scraping across different domains!
"""

import argparse
import asyncio
import json
import os
import random
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Project paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # scripts/scrapers/content_scraper -> project root
NEWS_DIR = PROJECT_ROOT / "content" / "news"
CONFIG_FILE = SCRIPT_DIR / "config.yml"
REGISTRY_FILE = SCRIPT_DIR / "scraped_urls.json"

# Concurrency settings
MAX_CONCURRENT_DOMAINS = 5  # Scrape up to 5 different domains at once
MAX_CONCURRENT_PER_DOMAIN = 1  # Only 1 request per domain at a time (be nice)


def log(msg: str, level: str = "INFO"):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {msg}", flush=True)


def load_config() -> dict:
    """Load configuration from config.yml"""
    import yaml

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {
        "rate_limit": {
            "delay_seconds": 3,
            "max_retries": 3,
            "timeout_seconds": 60,
        },
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "sites": {},
    }


def load_registry() -> dict:
    """Load the registry of previously scraped URLs"""
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"scraped_urls": {}, "last_updated": None}


def save_registry(registry: dict):
    """Save the registry of scraped URLs"""
    registry["last_updated"] = datetime.now().isoformat()
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def slugify(text: str, max_length: int = 80) -> str:
    """Convert text to a filesystem-safe slug"""
    text = unicodedata.normalize("NFKD", text)
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    text = text.strip("-")
    if len(text) > max_length:
        text = text[:max_length].rsplit("-", 1)[0]
    return text or "untitled"


def extract_urls_from_markdown(filepath: Path) -> list[dict]:
    """Extract URLs and titles from a markdown file."""
    urls = []

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Pattern 1: Markdown links [Title](URL)
    link_pattern = r"\[([^\]]+)\]\((https?://[^\)]+)\)"
    for match in re.finditer(link_pattern, content):
        title, url = match.groups()
        if title.strip().lower() in {"original", "archive"}:
            continue
        if not url.endswith(".md") and not url.startswith("#"):
            urls.append(
                {
                    "title": title.strip("*").strip(),
                    "url": url.strip(),
                    "source_file": filepath.relative_to(PROJECT_ROOT).as_posix(),
                }
            )

    # Pattern 2: Table format | Title | URL |
    table_pattern = r"\|\s*([^|]+?)\s*\|\s*<?(\s*https?://[^\s>|]+)\s*>?\s*\|"
    for match in re.finditer(table_pattern, content):
        title, url = match.groups()
        title = title.strip()
        url = url.strip()
        if title.lower() not in ["標題", "title", "連結", "link", "---", "------"]:
            if url and not url.startswith("---"):
                urls.append(
                    {
                        "title": title,
                        "url": url,
                        "source_file": filepath.relative_to(PROJECT_ROOT).as_posix(),
                    }
                )

    # Pattern 3: List item with angle-bracket URL format: - Title (<URL>)
    # Used by 東方日報 and similar sources
    list_angle_pattern = r"^-\s+(.+?)\s+\(<(https?://[^>]+)>\)"
    for match in re.finditer(list_angle_pattern, content, re.MULTILINE):
        title, url = match.groups()
        title = title.strip()
        url = url.strip()
        if title and url:
            urls.append(
                {
                    "title": title,
                    "url": url,
                    "source_file": filepath.relative_to(PROJECT_ROOT).as_posix(),
                }
            )

    return urls


def get_source_name(filepath: Path) -> str:
    """Extract source name from filepath"""
    parts = filepath.relative_to(NEWS_DIR).parts
    return parts[0] if parts else "unknown"


def discover_news_sources() -> dict[str, Path]:
    """Discover all news source directories with markdown files"""
    sources = {}
    if not NEWS_DIR.exists():
        return sources

    for item in NEWS_DIR.iterdir():
        if item.is_dir():
            for readme in item.glob("[Rr][Ee][Aa][Dd][Mm][Ee].*[Mm][Dd]"):
                sources[item.name] = readme
                break
    return sources


def get_all_urls(sources: dict[str, Path] = None, source_filter: str = None) -> list[dict]:
    """Get all URLs from news markdown files."""
    if sources is None:
        sources = discover_news_sources()

    all_urls = []
    for source_name, filepath in sources.items():
        if source_filter and source_name.lower() != source_filter.lower():
            continue
        urls = extract_urls_from_markdown(filepath)
        for url_info in urls:
            url_info["source"] = source_name
        all_urls.extend(urls)
    return all_urls


def filter_new_urls(urls: list[dict], registry: dict) -> list[dict]:
    """Filter out URLs that have already been scraped"""
    scraped = registry.get("scraped_urls", {})
    return [u for u in urls if u["url"] not in scraped]


def get_domain(url: str) -> str:
    """Extract domain from URL"""
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")


def group_urls_by_domain(urls: list[dict]) -> dict[str, list[dict]]:
    """Group URLs by their domain for parallel processing"""
    grouped = defaultdict(list)
    for url_info in urls:
        domain = get_domain(url_info["url"])
        grouped[domain].append(url_info)
    return dict(grouped)


def get_site_config(url: str, config: dict) -> dict:
    """Get site-specific configuration"""
    domain = get_domain(url)
    site_config = config.get("sites", {}).get(domain, {})
    return {
        "delay_seconds": site_config.get("delay_seconds", config["rate_limit"]["delay_seconds"]),
        "max_retries": site_config.get("max_retries", config["rate_limit"]["max_retries"]),
        "timeout_seconds": site_config.get("timeout_seconds", config["rate_limit"]["timeout_seconds"]),
    }


def get_existing_archive_url(folder: Path) -> str | None:
    """Get URL from existing archive folder's metadata"""
    metadata_file = folder / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, encoding="utf-8") as f:
                return json.load(f).get("url")
        except Exception:
            pass
    return None


def save_archive(url_info: dict, html: str, source_dir: Path) -> tuple[Path, bool]:
    """Save scraped content to archive directory. Returns (path, created_new)."""
    archive_dir = source_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    slug = slugify(url_info["title"])
    article_dir = archive_dir / slug
    url = url_info["url"]

    # Check if folder exists with same URL (duplicate)
    if article_dir.exists():
        existing_url = get_existing_archive_url(article_dir)
        if existing_url == url:
            log("  ⏭️ Archive already exists for this URL", "WARN")
            return article_dir, False  # Already archived

        # Different URL, need unique folder name
        counter = 1
        while (archive_dir / f"{slug}-{counter}").exists():
            existing_url = get_existing_archive_url(archive_dir / f"{slug}-{counter}")
            if existing_url == url:
                log("  ⏭️ Archive already exists for this URL", "WARN")
                return archive_dir / f"{slug}-{counter}", False  # Already archived
            counter += 1
        article_dir = archive_dir / f"{slug}-{counter}"

    article_dir.mkdir(exist_ok=True)

    # Save HTML
    with open(article_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Save metadata
    metadata = {
        "url": url,
        "title": url_info["title"],
        "source": url_info["source"].lower(),  # Normalize to lowercase
        "source_file": url_info["source_file"],
        "scraped_at": datetime.now().isoformat(),
        "archive_path": article_dir.relative_to(PROJECT_ROOT).as_posix(),
    }
    with open(article_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return article_dir, True


def _archive_link_for_source_file(source_file: Path, archive_dir: Path) -> str:
    try:
        rel = archive_dir.relative_to(source_file.parent)
        rel_str = rel.as_posix()
    except ValueError:
        # Fallback for case-mismatched/legacy folder layouts: compute a generic relative path.
        rel_str = Path(os.path.relpath(archive_dir, start=source_file.parent)).as_posix()
    return rel_str.rstrip("/") + "/"


def _add_buttons_to_line(line: str, url: str, archive_link: str) -> str:
    if "Archive](" in line or "Original](" in line:
        if ".hkfd-news-button" in line:
            return line
        line = line.replace("{.md-button .md-button--primary}", "{.md-button .md-button--primary .hkfd-news-button}")
        line = line.replace("{.md-button}", "{.md-button .hkfd-news-button}")
        return line

    original_button = f"[Original]({url}){{.md-button .md-button--primary .hkfd-news-button}}"
    archive_button = f"[Archive]({archive_link}){{.md-button .hkfd-news-button}}"
    return line.rstrip("\n") + f" {original_button} {archive_button}\n"


def add_archive_buttons_to_markdown(source_file: Path, url: str, archive_dir: Path) -> bool:
    """
    Add Material-style buttons next to a URL entry inside a news markdown file.
    Returns True if the file was modified.
    """
    if not source_file.exists():
        return False

    archive_link = _archive_link_for_source_file(source_file, archive_dir)
    text = source_file.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    changed = False
    url_escaped = re.escape(url)

    # Target common list format: - [Title](URL)
    list_link_re = re.compile(rf"^(\s*[-*]\s+)\[[^\]]+\]\(({url_escaped})\).*$", re.MULTILINE)
    for i, line in enumerate(lines):
        if list_link_re.match(line):
            new_line = _add_buttons_to_line(line, url, archive_link)
            if new_line != line:
                lines[i] = new_line
                changed = True

    if not changed:
        return False

    updated_text = "".join(lines)
    try:
        source_file.write_text(updated_text, encoding="utf-8")
    except OSError as e:
        # Windows can sometimes raise OSError(22) for certain paths; fall back to io.open.
        try:
            with open(source_file, "w", encoding="utf-8", newline="\n") as f:
                f.write(updated_text)
        except OSError:
            log(f"Failed to write markdown file: {source_file} ({e})", "WARN")
            return False
    return True


def find_archive_dir_for_url(source_dir: Path, url: str) -> Path | None:
    """Find an existing archive folder for a URL by scanning metadata.json files."""
    archive_root = source_dir / "archive"
    if not archive_root.exists():
        return None
    for metadata_file in archive_root.glob("*/metadata.json"):
        try:
            data = json.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("url") == url:
            return metadata_file.parent
    return None


def _normalize_registry_relpath(path_str: str) -> Path:
    # Registry values may be written from Windows and contain backslashes. Normalize to POSIX-style.
    return Path(path_str.replace("\\", "/"))


def update_markdown_from_registry(registry: dict, source_filter: str | None = None) -> dict[str, int]:
    """Update markdown files with Archive/Original buttons for all registry entries."""
    stats = {"updated_files": 0, "updated_links": 0, "skipped": 0}
    scraped = registry.get("scraped_urls", {})
    sources = discover_news_sources()
    source_readmes_by_lower = {name.lower(): path for name, path in sources.items()}
    updated_files: set[Path] = set()

    # Build an index of URL -> archive_dir per source once (fast path for older registries / casing mismatches).
    archive_index_by_source: dict[str, dict[str, Path]] = {}
    for source_name, readme_path in sources.items():
        source_lower = source_name.lower()
        if source_filter and source_lower != source_filter.lower():
            continue
        source_dir = readme_path.parent
        archive_root = source_dir / "archive"
        if not archive_root.exists():
            continue
        url_to_dir: dict[str, Path] = {}
        for metadata_file in archive_root.glob("*/metadata.json"):
            try:
                data = json.loads(metadata_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            url = data.get("url")
            if isinstance(url, str) and url:
                url_to_dir[url] = metadata_file.parent
        if url_to_dir:
            archive_index_by_source[source_lower] = url_to_dir

    for url, info in scraped.items():
        source = (info.get("source") or "").lower()
        if source_filter and source != source_filter.lower():
            continue
        source_file_rel = info.get("source_file")
        archive_path_rel = info.get("archive_path")
        # Backward-compatibility: older registries didn't track source_file and/or had wrong archive_path casing.
        source_file = (PROJECT_ROOT / _normalize_registry_relpath(source_file_rel)) if source_file_rel else source_readmes_by_lower.get(source)
        archive_dir = (PROJECT_ROOT / _normalize_registry_relpath(archive_path_rel)) if archive_path_rel else None

        if not source_file or not source_file.exists():
            stats["skipped"] += 1
            continue

        if not archive_dir or not archive_dir.exists():
            archive_dir = archive_index_by_source.get(source, {}).get(url)
            if not archive_dir:
                source_dir = NEWS_DIR / source
                if not source_dir.exists():
                    # Try case-insensitive match
                    for d in NEWS_DIR.iterdir():
                        if d.is_dir() and d.name.lower() == source:
                            source_dir = d
                            break
                archive_dir = find_archive_dir_for_url(source_dir, url) if source_dir.exists() else None

        if not archive_dir:
            stats["skipped"] += 1
            continue

        if add_archive_buttons_to_markdown(source_file, url, archive_dir):
            stats["updated_links"] += 1
            updated_files.add(source_file)
        else:
            stats["skipped"] += 1
    stats["updated_files"] = len(updated_files)
    return stats


async def scrape_with_requests(url: str, config: dict) -> tuple[str, bool]:
    """Fallback scraper using requests library for simple pages"""
    import requests

    try:
        headers = {"User-Agent": config["user_agent"]}
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        return response.text, True
    except Exception as e:
        log(f"  ⚠️ Requests fallback failed: {str(e)[:40]}", "WARN")
        return "", False


def scrape_with_uc_inmedia(url: str, config: dict) -> tuple[str, bool]:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        driver = uc.Chrome(headless=False, use_subprocess=False)
        driver.get(url)
        element = WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/article")))
        content = element.get_attribute("innerHTML")
        driver.close()
        return content, True
    except Exception as e:
        log(f"  ⚠️ Undetected Chromedriver fallback failed: {str(e)[:40]}", "WARN")
        return "", False


def scrape_with_uc_hkej(url: str, config: dict) -> tuple[str, bool]:
    """Fallback scraper using undetected-chromedriver library for hkej, not-mature"""
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        driver = uc.Chrome(headless=True, use_subprocess=False)
        driver.get(url)
        element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[7]/div/div[1]/div[4]")))
        content = element.get_attribute("outerHTML")
        check_content = element.text
        if check_content.find("訂戶登入") > -1:
            log("Need Subscriber Login")
            return "", False
        driver.close()
        return content, True
    except Exception as e:
        log(f"  ⚠️ Undetected Chromedriver fallback failed: {str(e)[:40]}", "WARN")
        return "", False


async def scrape_url_async(url_info: dict, context, config: dict, retries: int = 0, browser=None) -> tuple[str, bool]:
    """
    Scrape a single URL with multiple fallback strategies:
    - Retry 0: domcontentloaded (fast)
    - Retry 1: networkidle (wait for all network)
    - Retry 2: new context without HTTP/2 (fixes protocol errors)
    - Retry 3: requests library fallback (for download-triggering pages)
    """
    url = url_info["url"]
    site_config = get_site_config(url, config)
    timeout = site_config["timeout_seconds"] * 1000
    max_retries = site_config["max_retries"]
    from playwright.async_api import TimeoutError as PlaywrightTimeout

    # Strategy selection based on retry count
    strategies = [
        {"wait_until": "domcontentloaded", "desc": "domcontentloaded"},
        {"wait_until": "networkidle", "desc": "networkidle"},
        {"wait_until": "domcontentloaded", "desc": "no-http2", "no_http2": True},
        {"desc": "requests-fallback", "use_requests": True},
    ]

    if url.find("inmediahk.net") > -1:
        strategies = [
            {"desc": "uc-fallback", "use_uc_inmedia": True},
        ]

    strategy_idx = min(retries, len(strategies) - 1)
    strategy = strategies[strategy_idx]

    # Use requests library as final fallback
    if strategy.get("use_requests"):
        log("  🔄 Trying requests fallback...", "WARN")
        return await scrape_with_requests(url, config)

    if strategy.get("use_uc_inmedia"):
        log("  🔄 Trying undetected-chromedriver fallback...", "WARN")
        return scrape_with_uc_inmedia(url, config)

    # Create new context for HTTP/2 disabled retry
    use_context = context
    created_context = False
    if strategy.get("no_http2") and browser:
        try:
            use_context = await browser.new_context(
                user_agent=config["user_agent"],
                viewport={"width": 1920, "height": 1080},
                extra_http_headers={"Upgrade-Insecure-Requests": "1"},
                ignore_https_errors=True,
            )
            created_context = True
        except Exception:
            use_context = context

    page = await use_context.new_page()
    try:
        # Handle download-triggering pages
        page.on("download", lambda _: None)  # Ignore downloads

        await page.goto(url, timeout=timeout, wait_until=strategy["wait_until"])
        await page.wait_for_timeout(1500)  # Wait for JS
        html = await page.content()

        # Check if we got meaningful content
        if len(html) < 500:
            raise ValueError("Page content too short, likely blocked")

        return html, True

    except PlaywrightTimeout:
        if retries < max_retries:
            log(f"  ⏳ Timeout ({strategy['desc']}), retry {retries + 1}/{max_retries}...", "WARN")
            await asyncio.sleep(2**retries)
            return await scrape_url_async(url_info, context, config, retries + 1, browser)
        return "", False

    except Exception as e:
        error_str = str(e)

        # Skip URLs that trigger downloads (like PDFs, videos)
        if "Download is starting" in error_str:
            log("  ⏭️ Skipping download URL", "WARN")
            return "", False

        if retries < max_retries:
            log(f"  ⚠️ Error ({strategy['desc']}): {error_str[:40]}, retry {retries + 1}/{max_retries}...", "WARN")
            await asyncio.sleep(2**retries)
            return await scrape_url_async(url_info, context, config, retries + 1, browser)
        return "", False

    finally:
        await page.close()
        if created_context:
            await use_context.close()


async def scrape_domain_queue(
    domain: str,
    urls: list[dict],
    browser,
    config: dict,
    registry: dict,
    results: dict,
    progress: dict,
    update_markdown: bool,
):
    """Scrape all URLs for a single domain sequentially"""
    context = await browser.new_context(
        user_agent=config["user_agent"],
        viewport={"width": 1920, "height": 1080},
    )

    site_config = get_site_config(urls[0]["url"], config)
    delay = site_config["delay_seconds"]

    for url_info in urls:
        url = url_info["url"]
        title = url_info["title"][:40]
        source = url_info["source"]

        progress["current"] += 1
        pct = (progress["current"] / progress["total"]) * 100
        log(f"[{progress['current']}/{progress['total']}] ({pct:.0f}%) {domain}: {title}...")

        html, success = await scrape_url_async(url_info, context, config, browser=browser)

        if success and html:
            # Find source directory (case-insensitive)
            source_dir = NEWS_DIR / source.lower()
            if not source_dir.exists():
                for d in NEWS_DIR.iterdir():
                    if d.is_dir() and d.name.lower() == source.lower():
                        source_dir = d
                        break

            archive_dir, created_new = save_archive(url_info, html, source_dir)

            registry["scraped_urls"][url] = {
                "title": url_info["title"],
                "source": source.lower(),
                "source_file": url_info["source_file"],
                "scraped_at": datetime.now().isoformat(),
                "archive_path": str(archive_dir.relative_to(PROJECT_ROOT)),
            }
            save_registry(registry)
            results["success"] += 1
            if created_new:
                log(f"  ✓ Saved ({len(html) // 1024}KB)")

            if update_markdown:
                try:
                    add_archive_buttons_to_markdown(PROJECT_ROOT / url_info["source_file"], url, archive_dir)
                except Exception as e:
                    log(f"  ⚠️ Failed to update markdown buttons: {str(e)[:60]}", "WARN")
        else:
            results["failed"] += 1
            results["failed_urls"].append(url)  # Track failed URL
            log("  ✗ Failed")

        # Rate limit delay between requests to same domain
        if urls.index(url_info) < len(urls) - 1:
            await asyncio.sleep(delay + random.uniform(0, 1))

    await context.close()


async def run_scraper_async(
    dry_run: bool = False,
    source_filter: str = None,
    limit: int = None,
    verbose: bool = False,
    update_markdown: bool = True,
):
    """Main async scraper function with parallel domain processing"""
    config = load_config()
    registry = load_registry()
    sources = discover_news_sources()

    log(f"Found {len(sources)} news sources")

    # Get all URLs
    all_urls = get_all_urls(sources, source_filter)
    log(f"Found {len(all_urls)} total URLs")

    # Filter to new URLs only
    new_urls = filter_new_urls(all_urls, registry)
    log(f"Found {len(new_urls)} NEW URLs to scrape")

    if limit:
        new_urls = new_urls[:limit]
        log(f"Limited to {limit} URLs")

    if dry_run:
        print("\n=== DRY RUN ===\n")
        domains = group_urls_by_domain(new_urls)
        for domain, urls in sorted(domains.items(), key=lambda x: -len(x[1])):
            print(f"{domain}: {len(urls)} URLs")
            if verbose:
                for u in urls[:3]:
                    print(f"  - {u['title'][:50]}")
                if len(urls) > 3:
                    print(f"  ... and {len(urls) - 3} more")
        print(f"\nWould scrape {len(new_urls)} URLs across {len(domains)} domains")
        return {"success": 0, "failed": 0, "failed_urls": []}

    if not new_urls:
        log("No new URLs to scrape")
        return {"success": 0, "failed": 0, "failed_urls": []}

    # Group URLs by domain
    domains = group_urls_by_domain(new_urls)
    log(f"URLs grouped into {len(domains)} domains")

    # Show domain distribution
    for domain, urls in sorted(domains.items(), key=lambda x: -len(x[1]))[:5]:
        log(f"  {domain}: {len(urls)} URLs")
    if len(domains) > 5:
        log(f"  ... and {len(domains) - 5} more domains")

    print()
    log("🚀 Starting parallel scraper...")
    print()

    results = {"success": 0, "failed": 0, "failed_urls": []}
    progress = {"current": 0, "total": len(new_urls)}

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Create tasks for each domain (limited concurrency)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOMAINS)

        async def bounded_scrape(domain, urls):
            async with semaphore:
                await scrape_domain_queue(domain, urls, browser, config, registry, results, progress, update_markdown)

        # Run all domain scrapers concurrently (bounded by semaphore)
        tasks = [bounded_scrape(domain, urls) for domain, urls in domains.items()]

        await asyncio.gather(*tasks)

        await browser.close()

    print()
    log("=" * 50)
    log(f"✅ Success: {results['success']}")
    log(f"❌ Failed:  {results['failed']}")
    log(f"📊 Total:   {results['success'] + results['failed']}")
    log("=" * 50)

    return results


def run_scraper(
    dry_run: bool = False,
    source_filter: str = None,
    limit: int = None,
    verbose: bool = False,
    update_markdown: bool = True,
) -> dict | None:
    """Wrapper to run async scraper. Returns results dict with success, failed, failed_urls."""
    return asyncio.run(run_scraper_async(dry_run, source_filter, limit, verbose, update_markdown))


def main():
    parser = argparse.ArgumentParser(description="Scrape news articles from URLs in markdown files (PARALLEL)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scraped without actually scraping",
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Only scrape URLs from a specific source (e.g., BBC, HK01)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of URLs to scrape",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List all available news sources",
    )
    parser.add_argument(
        "--update-markdown-only",
        action="store_true",
        help="Update markdown files with Archive/Original buttons from registry, without scraping",
    )
    parser.add_argument(
        "--no-update-markdown",
        action="store_true",
        help="Do not modify markdown files during scraping",
    )

    args = parser.parse_args()

    if args.list_sources:
        sources = discover_news_sources()
        registry = load_registry()
        scraped = registry.get("scraped_urls", {})

        print("Available news sources:")
        for name, path in sorted(sources.items()):
            urls = extract_urls_from_markdown(path)
            new_count = len([u for u in urls if u["url"] not in scraped])
            print(f"  {name}: {len(urls)} URLs ({new_count} new)")
        return

    if args.update_markdown_only:
        registry = load_registry()
        stats = update_markdown_from_registry(registry, args.source)
        log(f"Updated markdown (registry): {stats}")
        return

    run_scraper(
        dry_run=args.dry_run,
        source_filter=args.source,
        limit=args.limit,
        verbose=args.verbose,
        update_markdown=not args.no_update_markdown,
    )


if __name__ == "__main__":
    main()
