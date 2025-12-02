import requests 

def scrape(): 
    base_url = 'https://www.881903.com/api/news/section/morelist'
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    params = {
        'news_column_id': 11, # local news 
        'limit': 100
    }
    start_date = '2025-11-26'
    results = []

    def is_relevant(title, preview): 
        # Note: The word usage is not consistent for different articles
        context = title + preview
        if '宏福苑' in context or '宏褔苑' in context: 
            return True 
        if '宏業' in context: 
            return True
        if '何偉豪' in context: 
            return True
        if '救災' in context or '受災' in context: 
            return True
        if '五級火' in context or '五級大火' in context: 
            return True
        return False

    has_next = True
    while has_next:
        response = requests.get(base_url, params=params, headers=headers)
        response.raise_for_status()
        params.update({'offset': response.json()['response']['next_offset']})
        content = response.json()
        articles = content['response']['content']
        
        for article in articles: 
            if not is_relevant(article['title'], article['preview_content']): 
                continue 
            
            display_date = article['display_date']

            if display_date < start_date: 
                has_next = False
                continue

            title = article['title']
            link = f'https://www.881903.com/news/local/{article["item_id"]}/'
            results.append((display_date, title, link))

        
        params.update({'offset': content['response']['next_offset']})
    
    return ('商業電台', results)
