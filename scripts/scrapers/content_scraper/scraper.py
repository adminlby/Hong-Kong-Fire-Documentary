#!/usr/bin/env python3
"""
News Scraper for Hong Kong Fire Documentary
Extracts URLs from markdown files, deduplicates, and archives HTML content.
Now with PARALLEL scraping across different domains!
"""

import argparse
import asyncio
import json
import random
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

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
        if not url.endswith(".md") and not url.startswith("#"):
            urls.append(
                {
                    "title": title.strip("*").strip(),
                    "url": url.strip(),
                    "source_file": str(filepath.relative_to(PROJECT_ROOT)),
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
                        "source_file": str(filepath.relative_to(PROJECT_ROOT)),
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
                    "source_file": str(filepath.relative_to(PROJECT_ROOT)),
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


def save_archive(url_info: dict, html: str, source_dir: Path) -> Path | None:
    """Save scraped content to archive directory. Returns None if already exists."""
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
            return None  # Skip - already archived

        # Different URL, need unique folder name
        counter = 1
        while (archive_dir / f"{slug}-{counter}").exists():
            existing_url = get_existing_archive_url(archive_dir / f"{slug}-{counter}")
            if existing_url == url:
                log("  ⏭️ Archive already exists for this URL", "WARN")
                return None  # Skip - already archived
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
        "archive_path": str(article_dir.relative_to(PROJECT_ROOT)),
    }
    with open(article_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return article_dir


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


def scrape_with_uc(url: str, config: dict) -> tuple[str, bool]:
    """Fallback scraper using undetected-chromedriver library for hkej, not-mature"""
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    try:
        driver = uc.Chrome(headless=True, use_subprocess=False)
        driver.get(url)
        element = WebDriverWait(driver, 10).until(
           EC.visibility_of_element_located((By.XPATH, "/html/body/div[7]/div/div[1]/div[4]"))
        )
        content = element.get_attribute("outerHTML")
        check_content = element.text
        if check_content.find("訂戶登入") > -1:
            log(f"Need Subscriber Login")
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

    # Strategy selection based on retry count
    strategies = [
        {"wait_until": "domcontentloaded", "desc": "domcontentloaded"},
        {"wait_until": "networkidle", "desc": "networkidle"},
        {"wait_until": "domcontentloaded", "desc": "no-http2", "no_http2": True},
        {"desc": "requests-fallback", "use_requests": True},
    ]

    #if url.find("hkej.com") > -1:
    #    strategies = [
    #        {"desc": "uc-fallback", "use_uc": True},
    #    ]

    strategy_idx = min(retries, len(strategies) - 1)
    strategy = strategies[strategy_idx]

    # Use requests library as final fallback
    if strategy.get("use_requests"):
        log("  🔄 Trying requests fallback...", "WARN")
        return await scrape_with_requests(url, config)

    if strategy.get("use_uc"):
        log("  🔄 Trying undetected-chromedriver fallback...", "WARN")
        return scrape_with_uc(url, config)

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

            archive_path = save_archive(url_info, html, source_dir)

            if archive_path is None:
                # Already existed - still mark as success and add to registry
                results["success"] += 1
                # Update registry to prevent future attempts
                registry["scraped_urls"][url] = {
                    "title": url_info["title"],
                    "source": source.lower(),
                    "scraped_at": datetime.now().isoformat(),
                    "archive_path": "already_existed",
                }
                save_registry(registry)
            else:
                # New archive saved
                registry["scraped_urls"][url] = {
                    "title": url_info["title"],
                    "source": source.lower(),
                    "scraped_at": datetime.now().isoformat(),
                    "archive_path": str(archive_path.relative_to(PROJECT_ROOT)),
                }
                save_registry(registry)
                results["success"] += 1
                log(f"  ✓ Saved ({len(html) // 1024}KB)")
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

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Create tasks for each domain (limited concurrency)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOMAINS)

        async def bounded_scrape(domain, urls):
            async with semaphore:
                await scrape_domain_queue(domain, urls, browser, config, registry, results, progress)

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
) -> dict | None:
    """Wrapper to run async scraper. Returns results dict with success, failed, failed_urls."""
    return asyncio.run(run_scraper_async(dry_run, source_filter, limit, verbose))


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

    run_scraper(
        dry_run=args.dry_run,
        source_filter=args.source,
        limit=args.limit,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()