import time

import undetected_chromedriver as uc
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


def scrape():
    driver = uc.Chrome(headless=False, use_subprocess=False)
    actions = ActionChains(driver)

    topic_url = "https://www.inmediahk.net/taxonomy/term/541575/530434"
    driver.get(topic_url)
    print(f"Visiting topic page: {topic_url}")
    time.sleep(10)
    links = driver.find_elements(By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/section/div")
    count = len(links)
    results = []
    for j in range(count - 1):
        i = j + 1
        try:
            p_elm = driver.find_element(By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/section/div[" + str(i) + "]/div[2]/p")
            a_elm = driver.find_element(By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/section/div[" + str(i) + "]/div[2]/a[2]")
            h3_elm = driver.find_element(By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/section/div[" + str(i) + "]/div[2]/a[2]/h3")
            address = a_elm.get_attribute("href")
            article_date = p_elm.text
            article_title = h3_elm.text
            results.append((article_date, article_title, address))
        except Exception as e:
            print(e)
            pass
    driver.close()
    return ("獨立媒體", results)
