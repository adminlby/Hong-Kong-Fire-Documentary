import asyncio
import re

from playwright.async_api import async_playwright


async def _scrape_async():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = await context.new_page()

        results = []
        keywords = ["宏福苑", "大埔 火警"]  # Keywords from user's logic

        print("Searching HKEJ...")
        for keyword in keywords:
            url = f"https://search.hkej.com/template/fulltextsearch/php/search.php?q={keyword}"
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)  # Wait for results to render

                # Select result containers
                containers = await page.query_selector_all("div.result")

                for container in containers:
                    try:
                        # Title and Link
                        h3_a = await container.query_selector("h3 a")
                        if not h3_a:
                            continue

                        title = await h3_a.inner_text()
                        link = await h3_a.get_attribute("href")

                        # Summary
                        summary_elem = await container.query_selector("p.recap")
                        summary_text = await summary_elem.inner_text() if summary_elem else ""

                        # Date Extraction
                        date_elem = await container.query_selector("span.timeStamp")
                        date_str = "2025-11-26"  # Default

                        if date_elem:
                            date_text = await date_elem.inner_text()
                            date_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_text)
                            if date_match:
                                y, m, d = date_match.groups()
                                date_str = f"{y}-{int(m):02d}-{int(d):02d}"

                        # Filtering Logic (from user's request)
                        search_content = title + " " + summary_text

                        is_relevant = False

                        if "宏福" in search_content or "Wang Fuk" in search_content:
                            is_relevant = True
                        elif "大埔" in search_content and ("火" in search_content or "Fire" in search_content):
                            is_relevant = True

                        if is_relevant:
                            # Deduplicate
                            if link not in [r["link"] for r in results]:
                                results.append({"date": date_str, "title": title.strip(), "link": link})

                    except Exception as e:
                        print(f"Error parsing result: {e}")

            except Exception as e:
                print(f"Search failed for {keyword}: {e}")

        await browser.close()
        return results


def scrape():
    """
    Scrapes HKEJ and returns a tuple of (source_name, list_of_articles).
    Each article is a tuple of (date, title, link).
    """
    raw_results = asyncio.run(_scrape_async())

    formatted_results = [(r["date"], r["title"], r["link"]) for r in raw_results]

    # Sort by date descending
    formatted_results.sort(key=lambda x: x[0], reverse=True)

    return ("信報財經新聞", formatted_results)
