import datetime

import requests
from bs4 import BeautifulSoup


def scrape():
    base_url = "https://news.rthk.hk"
    start_date = datetime.date(2025, 12, 9)
    end_date = datetime.date.today()

    configs = [{"lang": "English", "url": "https://news.rthk.hk/rthk/en/news-archive.htm", "keywords": ["Wang Fuk"]}, {"lang": "Chinese", "url": "https://news.rthk.hk/rthk/ch/news-archive.htm", "keywords": ["宏福"]}]

    results = []

    def get_news_for_date(url, date):
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")

        params = {"archive_year": year, "archive_month": month, "archive_day": day, "archive_cat": "all"}

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    def parse_news(html, keywords):
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", class_="item")
        daily_news = []

        for item in items:
            title_span = item.find("span", class_="title")
            if title_span:
                link_tag = title_span.find("a")
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    href = link_tag.get("href")
                    full_link = base_url + href if href.startswith("/") else href

                    if any(k.lower() in title.lower() for k in keywords):
                        daily_news.append((title, full_link))
        return daily_news

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")

        for config in configs:
            html = get_news_for_date(config["url"], current_date)
            if html:
                news_items = parse_news(html, config["keywords"])
                for title, link in news_items:
                    results.append((date_str, title, link))

        current_date += datetime.timedelta(days=1)

    return ("香港電台", results)
