from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from datetime import timedelta
from module.etc_util import printL, mode_check, tele_push_admin
# import telegram
import asyncio, json
import time, datetime
# import csv
# from openpyxl import load_workbook	# 엑셀 읽기위해 추가
import sqlite3
# import sys

#--- Start Time 기록 -----
flag = True
if flag:
	current_time = datetime.datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
	start_time = current_time.strptime(formatted_time, "%Y-%m-%d %H:%M:%S")
	printL(f"-- START : {start_time}")
	printL(f"-- {mode_check()} MODE")

#--- DB 접속설정 및 당일발송 대상 초기화 -----------
DATABASE = 'land_naver.sqlite3'
def query_database(query):
	conn = sqlite3.connect(DATABASE)
	cursor = conn.cursor()
	cursor.execute(query)
	result = cursor.fetchall()
	cursor.close()
	conn.close()
	return result

def query_database_update(query):
	conn = sqlite3.connect(DATABASE)
	cursor = conn.cursor()
	cursor.execute(query)
	conn.commit()
	cursor.close()
	conn.close()

flag = True
if flag:	# 과거데이터 삭제, 당일 데이터 삭제
	# 날짜 (오늘)
	current_time = datetime.datetime.now()
	formatted_date = current_time.strftime("%Y%m%d")
	# 어제,그제 날짜 yyyymmdd 로 만들기
	today = current_time.date()
	delete_day_form = today - timedelta(days=5)	# 삭제대상, 5일전 데이터는 삭제처리
	delete_day = delete_day_form.strftime("%Y%m%d")

	yesterday_form = today - timedelta(days=1)	# 어제일자
	yesterday = yesterday_form.strftime("%Y%m%d")
	
	query = f'DELETE FROM agent WHERE date = "{delete_day}"'	# 삭제대상(과거) 데이터 삭제
	query_database_update(query)
	query = f'DELETE FROM agent WHERE date = "{formatted_date}"'	# 당일자 삭제 (이미 있을때 다시 넣기 위해서)
	query_database_update(query)

flag = True
if flag:	# 크롬 환경설정 부분
	options = Options()
	
	# global hostname
	if mode_check() == 'TEST':
		# options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨
		pass
	else:
		options.add_argument("headless") #크롬창이 뜨지 않고 백그라운드로 동작됨

	# 아래 옵션 두줄 추가(NAS docker 에서 실행시 필요, memory 부족해서)
	options.add_argument('--no-sandbox')
	options.add_argument('--disable-dev-shm-usage')
	options.add_argument("window-size=1920,2160")	# 창크기가 작아서 전체 내용이 표시되지 않아서 크게 키움

	# 아래는 headless 크롤링을 막아놓은곳에 필요 (user agent에 HeadlessChrome 이 표시되는걸 방지)
	options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

	driver = webdriver.Chrome(options=options)

flag = True
if flag:	# --------------------------- MAIN -----------------------------
	query = f'SELECT count(*), agent_name, naver_bld_id FROM land_item WHERE date = "{formatted_date}" GROUP BY agent_name ORDER BY 1 DESC'
	printL(query)
	agent_lists = query_database(query)
	# printL(f'agent_lists ={agent_lists}')
	printL(f'count ={len(agent_lists)}')
	i = 0
	for agent_list in agent_lists:
		i = i + 1
		count = agent_list[0]
		agent = agent_list[1]
		url = f'https://new.land.naver.com/offices?articleNo={agent_list[2]}'
		printL(f'{i}/{len(agent_lists)}. {agent}, {url}')
		driver.get(url)
		time.sleep(1)
		try:
			owner = driver.find_element(By.CLASS_NAME, 'info_agent_wrap').find_element(By.TAG_NAME, 'dd').text.replace("등록번호","")
			agt_number = driver.find_element(By.CLASS_NAME, 'info_agent_wrap').find_elements(By.CLASS_NAME, 'text.text--number')
			address = agt_number[0].text
			tel = agt_number[1].text
		except:	# 일반적인 실패는 재시도 하면 되지만, 매물이 없어져서 해당 페이지가 안열리면 재시도해도 실패됨.
			printL("RETRY......~~")
			time.sleep(2)
			try:
				owner = driver.find_element(By.CLASS_NAME, 'info_agent_wrap').find_element(By.TAG_NAME, 'dd').text.replace("등록번호","")
				agt_number = driver.find_element(By.CLASS_NAME, 'info_agent_wrap').find_elements(By.CLASS_NAME, 'text.text--number')
				address = agt_number[0].text
				tel = agt_number[1].text
			except:
				printL("RETRY Failed. 전일자에서라도 정보를 검색...")
				query = f'SELECT owner, address, tel1 FROM agent WHERE agent_name = "{agent}" AND owner != ""'	# 현재 매물이 없어졌으니 어제자 정보라도 찾기
				agent_info = query_database(query)
				printL(f'agent_info length = {len(agent_info)}')
				if len(agent_info) > 0:
					owner = f'{agent_info[0][0]}⚲'
					address = agent_info[0][1]
					tel = agent_info[0][2]
				else:
					owner = ""
					address = ""
					tel = ""

		query = f'SELECT count(*) FROM land_item WHERE date = "{yesterday}" AND agent_name = "{agent}"'	# 어제 매물건수 확인
		yesterday_count = query_database(query)[0][0]
		if yesterday_count == 0:
			chg = "new"
		else:
			chg = count - yesterday_count
		printL(f'count = {count}, chg = {chg}')
		printL(f'owner = {owner}')
		printL(f'address = {address}')
		printL(f'tel = {tel}')

		query = f'INSERT INTO agent (date, agent_name, link, count, chg, owner, address, tel1, tel2, etc1, etc2, etc3) VALUES ("{formatted_date}", "{agent}", "{url}", {count}, "{chg}", "{owner}", "{address}", "{tel}", "", "", "", "")'
		query_database_update(query)
		printL('------------------------------------------------------------')
driver.quit()

#--- End Time 기록 -----
flag = True
if flag:
	current_time = datetime.datetime.now()
	formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
	end_time = current_time.strptime(formatted_time, "%Y-%m-%d %H:%M:%S")
	elap_time = end_time - start_time
	printL(f"-- END : {end_time}")
	printL(f"-- Elapsed time : {elap_time}")