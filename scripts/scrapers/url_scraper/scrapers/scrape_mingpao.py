"""
mingpao scraper
"""

# max_pages: int = 10                          #30 <-- temp solution for errors raise in 2026/1/22
max_pages: int = 30


def parse_response(data: dict):
    result = []
    try:
        title = [i["TITLE"].replace("\u3000", " ").replace("|", " ") for i in data["data_Result"]]
        links = [i["SUMMARY"]["sharelink"] for i in data["data_Result"]]
        dates = [i["ATTRIBUTES"]["DOCISSUE"] for i in data["data_Result"]]

        result = [(dates[i], title[i], links[i]) for i in range(len(data["data_Result"]))]
    except:
        pass
    return result


def scrape():
    import datetime
    import json
    from urllib.parse import quote

    import httpx

    keyword = "宏福苑"  # you can change this
    encoded_keyword = quote(keyword)

    url = "https://news.mingpao.com/php/searchapi.php"

    params = {
        "mode": "both",
        "keywords": encoded_keyword,
        "pnssection": "s00001,s00002,s00004,s00016,s00005,s00003,s00012,s00013,s00014,s00011,s00015,s00017,s00018",
        "inssection": "s00001,s00024,s00007,s00002,s00003,s00004,s00005,s00006,s00022",
        "periodstart": "20250826",
        "periodend": datetime.date.today().strftime("%Y%m%d"),
        "subsectionkeywords": "",
        "sort": "d",
        # "pagesize": "100",                   #1 <-- temp solution for errors raise in 2026/1/22
        "pagesize": "1",
        "page": "1",
        "searchtype": "a",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://news.mingpao.com/php/search2.php",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=4",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }

    # Use httpx with HTTP/2
    with httpx.Client(http2=True, timeout=30.0) as client:
        result = []
        for i in range(1, max_pages):
            params["page"] = str(i)
            response = client.get(url, params=params, headers=headers)

            # MingPao returns JSON even though Content-Type might be text/html sometimes
            response.raise_for_status()

            try:
                data: dict = response.json()
                if data.get("data_Msg") == "找不到記錄":
                    break
                result += parse_response(data)
            except json.JSONDecodeError:
                print("Response is not JSON:")
                print(response.text[:500])
                raise
        return ("明報", result)
