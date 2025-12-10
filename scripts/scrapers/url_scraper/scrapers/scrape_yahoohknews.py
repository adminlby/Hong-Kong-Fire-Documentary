import asyncio
import datetime
import re

from playwright.async_api import async_playwright


async def _scrape_async():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = await context.new_page()

        results = []

        topic_url = "https://hk.news.yahoo.com/topic/Tai-Po-Wang-Fuk-Court-Fire"
        print(f"Visiting topic page: {topic_url}")

        try:
            await page.goto(topic_url, wait_until="domcontentloaded", timeout=30000)
            # Wait for content to stabilize
            await asyncio.sleep(3)

            # Scroll to bottom to load all content
            last_height = await page.evaluate("document.body.scrollHeight")
            retries = 0
            counter = 0
            while True or counter < 40:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    retries += 1
                    if retries >= 3:  # Try a couple times to ensure no more content loads
                        break
                else:
                    retries = 0
                counter += 1
                last_height = new_height

            elements = await page.query_selector_all("a")
            for el in elements:
                try:
                    title_raw = await el.inner_text()
                    link = await el.get_attribute("href")

                    if link and title_raw and len(title_raw.strip()) > 5:
                        title_clean = " ".join(title_raw.split())

                        news_source_orignial = re.search(r"Yahoo新聞", title_clean)
                        if not news_source_orignial:
                            continue

                        close_match = title_clean.find("宏福苑五級火追蹤\uff5c")
                        if close_match == -1:
                            continue

                        title_actual = title_clean[close_match + 7 :].strip()

                        summary_article_match = re.search(r"純文字重點 不帶災場畫面 附情緒支援熱線", title_clean)
                        if summary_article_match:
                            continue

                        if not link.startswith("http"):
                            link = "https://hk.news.yahoo.com" + link

                            base_date = datetime.date.today()
                            article_date = base_date.strftime("%Y-%m-%d")

                            # 1. Relative Time (e.g., 2小時前, 1日前)
                            time_match = re.search(r"(\d+)(小時|分鐘|日|天)前", title_clean)
                            if time_match:
                                val = int(time_match.group(1))
                                unit = time_match.group(2)

                                if unit in ["日", "天"]:
                                    calc_date = base_date - datetime.timedelta(days=val)
                                    article_date = calc_date.strftime("%Y-%m-%d")

                            else:
                                abs_match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", title_clean)
                                if abs_match:
                                    y, m, d = map(int, abs_match.groups())
                                    article_date = datetime.date(y, m, d).strftime("%Y-%m-%d")
                                else:
                                    # 3. Absolute Date Short (MM月DD日) - Assume current year
                                    short_match = re.search(r"(\d{1,2})月(\d{1,2})日", title_clean)
                                    if short_match:
                                        m, d = map(int, short_match.groups())
                                        article_date = datetime.date(base_date.year, m, d).strftime("%Y-%m-%d")

                            if link not in [r["link"] for r in results]:
                                results.append({"date": article_date, "title": title_actual, "link": link})
                except Exception:
                    pass

        except Exception as e:
            print(f"Error visiting topic page: {e}")

        await browser.close()
        return results


def scrape():
    try:
        raw_results = asyncio.run(_scrape_async())
    except Exception as e:
        print(f"Yahoo HK News Scraper failed: {e}")
        raw_results = []

    formatted_results = [(r["date"], r["title"], r["link"]) for r in raw_results]
    return ("Yahoo HK News", formatted_results)
