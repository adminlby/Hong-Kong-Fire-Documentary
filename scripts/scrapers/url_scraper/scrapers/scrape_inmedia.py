import json
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import undetected_chromedriver as uc

import unittest, time, re, random
from selenium import webdriver
import sys



def scrape():

    driver = uc.Chrome(headless=False,use_subprocess=False)
    actions = ActionChains(driver)
    
    topic_url = "https://www.inmediahk.net/taxonomy/term/541575/530434"
    driver.get(topic_url)
    print(f"Visiting topic page: {topic_url}")
    time.sleep(10)
    links = driver.find_elements(By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/section/div")
    count = len(links)
    results = []
    for j in range(count-1):
        i = j+1
        try:
            p_elm = driver.find_element(By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/section/div["+str(i)+"]/div[2]/p")
            a_elm = driver.find_element(By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/section/div["+str(i)+"]/div[2]/a[2]")
            h3_elm = driver.find_element(By.XPATH, "/html/body/div[4]/section/section/div[2]/div[2]/section/div["+str(i)+"]/div[2]/a[2]/h3")
            address = a_elm.get_attribute("href")
            article_date = p_elm.text
            article_title = h3_elm.text
            results.append((article_date, article_title, address))
        except Exception as e:
            print(e)
            pass
    driver.close()
    return ("獨立媒體", results)