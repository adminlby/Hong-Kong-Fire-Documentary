import warnings
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def scrape():
    url = "https://feeds.bbci.co.uk/zhongwen/trad/rss.xml"
    results = []

    def is_relevant(title, description):
        context = title + description
        if "宏福苑" in context:
            return True
        if "香港" in context and ("大火" in context or "火災" in context):
            return True
        return False

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    articles = soup.select("rss channel item")

    for article in articles:
        title = article.select_one("title").text
        description = article.select_one("description").text

        if not is_relevant(title, description):
            continue

        date_str = datetime.strptime(article.select_one("pubDate").text, "%a, %d %b %Y %H:%M:%S GMT").strftime("%F")
        link = urlparse(article.select_one("guid").text)
        link = f"{link.scheme}://{link.netloc}{link.path}"

        results.append((date_str, title, link))

    return ("BBC 中文", results)
