from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException
from datetime import timedelta, datetime
import time
import socket
import os
import pytz
import re

print("-- stock check start")
options = Options()

options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨
			
# 아래 옵션 두줄 추가(NAS docker 에서 실행시 필요, memory 부족해서)
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)

url1 = "https://app.webull.com/stocks"
driver.get(url1)
action = ActionChains(driver)
time.sleep(3)

# TSLA 검색
# Symbol/Name 플레이스홀더가 있는 입력창 찾기
search_box = driver.find_element(By.XPATH, "//input[@placeholder='Symbol/Name']")
search_box.send_keys("TSLA")
time.sleep(2)
# Tesla 검색결과 클릭
tesla_result = driver.find_element(By.XPATH, "//span[text()='Tesla Inc']")
tesla_result.click()
time.sleep(3)

# 주가 정보 가져오기

# DomWrap 내의 p 태그 찾기
# dom_wrap = driver.find_element(By.ID, "DomWrap")
# dom_wrap 내용 출력
# print(f"dom_wrap 내용: {dom_wrap.get_attribute('innerHTML')}")
# p_elements = dom_wrap.find_elements(By.TAG_NAME, "p")

# result1 = ""
# for p in p_elements:
#     print(f"p 태그 내용: {p.text}")

# BeautifulSoup으로 파싱
html = driver.find_element("id", "DomWrap").get_attribute("outerHTML")
soup = BeautifulSoup(html, "html.parser")
# 모든 <p> 태그 내용 가져오기
p_tags = soup.find_all("p")
result1 = "Overnight: "
# print(p_tags)

# p 태그 내의 span 태그들을 찾기
for p_tag in p_tags:
    span_tags = p_tag.find_all("span")
    for span in span_tags:
        # print(span.text)
        result1 = result1 + span.text + " "
print(result1)



# # DomWrap 내의 span 태그 찾기
# span_elements = dom_wrap.find_elements(By.TAG_NAME, "span")

# # span 태그 내용 출력
# for span in span_elements:
#     print(f"span 태그 내용: {span.text}")


# tit = driver.find_element(By.CLASS_NAME, "tit")
# print(f"tit 내용: {tit.text}")
